import re

def escape_markdown_v2(text: str) -> str:
    """
    Экранирует спецсимволы для Telegram MarkdownV2.
    """
    # Список спецсимволов для MarkdownV2
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

def escape_numbered_list(text: str) -> str:
    """
    Эксклюзивно экранирует только точку после цифры в начале строки (для списков).
    """
    # Превращает "1) ..." в "1. ..." и экранирует точку
    # Превращает "1. ..." в "1\. ..."
    return re.sub(r'^(\d+)\.\s', r'\1\\. ', text, flags=re.MULTILINE)

def format_text_for_telegram_md(text: str) -> str:
    """
    Форматирует текст для Telegram MarkdownV2:
    1. Экранирует все спецсимволы.
    2. Для нумерованных списков экранирует только точку (для Telegram).
    """
    # Сначала экранируем точку для списков (1. , 2. , ...)
    text = re.sub(r'^(\d+)\)', r'\1.', text, flags=re.MULTILINE) # 1) => 1.
    text = escape_numbered_list(text)
    # Потом экранируем все остальные спецсимволы
    safe = escape_markdown_v2(text)
    return safe

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