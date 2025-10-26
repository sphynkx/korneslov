import logging


def extract_text_from_openai_response(resp) -> str:
    """
    Normalize different OpenAI response shapes to a string.
    Returns "" if nothing found.
    """
    try:
        if resp is None:
            return ""
        ## direct string
        if isinstance(resp, str):
            return resp.strip()

        ## v1 client shape: choices[0].message.content
        choices = getattr(resp, "choices", None)
        if choices:
            try:
                c0 = choices[0]
            except Exception:
                c0 = None
            if c0 is not None:
                msg = getattr(c0, "message", None) or (c0.get("message") if isinstance(c0, dict) else None)
                if msg:
                    cont = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                    if isinstance(cont, str) and cont.strip():
                        return cont.strip()
                alt = getattr(c0, "text", None) or getattr(c0, "content", None) or (c0.get("text") if isinstance(c0, dict) else None)
                if isinstance(alt, str) and alt.strip():
                    return alt.strip()

        ## fallback: dict-like top-level
        if isinstance(resp, dict):
            for key in ("text", "output", "result", "content"):
                val = resp.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return ""
    except Exception as e:
        logging.exception("extract_text_from_openai_response failed: %s", e)
        try:
            logging.debug("repr(resp) truncated: %s", repr(resp)[:4000])
        except Exception:
            pass
        return ""
