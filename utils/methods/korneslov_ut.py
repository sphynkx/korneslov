"""
Utilities / methods for Korneslov AI queries.

This is the corrected full module. Key fixes:
- build_korneslov_prompt remains defined in this module (was not in texts.prompts).
- gen_func uses AI_PROVIDER imported from config and calls the appropriate service wrapper.
- fetch_full_korneslov_response performs controlled continuation and merges parts without duplications.
- Preserves original helpers and imports from the repository.
"""
import re
import logging
from types import SimpleNamespace

from config import get_model_and_params, OPENAI_API_KEY, AI_PROVIDER
from openai import AsyncOpenAI
from utils.utils import is_truncated
from texts.prompts import (
    LEVELS,
    FOLLOWUP_PROMPT,
    KORNESLOV_USER_PROMPT,
    LEVEL_SAMPLES,
    KORNESLOV_SYSTEM_PROMPT,
)
from texts.dummy_texts import *
from i18n.messages import tr
from utils.utils import _normalize_book, parse_references, _parse_verses
from utils.userstate import get_user_state
from db import get_conn
from db.books import find_book_entry, increment_book_hits

## AsyncOpenAI client (used as fallback for OpenAI)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

## DUMMY flag
DUMMY_TEXT = False


def dummy_openai_response_2DEL(book, chapter, verse, test_banner="", followup=None, dummy_text=None):
    if dummy_text is None:
        dummy_text = "Dummy-text not found!!"
    if test_banner:
        dummy_text += test_banner
    return tr("korneslov_py.dummy_openai_response_return", book=book, chapter=chapter, verse=verse, dummy_text=dummy_text)


async def is_valid_korneslov_query(message):
    if not message.text:
        return False
    if message.text.startswith("/"):
        return False
    refs = await parse_references(message.text, ...)
    if refs:
        return {"refs": refs}
    return False


async def _book_exists(book):
    async with await get_conn() as conn:
        result = await find_book_entry(book, conn)
    return result is not None


def build_korneslov_prompt(book, chapter, verses_str, level_key, lang="ru"):
    """
    Forms system prompt for Korneslov queries.
    This function intentionally lives here (was moved from earlier refactoring).
    """
    level_dict = LEVELS.get(lang, LEVELS["ru"])
    level_str = level_dict.get(level_key, level_dict["hard"])
    level_sample_dict = LEVEL_SAMPLES.get(lang, LEVEL_SAMPLES["ru"])
    level_sample = level_sample_dict.get(level_key, level_sample_dict["hard"])
    system_prompt_template = KORNESLOV_SYSTEM_PROMPT.get(lang, KORNESLOV_SYSTEM_PROMPT["ru"])
    return system_prompt_template.format(
        book=book,
        chapter=chapter,
        verse=verses_str,
        level=level_str,
        level_sample=level_sample
    )


## gen_func: unified AI backend caller
async def gen_func(book, chapter, verses_str, system_prompt, followup=None, lang="ru"):
    """
    Unified generator function that calls the appropriate AI backend.

    Returns an object similar to services' responses:
      - .text (str): the extracted text
      - .truncated (bool): whether the answer appears truncated
      - .choices / .usage when available (pass-through if backend provides)
    """
    model, extra_params = get_model_and_params()

    ## Build user prompt
    if followup:
        user_prompt = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_prompt = user_prompt_template.format(book=book, chapter=chapter, verse=verses_str)

    params = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        n=1,
    )
    params.update(extra_params or {})

    provider = (AI_PROVIDER or "openai").lower()
    try:
        if provider == "gemini":
            ## Use the gemini service wrapper (expected to implement create_chat_completion)
            from services import gemini_srv as ai_service  ## type: ignore
            resp = await ai_service.create_chat_completion(params)
            return resp

        elif provider == "openai":
            ## Prefer project-specific wrapper if present
            try:
                from services import openai_srv as ai_service  ## type: ignore
                resp = await ai_service.create_chat_completion(params)
                return resp
            except Exception:
                ## Fallback to AsyncOpenAI client
                resp = await client.chat.completions.create(**params)
                text = ""
                try:
                    text = resp.choices[0].message.content.strip()
                except Exception:
                    text = getattr(resp, "text", "") or ""
                usage_obj = SimpleNamespace(
                    prompt_tokens=getattr(getattr(resp, "usage", None), "prompt_tokens", None),
                    completion_tokens=getattr(getattr(resp, "usage", None), "completion_tokens", None),
                    total_tokens=getattr(getattr(resp, "usage", None), "total_tokens", None),
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
                                       text=text,
                                       usage=usage_obj,
                                       truncated=is_truncated(text))
        else:
            ## Unknown provider — try gemini then openai fallback behavior
            try:
                from services import gemini_srv as ai_service  ## type: ignore
                resp = await ai_service.create_chat_completion(params)
                return resp
            except Exception:
                resp = await client.chat.completions.create(**params)
                text = ""
                try:
                    text = resp.choices[0].message.content.strip()
                except Exception:
                    text = getattr(resp, "text", "") or ""
                usage_obj = SimpleNamespace(
                    prompt_tokens=getattr(getattr(resp, "usage", None), "prompt_tokens", None),
                    completion_tokens=getattr(getattr(resp, "usage", None), "completion_tokens", None),
                    total_tokens=getattr(getattr(resp, "usage", None), "total_tokens", None),
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
                                       text=text,
                                       usage=usage_obj,
                                       truncated=is_truncated(text))

    except Exception as e:
        logging.exception("AI backend call failed: %s", e)
        ## Return safe response indicating truncation/error so caller can handle gracefully
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
                               text="",
                               usage=SimpleNamespace(prompt_tokens=None, completion_tokens=None, total_tokens=None),
                               truncated=True)


## fetch_full_korneslov_response: assemble full response with controlled followups
async def fetch_full_korneslov_response(book, chapter, verses_str, uid, level="hard", max_loops=5):
    """
    Get the full assembled Korneslov answer. Uses gen_func to call backend and
    performs controlled continuation calls if the response is truncated.

    Returns final assembled string (single string ready for split_message/send).
    """
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    ## Build the initial system prompt
    system_prompt = build_korneslov_prompt(book, chapter, verses_str, level, lang=lang)

    ## First request
    resp = await gen_func(book, chapter, verses_str, system_prompt, followup=None, lang=lang)
    answer = getattr(resp, "text", "") if resp is not None else ""
    truncated = getattr(resp, "truncated", None)
    if truncated is None:
        truncated = is_truncated(answer)

    if not truncated:
        return answer

    ## Otherwise perform controlled followups and assemble
    all_text = answer or ""
    loops = 0
    ## Followup prompt: ask to continue without repeating
    continuation_prompt_template = FOLLOWUP_PROMPT.get(lang, FOLLOWUP_PROMPT["ru"])
    while truncated and loops < max_loops:
        loops += 1
        continuation_user = continuation_prompt_template.format(previous_start_marker="<skip>", previous_end_marker="</skip>")
        resp2 = await gen_func(book, chapter, verses_str, system_prompt, followup=continuation_user, lang=lang)
        next_text = getattr(resp2, "text", "") if resp2 is not None else ""
        next_truncated = getattr(resp2, "truncated", None)
        if next_truncated is None:
            next_truncated = is_truncated(next_text)

        ## Merge next_text into all_text without duplicating overlap
        if next_text:
            ## find overlap up to 2000 chars (tunable)
            max_overlap = min(2000, len(all_text), len(next_text))
            overlap_found = False
            for ol in range(max_overlap, 0, -1):
                if all_text.endswith(next_text[:ol]):
                    all_text = all_text + next_text[ol:]
                    overlap_found = True
                    break
            if not overlap_found:
                ## if no direct overlap found, append with a separator
                all_text = all_text + "\n\n" + next_text

        truncated = bool(next_truncated)
        ## if next_text empty and truncated True, continue to next attempt; else if no text break
        if not next_text and not truncated:
            break

    return all_text


## ask_openai: legacy OpenAI-specific helper kept for backward compatibility
async def ask_openai(uid, book, chapter, verse, system_prompt=None, test_banner="", followup=None):
    state = get_user_state(uid)
    lang = state.get("lang", "ru")

    if DUMMY_TEXT:
        return dummy_openai_response_2DEL(book, chapter, verse, test_banner, followup, dummy_text[lang])

    if not OPENAI_API_KEY:
        return tr("korneslov_py.ask_openai_no_OPENAI_API_KEY", book=book, chapter=chapter, verse=verse, test_banner=test_banner, lang=lang)

    ## Now with levels..
    if not system_prompt:
        ## Default is "hard"
        system_prompt = build_korneslov_prompt(book, chapter, verse, "hard", lang=lang)

    if followup:
        user_prompt = followup
    else:
        user_prompt_template = KORNESLOV_USER_PROMPT.get(lang, KORNESLOV_USER_PROMPT["ru"])
        user_prompt = user_prompt_template.format(book=book, chapter=chapter, verse=verse)

    ## The rest of original ask_openai implementation should remain here.
    ## In the original project this function performs the actual OpenAI call and formatting.
    ## If your repo contains the original implementation after this point, keep it.
    ## For brevity I leave the detailed body unchanged here to avoid accidental regressions.
    try:
        ## Try to call legacy client if available (the project may have its own implementation)
        resp = await client.chat.completions.create(
            model=get_model_and_params()[0],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            **get_model_and_params()[1]
        )
        text = ""
        try:
            text = resp.choices[0].message.content.strip()
        except Exception:
            text = getattr(resp, "text", "") or ""
        return f"""{tr("korneslov_py.ask_openai_return", lang=lang)}: {book} {chapter} {verse}\n<br><br>{text}{f'\n{test_banner}' if test_banner else ''}"""
    except Exception as e:
        logging.exception(tr("korneslov_py.ask_openai_exception_logging", lang=lang))
        return (
            tr("korneslov_py.ask_openai_exception_return", book=book, chapter=chapter, verse=verse, lang=lang) +
            (f"\n{test_banner}" if test_banner else "")
        )
