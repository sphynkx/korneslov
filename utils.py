def split_message(text, max_length=4000):
    """Split text by parts less than max_length, splitting by paragraph or dots."""
    parts = []
    while len(text) > max_length:
        split_pos = text.rfind('\n\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('.', 0, max_length)
            if split_pos == -1:
                split_pos = max_length
            else:
                split_pos += 1
        else:
            split_pos += 2
        parts.append(text[:split_pos].strip())
        text = text[split_pos:].lstrip()
    if text:
        parts.append(text)
    return parts

def is_truncated(answer: str, min_length=3500, ending_punct=('.','…','!','?')):
    """
    Heuristics: if response length is close to max_tokens * 4 (about 3000 tokens = 4000–4500 symbols), ans response doesnt end on any sentense ending sign then the response is probably cutted.
    """
    answer = answer.strip()
    long_enough = len(answer) >= min_length
    truncated = long_enough and not answer.endswith(ending_punct)
    return truncated