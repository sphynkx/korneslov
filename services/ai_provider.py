import logging
from typing import Optional

from config import AI_PROVIDER


async def ask_ai(
    uid: int,
    book: str,
    chapter: int,
    verse: str,
    system_prompt: Optional[str] = None,
    followup: Optional[str] = None,
    test_banner: str = "",
) -> str:
    """
    Provider dispatcher: routes to OpenAI or Gemini service based on AI_PROVIDER.
    Returns formatted string suitable for sending to Telegram.
    """
    provider = (AI_PROVIDER or "openai").lower()

    if provider == "gemini":
        try:
            from services.gemini_srv import ask_gemini
            return await ask_gemini(uid, book, chapter, verse, system_prompt=system_prompt, test_banner=test_banner, followup=followup)
        except Exception:
            logging.exception("Gemini provider failed, falling back to OpenAI")
            ## fall through to OpenAI

    ## default / fallback: OpenAI
    from services.openai_srv import ask_openai
    return await ask_openai(uid, book, chapter, verse, system_prompt=system_prompt, test_banner=test_banner, followup=followup)
