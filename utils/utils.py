import re
from i18n.messages import tr

## Dummy for Statistika button
def get_statistics_text() -> str:
    return "STATISTIKA."


## Split msgz for Teleram (with tiny heuristicx).
def split_message_OLD(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        ## Search for closest \n or <br> before limit
        split_pos = text.rfind('<br>', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('.', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        else:
            split_pos += 4 if text[split_pos:split_pos+4] == '<br>' else 1
        parts.append(text[:split_pos].strip())
        text = text[split_pos:].lstrip()
    if text:
        parts.append(text)
    return parts


## Improved heuristics - tracks allowed pair tags, count all tags using dict. In case of unclosed tag force set close tag at the end of part, and force set open tag at the beginning of the next part. No errors were observed.
def split_message(text, max_length=4000):
    ## Only paired tags and allowed for telegram API
    TELEGRAM_PAIR_TAGS = {
        "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
        "span", "a", "code", "pre"
    }

    def get_tag_counts(s):
        ## Count every tags
        tags = re.findall(r'<(/?)(\w+)[^>]*?>', s)
        counts = dict.fromkeys(TELEGRAM_PAIR_TAGS, 0)
        for slash, tag in tags:
            tag = tag.lower()
            if tag not in TELEGRAM_PAIR_TAGS:
                continue
            if not slash:
                counts[tag] += 1
            else:
                counts[tag] -= 1
        return counts

    parts = []
    while len(text) > max_length:
        ## Search for closest \n or <br> before limit
        split_pos = text.rfind('<br>', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind('.', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        else:
            split_pos += 4 if text[split_pos:split_pos+4] == '<br>' else 1

        part = text[:split_pos].strip()
        counts = get_tag_counts(part)
        ## Force close unclosed tag
        for tag, count in counts.items():
            if count % 2 == 1:
                part += f'</{tag}>'
        parts.append(part)
        text = text[split_pos:].lstrip()
        ## Force set open tag at beginning of next part
        for tag, count in counts.items():
            if count % 2 == 1:
                text = f'<{tag}>' + text
    if text:
        parts.append(text)
    return parts


def is_truncated(answer: str, min_length=3500, ending_punct=('.','…','!','?', '>')):
    """
    Heuristics: if response length is close to max_tokens * 4 (about 3000 tokens = 4000–4500 symbols), ans response doesnt end on any sentence ending sign then the response is probably cutted.
    """
    answer = answer.strip()
    ## Dirty hack - to permit false repeates and unneeded followups
    ##if re.search(tr("utils_py.is_truncated_regexp"), answer):
    ##Swithed to more universal marker
    if re.search("<b>\u200b\u200b\u200b\u200b</b>", answer):
        return False

    long_enough = len(answer) >= min_length
    truncated = long_enough and not answer.endswith(ending_punct)
    return truncated

