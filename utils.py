import re

## Dummy for Statistika button
def get_statistics_text() -> str:
    return "STATISTICA."

def escape_markdown_v2_DEL(text: str) -> str:
    """
    Экранирует спецсимволы для Telegram MarkdownV2.
    """
    # Список спецсимволов для MarkdownV2
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

def escape_numbered_list_DEL(text: str) -> str:
    """
    Эксклюзивно экранирует только точку после цифры в начале строки (для списков).
    """
    # Превращает "1) ..." в "1. ..." и экранирует точку
    # Превращает "1. ..." в "1\. ..."
    return re.sub(r'^(\d+)\.\s', r'\1\\. ', text, flags=re.MULTILINE)




## Work variant but escapes ALL specsymbols - tg-parser not recognize that text id MD-formated and displays as simple text.
def format_text_for_telegram_md_DEL(text: str) -> str:
    """
    Железобетонная экранировка для Telegram MarkdownV2.
    Экранирует каждый markdown-спецсимвол всегда, по всему тексту.
    """
    # Весь список спецсимволов
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)
    
def format_text_for_telegram_md_BLA_DEL(text: str) -> str:
    """
    Экранирует только опасные спецсимволы для Telegram MarkdownV2.
    Оставляет *...* и _..._ для форматирования.
    """
    # 1. Экранируем точку после цифры в начале строки (нумерованный список)
    text = re.sub(r'^(\d+)\.(\s)', r'\1\\.\2', text, flags=re.MULTILINE)
    # 2. Экранируем #, +, -, =, !, . только в начале строки
    text = re.sub(r'^(#|\+|-|=|!|\.)', r'\\\1', text, flags=re.MULTILINE)
    # 3. Экранируем [ ] ( ) ~ ` > | { } во всем тексте
    escape_chars = r'\[\]()~`>|{}+\.'
    text = re.sub(r'([%s])' % escape_chars, r'\\\1', text)
    text = re.sub(r'^(\d+)\.(?=\s|\S)\\(\\)', r'\1\\.', text, flags=re.MULTILINE)

    return text



import re

def split_message(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        # Ищем ближайший перенос строки или <br> перед лимитом
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


def is_truncated(answer: str, min_length=3500, ending_punct=('.','…','!','?')):
    """
    Heuristics: if response length is close to max_tokens * 4 (about 3000 tokens = 4000–4500 symbols), ans response doesnt end on any sentense ending sign then the response is probably cutted.
    """
    answer = answer.strip()
    long_enough = len(answer) >= min_length
    truncated = long_enough and not answer.endswith(ending_punct)
    return truncated



def html_escape_telegram_DEL(text):
    # Экранирует <, >, & только между тегами, но НЕ внутри тегов!
    def escape(m):
        s = m.group(1)
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return re.sub(r'>([^<]*)<', lambda m: '>' + escape(m) + '<', text)



def check_html_balance_DEL(text):
    tags = re.findall(r'<(/?\w+)', text)
    stack = []
    for t in tags:
        if not t.startswith('/'):
            stack.append(t)
        else:
            if stack and stack[-1] == t[1:]:
                stack.pop()
            else:
                print(f"Unmatched closing tag: </{t[1:]}>")
    if stack:
        print("Unmatched opening tags:", stack)
    else:
        print("Tags balanced")
