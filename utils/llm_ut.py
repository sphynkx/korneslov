import asyncio
import json
import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse, unquote

import httpx


DEFAULT_LLM_TIMEOUT_S = 120.0
DEFAULT_PROXY_PRECHECK_TIMEOUT_S = 2.0


class LLMInfraError(RuntimeError):
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


RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


def _iter_exc_chain(exc: BaseException, max_depth: int = 10):
    cur: Optional[BaseException] = exc
    depth = 0
    while cur is not None and depth < max_depth:
        yield cur
        nxt = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
        cur = nxt if isinstance(nxt, BaseException) else None
        depth += 1


def is_retryable_exception(exc: BaseException) -> bool:
    # 1) direct httpx/httpcore errors
    for e in _iter_exc_chain(exc):
        if isinstance(
            e,
            (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.ProxyError,
                httpx.RemoteProtocolError,
                httpx.NetworkError,
            ),
        ):
            return True

        # 2) plain asyncio/socket timeouts surfaced differently
        if isinstance(e, (TimeoutError, asyncio.TimeoutError)):
            return True

        # 3) OpenAI wraps timeouts into APITimeoutError (we don't import openai here to avoid hard dependency)
        if e.__class__.__name__ in ("APITimeoutError", "TimeoutException"):
            return True

    return False


def is_retryable_status(status_code: Optional[int]) -> bool:
    return status_code in RETRYABLE_HTTP_STATUSES if status_code is not None else False


@dataclass(frozen=True)
class ParsedProxy:
    scheme: str
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]


def parse_proxy_url(proxy_url: str) -> ParsedProxy:
    u = urlparse(proxy_url)
    if not u.scheme or not u.hostname or not u.port:
        raise ValueError(f"Invalid proxy url: {proxy_url!r}")

    scheme = u.scheme.lower()
    username = unquote(u.username) if u.username else None
    password = unquote(u.password) if u.password else None
    return ParsedProxy(
        scheme=scheme,
        host=u.hostname,
        port=int(u.port),
        username=username,
        password=password,
    )


async def tcp_port_check(host: str, port: int, *, timeout_s: float = DEFAULT_PROXY_PRECHECK_TIMEOUT_S) -> Tuple[bool, str]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout_s)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True, "tcp_ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def socks5_handshake_check(proxy_url: str, *, timeout_s: float = DEFAULT_PROXY_PRECHECK_TIMEOUT_S) -> Tuple[bool, str]:
    try:
        p = parse_proxy_url(proxy_url)
        if p.scheme not in ("socks5", "socks5h"):
            return False, f"Unsupported scheme for socks5 check: {p.scheme}"

        reader, writer = await asyncio.wait_for(asyncio.open_connection(p.host, p.port), timeout=timeout_s)

        # VER=0x05, NMETHODS=2, METHODS: 0x00 (no auth), 0x02 (user/pass)
        writer.write(b"\x05\x02\x00\x02")
        await writer.drain()

        data = await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)
        ver, method = data[0], data[1]
        if ver != 0x05:
            writer.close()
            return False, f"bad_ver={ver}"
        if method == 0xFF:
            writer.close()
            return False, "no_acceptable_auth_methods"

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        return True, f"socks5_ok(method=0x{method:02x})"

    except asyncio.IncompleteReadError:
        return False, "IncompleteReadError: proxy closed connection during handshake"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def check_proxy_available(proxy_url: str, *, timeout_s: float = DEFAULT_PROXY_PRECHECK_TIMEOUT_S) -> Tuple[bool, str]:
    try:
        p = parse_proxy_url(proxy_url)
    except Exception as e:
        return False, f"parse_error: {e}"

    ok_tcp, info_tcp = await tcp_port_check(p.host, p.port, timeout_s=timeout_s)
    if not ok_tcp:
        return False, info_tcp

    if p.scheme in ("socks5", "socks5h"):
        return await socks5_handshake_check(proxy_url, timeout_s=timeout_s)

    return True, "tcp_ok(http_proxy_not_deep_checked)"


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


def build_httpx_client_for_proxy(
    proxy_url: Optional[str],
    *,
    timeout_s: float = DEFAULT_LLM_TIMEOUT_S,
) -> httpx.AsyncClient:
    """
    httpx<0.26 compatible:
      - use proxies= mapping
      - trust_env=False
      - set generous timeouts (proxy + TLS + upstream latency)
    """
    timeout = httpx.Timeout(
        timeout=timeout_s,
        connect=min(20.0, timeout_s),
        read=timeout_s,
        write=min(30.0, timeout_s),
        pool=min(30.0, timeout_s),
    )

    if proxy_url:
        return httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        )

    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
    )


async def run_with_proxy_failover(
    provider: str,
    proxies: Sequence[ProxySpec],
    func,
    *,
    allow_direct_if_no_proxies: bool = False,
    precheck_proxy_port: bool = True,
    precheck_timeout_s: float = DEFAULT_PROXY_PRECHECK_TIMEOUT_S,
    llm_timeout_s: float = DEFAULT_LLM_TIMEOUT_S,
) -> Any:
    attempts: List[Dict[str, Any]] = []

    if not proxies:
        if allow_direct_if_no_proxies:
            async with build_httpx_client_for_proxy(None, timeout_s=llm_timeout_s) as http_client:
                return await func(http_client, None)
        raise LLMInfraError("No enabled proxies configured", provider=provider, attempts=[])

    last_exc: Optional[BaseException] = None

    for p in proxies:
        proxy_label = f"{p.name} ({_mask_proxy_url(p.url)})"

        if precheck_proxy_port:
            ok, info = await check_proxy_available(p.url, timeout_s=precheck_timeout_s)
            if not ok:
                attempts.append({"proxy": proxy_label, "precheck": True, "ok": False, "info": info, "retryable": True})
                logging.warning("Proxy precheck failed, provider=%s proxy=%s info=%s", provider, proxy_label, info)
                continue

        try:
            async with build_httpx_client_for_proxy(p.url, timeout_s=llm_timeout_s) as http_client:
                return await func(http_client, p)
        except Exception as e:
            last_exc = e

            status = None
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    status = e.response.status_code
                except Exception:
                    status = None

            retryable = is_retryable_exception(e) or is_retryable_status(status)

            attempts.append(
                {
                    "proxy": proxy_label,
                    "exc_type": type(e).__name__,
                    "exc": str(e),
                    "status": status,
                    "retryable": retryable,
                }
            )

            if retryable:
                logging.warning("LLM proxy attempt failed (retryable), provider=%s proxy=%s err=%s", provider, proxy_label, e)
                continue

            logging.error("LLM proxy attempt failed (non-retryable), provider=%s proxy=%s err=%s", provider, proxy_label, e)
            raise

    msg = f"All proxies failed for provider={provider}"
    if last_exc is not None:
        msg += f" (last error: {type(last_exc).__name__}: {last_exc})"
    raise LLMInfraError(msg, provider=provider, attempts=attempts)