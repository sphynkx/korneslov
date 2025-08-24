from userstate import get_user_state

MESSAGES = {
    "ru": {
        "main_menu": {
            "welcome": "Добро пожаловать! Выберите действие:",
            "test1": "Корнеслов Бытие 1:1",
            "test2": "Корнеслов Бытие 3:1",
            "test3": "Корнеслов Иоанна 11:35",
            "language": "Language",
            "korneslov": "Корнеслов",
            "payment": "Оплата",
            "stats": "Статистика",
            "help": "Справка",
            "title": "Главное меню",
            "help_text": "Это справка по использованию бота. Здесь вы найдете информацию о функциях и возможностях."
        },
        "korneslov_menu": {
            "masoret": "Масорет",
            "rishi": "Риши",
            "back_to_main": "Назад в главное меню",
            "title": "Корнеслов",
            "prompt": """Выберите доступные опции в меню ниже. Если меню не отображено, нажмите на значок квадрата с точками справа внизу. Доступные направления:
 • <b>Масорет</b> - исследования ветхозаветного текста (древний иврит).
 • <b>Риши</b> - исследования текстов на санскрите: Shrimad Bhagavatam/Шримад Бхагаватам..
 • <b>Что-то еще</b> - что-нибудь еще..
\nВ каждом направлении есть подпункты для выбора уровня сложности разбора.

______________"""
        },
        "masoret_menu": {
            "light": "Поугарать",
            "smart": "Подробнее",
            "hard": "Академично",
            "back_to_korneslov": "Назад к Корнеслову",
            "prompt": """<b>Масорет</b> — выберите уровень сложности анализа:
Ответ может состоять из неполного набора доступных частей (0-3). Имеющиеся части разбора:
— <b>Часть 0 — Текст строки</b>
— <b>Часть 1 — Детальная справка по каждому слову</b>
— <b>Часть 2 — Список слов со значениями базовых корней</b>
— <b>Часть 3 — Цепочки базовых значений</b>

Та или иная совокупность частей выводится в зависимости от выбранного уровня сложности. Доступны следующие уровни:
• <b>Поугарать</b> - Простой разбор. Выводятся части 0 и 3.
• <b>Подробнее</b> - Более сложный разбор. Выводятся части 0, 2 и 3.
• <b>Академично</b> - Максимально глубокий и основательный разбор. Выводятся все части - 0, 1, 2 и 3.

После выбора уровня сложности не забудьте отправить запрос. Напишите его в формте:

<b>Корнеслов Книга Глава:Стих</b>

Напр.: Корнеслов Бытие 1:1

______________"""
,
            "level_set": "Установлен уровень"
        },
        "rishi_menu": {
            "light": "Поугарать",
            "smart": "Подробнее",
            "hard": "Академично",
            "back_to_korneslov": "Назад к Корнеслову",
            "prompt": "Риши — выберите действие:",
        },
        "oplata_menu": {
            "back_to_main": "Назад в главное меню",
            "prompt": "Здесь вы можете оплатить подписку, посмотреть баланс или вернуться в главное меню."
        },
        "language_menu": {
            "english": "English",
            "back_to_main": "Назад в главное меню",
            "set_to_english": "Язык установлен: english"
        }
    },
    "en": {
        "main_menu": {
            "welcome": "Welcome! Choose an action:",
            "test1": "Korneslov Genesis 1:1",
            "test2": "Korneslov Genesis 3:1",
            "test3": "Korneslov John 11:35",
            "language": "Язык",
            "korneslov": "Korneslov",
            "payment": "Payment",
            "stats": "Statistics",
            "help": "Help",
            "title": "Main menu",
            "help_text": "This is the help for the bot. Here you will find information about its features and usage."
        },
        "korneslov_menu": {
            "masoret": "Masoret",
            "rishi": "Rishi",
            "back_to_main": "Back to main menu",
            "title": "Korneslov",
            "prompt": """Choose available options below. If the menu is not displayed, tap the square icon with dots in the lower right. Available directions:
 • <b>Masoret</b> — Old Testament Hebrew studies.
 • <b>Rishi</b> — Sanskrit studies: Shrimad Bhagavatam.
 • <b>Something else</b> — something else...
\nEach direction contains its own difficulty submenu.

______________"""
        },
        "masoret_menu": {
            "light": "For fun",
            "smart": "Details",
            "hard": "Academic",
            "back_to_korneslov": "Back to Korneslov",
            "prompt": """<b>Masoret</b> — choose the difficulty level:
The answer may consist of an incomplete set of available parts (0-3). The available parts are:
— <b>Part 0 — Text of the line</b>
— <b>Part 1 — Detailed word-by-word information</b>
— <b>Part 2 — Roots and their base meanings</b>
— <b>Part 3 — Chains of base meanings</b>

Depending on your choice, you get various parts. Levels:
• <b>For fun</b> — Easy. Parts 0, 3.
• <b>Details</b> — Medium. Parts 0, 2, 3.
• <b>Academic</b> — All parts: 0, 1, 2, 3.

After choosing a level, send your request like:

<b>Korneslov Book Chapter:Verse</b>

Example: Korneslov Genesis 1:1

______________"""
,
            "level_set": "Level set"
        },
        "rishi_menu": {
            "light": "For fun",
            "smart": "Details",
            "hard": "Academic",
            "back_to_korneslov": "Back to Korneslov",
            "prompt": "Rishi — choose an action:",
        },
        "oplata_menu": {
            "back_to_main": "Back to main menu",
            "prompt": "Here you can pay for your subscription, check your balance, or return to the main menu."
        },
        "language_menu": {
            "english": "English",
            "back_to_main": "Back to main menu",
            "set_to_english": "Language set to: english"
        }
    }
}

def tr(key, msg=None, user_id=None, default_lang="ru", **kwargs):
    ## Define user_id from msg (if sent), of from param, else fallback
    if msg is not None:
        user_id = msg.from_user.id
    lang = default_lang
    if user_id is not None:
        lang = get_user_state(user_id).get("lang", default_lang)
    ## Get message
    parts = key.split(".")
    d = MESSAGES.get(lang, MESSAGES.get(default_lang))
    for part in parts:
        d = d.get(part, {})
    if isinstance(d, str):
        return d.format(**kwargs)
    ## Return something nonempty to satisfy telegram.
    return "PUSTO"

