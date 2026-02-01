import asyncio
import json
import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


# ----------------------------
# Errors
# ----------------------------

class LLMInfraError(RuntimeError):
    """
    Infrastructure-level failure for LLM call (all proxies failed, timeouts, network issues).
    Catch this to avoid charging.
    """
    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        attempts: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.attempts = attempts or []


# ----------------------------
# Proxy config
# ----------------------------

@dataclass(frozen=True)
class ProxySpec:
    name: str
    url: str
    enabled: bool = True


def _mask_proxy_url(url: str) -> str:
    if not isinstance(url, str) or not url:
        return ""
    return re.sub(r":([^:@/]+)@", r":***@", url)


def load_proxies_from_file(path: str) -> List[ProxySpec]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    proxies_raw = data.get("proxies") if isinstance(data, dict) else None
    if not isinstance(proxies_raw, list):
        raise ValueError(f"Invalid proxies config {path}: expected key 'proxies' as list")

    proxies: List[ProxySpec] = []
    for i, item in enumerate(proxies_raw):
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        if not url:
            continue
        name = (item.get("name") or f"proxy-{i+1}").strip()
        enabled = bool(item.get("enabled", True))
        proxies.append(ProxySpec(name=name, url=url, enabled=enabled))
    return proxies


def get_enabled_proxies() -> List[ProxySpec]:
    cfg = (os.getenv("PROXIES_CONFIG") or "").strip()
    if not cfg:
        return []
    try:
        proxies = load_proxies_from_file(cfg)
    except Exception:
        logging.exception("Failed to load proxies config from PROXIES_CONFIG=%r", cfg)
        return []
    return [p for p in proxies if p.enabled and p.url]


# ----------------------------
# Env proxy switching (process-wide)
# ----------------------------

@contextmanager
def temp_env(env_updates: Dict[str, Optional[str]]):
    old: Dict[str, Optional[str]] = {}
    try:
        for k, v in env_updates.items():
            old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, prev in old.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev


def build_proxy_env(proxy_url: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Set multiple vars for maximum compatibility:
      - ALL_PROXY is what you used before
      - HTTP_PROXY/HTTPS_PROXY are widely used too
    """
    if proxy_url:
        return {
            "ALL_PROXY": proxy_url,
            "HTTP_PROXY": proxy_url,
            "HTTPS_PROXY": proxy_url,
        }
    return {
        "ALL_PROXY": None,
        "HTTP_PROXY": None,
        "HTTPS_PROXY": None,
    }


# ----------------------------
# Failover runner (env-based)
# ----------------------------

# Global lock: switching env must be serialized in async app
_ENV_PROXY_LOCK = asyncio.Lock()


async def run_with_envproxy_failover(
    provider: str,
    proxies: Sequence[ProxySpec],
    func,  # async callable, no args
) -> Any:
    """
    Try proxies in order (priority-first). No stickiness.
    Uses env vars under a global lock for safety.

    func signature:
      async def func() -> Any
    """
    attempts: List[Dict[str, Any]] = []

    if not proxies:
        raise LLMInfraError("No enabled proxies configured", provider=provider, attempts=[])

    last_exc: Optional[BaseException] = None

    for p in proxies:
        proxy_label = f"{p.name} ({_mask_proxy_url(p.url)})"

        async with _ENV_PROXY_LOCK:
            with temp_env(build_proxy_env(p.url)):
                try:
                    return await func()
                except Exception as e:
                    last_exc = e
                    # Heuristic retryable: any timeout/network/proxy-related errors
                    ename = type(e).__name__
                    msg = str(e)
                    retryable = any(
                        key in ename for key in (
                            "Timeout", "ReadTimeout", "ConnectTimeout", "ConnectError", "Proxy", "APIConnectionError", "APITimeoutError"
                        )
                    ) or "timed out" in msg.lower()

                    attempts.append(
                        {
                            "proxy": proxy_label,
                            "exc_type": ename,
                            "exc": msg,
                            "retryable": retryable,
                        }
                    )

                    if retryable:
                        logging.warning("LLM attempt failed (retryable), provider=%s proxy=%s err=%s", provider, proxy_label, e)
                        continue

                    logging.error("LLM attempt failed (non-retryable), provider=%s proxy=%s err=%s", provider, proxy_label, e)
                    raise

    msg = f"All proxies failed for provider={provider}"
    if last_exc is not None:
        msg += f" (last error: {type(last_exc).__name__}: {last_exc})"
    raise LLMInfraError(msg, provider=provider, attempts=attempts)