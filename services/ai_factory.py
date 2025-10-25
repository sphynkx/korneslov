"""
Factory for AI service modules.

Provides get_ai_service() which returns a module-like object implementing:
- create_chat_completion(params) -> raw response (async)
The provider is selected via config.AI_PROVIDER (string). Default: "openai".

This keeps callers (e.g. korneslov_ut) provider-agnostic.
"""
import importlib
import logging

try:
    from config import AI_PROVIDER as CFG_AI_PROVIDER
except Exception:
    CFG_AI_PROVIDER = None

_provider_cache = {}

def get_ai_service():
    """
    Return the service module for the configured AI provider.
    Raises RuntimeError on unknown provider or missing implementation.
    """
    provider = CFG_AI_PROVIDER or "openai"
    provider = provider.lower()

    if provider in _provider_cache:
        return _provider_cache[provider]

    logging.debug("AI factory selecting provider: %s", provider)

    if provider == "openai":
        try:
            from services import openai_srv as svc
            _provider_cache[provider] = svc
            return svc
        except Exception as e:
            logging.exception("Failed to import OpenAI service module: %s", e)
            raise RuntimeError("OpenAI service module not available") from e

    if provider == "gemini":
        try:
            from services import gemini_srv as svc
            _provider_cache[provider] = svc
            return svc
        except Exception as e:
            logging.exception("Failed to import Gemini service module: %s", e)
            raise RuntimeError("Gemini service module not available") from e

    ## unknown provider
    logging.error("Unknown AI provider configured: %s", provider)
    raise RuntimeError(f"Unknown AI provider configured: {provider}")
