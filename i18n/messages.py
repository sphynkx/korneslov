from utils.userstate import get_user_state

MESSAGES = {
    "ru": {
        "start": {
            "start_bot": """<b>"Корнеслов"</b> - это телеграм-бот для комплексного лингвинистического анализа текстов Ветхого завета по оригинальной авторской методике.

Подробности работы и использования - см. раздел "Помощь".

Для оплаты нажмите кнопку "Оплата".

Прайс:
Минимальный запрос - 10 руб.
Подробный запрос - 20 руб.
Расширенный запрос - 30 руб.
            """,
            "testmode_banner": "\n\n<b>Тестовый режим: оплата и баланс отключены.</b>",
        },

        "main_menu": {
            "welcome": "Добро пожаловать! Выберите действие:",
            "test1": "бытие 1 1",
            "test2": "бытие 3 1",
            "test3": "тест 1 2",
            "language": "Language",
            "korneslov": "Корнеслов",
            "payment": "Оплата",
            "stats": "Статистика",
            "help": "Справка",
            "title": "Главное меню",
            "help_text": """<b>Запросы:</b>
Предусмотрено 3 уровня сложности запросов: базовый, подробный и академичный. Для выбора уровня нажмите на кнопку "Корнеслов", затем на "Масорет" и потом на одну из кнопок "Базовый", "Подробнее" или "Академичный". 

<b>Важно:</b>
• Разные уровни сложности запросов имеют различную стоимость. 
• Стоимость запросов выражена в "корешках" - внутренней "валюте" бота. Расценки:
  • "Базовый" - 1 корешок
  • "Подробнее" - 2 корешка
  • "Академичный" - 3 корешка
• Бот работает достаточно медленно. Поэтому отправив запрос - подождите несколько минут, не пытайтесь отправлять запрос заново.

<b>Использование:</b>
Выберите доступные опции в меню ниже. Если меню не отображено, нажмите на значок квадрата с точками справа внизу.
Для разбора текста нажмите на кнопку "Корнеслов" и выберите нужные опции в его подменю. Затем отправьте запрос в формате:
<b>книга глава стих</b>
Напр.: 
<i>бытие 1 1</i>
<i>бытие 1 2,3</i>
<i>бытие 1 4,6-8,10-12,14</i>

Иногда вместо полезного ответа бот может выдать ошибку. В этом случае плата не взимается. Просто повторите запрос.
                """,
            "unknown_command": "ERRORA!!"
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
"""
        },
        "masoret_menu": {
            "light": "Базовый",
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
• <b>Базовый</b> - Простой разбор. Выводятся части 0 и 3.
• <b>Подробнее</b> - Более сложный разбор. Выводятся части 0, 2 и 3.
• <b>Академично</b> - Максимально глубокий и основательный разбор. Выводятся все части - 0, 1, 2 и 3.

После выбора уровня сложности не забудьте отправить запрос. Напишите его в формате:

<b>книга глава стих(и)</b>

Напр.: 
<i>бытие 1 1</i>
<i>бытие 1 2,3</i>
<i>бытие 1 4,6-8,10-12,14</i>
""",
            "level_set": "Установлен уровень"
        },
        "rishi_menu": {
            "light": "Базовый",
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
        },
        "tgpayment": {
            "show_balance": "Ваш баланс: <b>{requests_left}</b> корешков.",
            "tgbuy_title": "Пополнение баланса",
            "balance_button": "Баланс",
            "balance_text": "Ваш текущий баланс: {amount} кредитов.",## todo - rework to real money and currencies
            "tgbuy_desc": "Покупка \"корешков\" к Корнеслову",
            "tgbuy_price_label": "10 кредитов",## where is??
            "tgbuy_payment_successful": "Оплата прошла!! Баланс пополнен на {money_amount} кредитов.",## todo - rework to real money and currencies (???)
            "tgbuy_payment_repeat": "Этот платеж уже был обработан ранее.",
            "tgbuy_invalid_currency": "Неподдерживаемая валюта. Попробуйте еще раз.",
            "choose_currency": "Выберите валюту для оплаты:",
            "enter_amount": "Введите сумму оплаты в {currency}:",
            "pay_button": "Оплатить",
            "approve_amount": "Сумма для оплаты: {amount} {currency}\n\nВыберите действие:",
            "invalid_amount": "Некорректная сумма, попробуйте еще раз.",
            "make_payment": "Произвести оплату",
            "back": "Назад",
            "low_amount": "❌ У вас нет доступных запросов.\nПожалуйста, пополните баланс:", ## used twice
            "provider_invalid": "Выбранная валюта не поддерживается провайдером оплаты. Пожалуйста, выберите другую валюту или попробуйте позже.",
        },
        "handle_korneslov_query": {
            "query_format_error": "Неверный формат запроса. Пример: бытие 1 1-3,5",
            "book_not_found": "Книга «{book}» не найдена в базе. Проверьте правильность названия.",
            "handle_korneslov_query_exception": "Произошла ошибка генерации. Повторите запрос позже.",
        },
        "korneslov_py": {
            "dummy_openai_response_return": "Корнеслов: {book} {chapter} {verse}\n<br>{dummy_text}",
            "ask_openai_no_OPENAI_API_KEY": "Корнеслов: {book} {chapter} {verse}\n(Ошибка: не указан ключ OpenAI или не установлен пакет openai){test_banner}",
            "ask_openai_return": "Корнеслов", ## inserted into f-string
            "ask_openai_exception_logging": "Ошибка при обращении к OpenAI",
            "ask_openai_exception_return": "Корнеслов: {book} {chapter} {verse}\n(Ошибка обращения к ChatGPT. Попробуйте позже.)",
        },
        "errors": {
            "db_unavailable": "Временные проблемы с базой данных. Пожалуйста, повторите попытку позже.",
            "message_parse_failed": "Ошибка при форматировании сообщения, отправляю упрощенный текст.",
            "unexpected": "Произошла внутренняя ошибка. Мы уже в курсе.",
        },
    },

########### ENGLISH ###########

    "en": {
        "start": {
            "start_bot": """<b>Korneslov</b> is a Telegram bot for comprehensive linguistic analysis of Old Testament texts using the author's original methodology.

For details on how to use it, see the "Help" section.

To pay, click the "Pay" button.

Price:
Minimum request - 0.1 EUR.
Detailed request - 0.2 EUR.
Advanced request - 0.3 EUR.
            """,
            "testmode_banner": "\n\n<b>Test mode: payment and balance are disabled.</b>",
            },
        "main_menu": {
            "welcome": "Welcome! Choose an action:",
            "test1": "genesis 1 1",
            "test2": "genesis 3 1",
            "test3": "test 1 2",
            "language": "Язык",
            "korneslov": "Korneslov",
            "payment": "Payment",
            "stats": "Statistics",
            "help": "Help",
            "title": "Main menu",
            "help_text": """<b>Queries:</b>
There are 3 levels of query difficulty: Basic, Detailed, and Academic. To select a level, click the "Korneslov" button, then "Masoret," and then one of the buttons: "Basic," "Detailed," or "Academic."

<b>Important:</b>
• Different query difficulty levels have different costs.
• Queries are priced in "koreshoks"—the bot's internal currency. Rates:
• "Basic" - 1 koreshok
• "Detailed" - 2 koreshoks
• "Academic" - 3 koreshoks
• The bot is quite slow. Therefore, after sending a query, please wait a few minutes; do not try to send it again.

<b>Usage:</b>
Select available options from the menu below. If the menu is not visible, click the square with dots icon in the lower right corner. To parse the text, click the "Root Book" button and select the desired options from the submenu. Then send a request in the following format:
<b>book chapter verse</b>
For example:
<i>Genesis 1:1</i>
<i>Genesis 1:2,3</i>
<i>Genesis 1:4,6-8,10-12,14</i>

Sometimes, instead of a useful answer, the bot may return an error. In this case, no fee is charged. Simply repeat the request.
            """
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
"""
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

<b>book chapter verse(s)</b>

Example: 
<i>genesis 1 1</i>
<i>genesis 1 2,3</i>
<i>genesis 1 4,6-8,10-12,14</i>
""",
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
        },
        "tgpayment": {
            "show_balance": "Your balance: <b>{requests_left}</b> koreshoks.",
            "tgbuy_title": "Balance replenishment",
            "balance_button": "Balance",
            "balance_text": "Your current balance: {amount} credits.",## todo - rework to real money and currencies
            "tgbuy_desc": "Buy koreshoks to Korneslov",
            "tgbuy_price_label": "10 credits",## where is??
            "tgbuy_payment_successful": "Payment completed!! Balance refilled by {money_amount} credits.",## todo - rework to real money and currencies (???)
            "tgbuy_payment_repeat": "This payment has already been processed.",
            "tgbuy_invalid_currency": "Unsupported currency. Try again.",
            "choose_currency": "Choose currency for payment:",
            "enter_amount": "Enter amount for payment in {currency}:",
            "pay_button": "Pay",
            "approve_amount": "Payment amount: {amount} {currency}\n\nChoose option:",
            "invalid_amount": "Incorrect value. Try again.",
            "make_payment": "Make a payment",
            "back": "Back",
            "low_amount": "❌ You have not available requests.\nPlease recharge your balance:", ## used twice
            "provider_invalid": "The selected currency is not supported by the payment provider. Please select a different currency or try again later.",
        },
        "handle_korneslov_query": {
            "query_format_error": "Query format error. Example: genesis 1 1-3,5",
            "book_not_found": "The book «{book}» not found in DB. Please check book name.",
            "handle_korneslov_query_exception": "A generation error occurred. Please try again later.",
        },
        "korneslov_py": {
            "dummy_openai_response_return": "Korneslov: {book} {chapter} {verse}\n{dummy_text}",
            "ask_openai_no_OPENAI_API_KEY": "Korneslov: {book} {chapter} {verse}\n(Error: No OpenAI key specified or openai package not installed){test_banner}",
            "ask_openai_return": "Korneslov", ## inserted into f-string
            "ask_openai_exception_logging": "OpenAI request failed",
            "ask_openai_exception_return": "Korneslov: {book} {chapter} {verse}\n(Error during request to ChatGPT. Try later.)",
        },
        "errors": {
            "db_unavailable": "There are temporary problems with the database. Please try again later..",
            "message_parse_failed": "There was an error formatting the message. I'm sending a simplified text.",
            "unexpected": "An internal error occurred. We're already aware of it.",
        },
    }
}


##def tr(key, msg=None, user_id=None, default_lang="ru", **kwargs):
def tr(key, caller=None, msg=None, user_id=None, lang="ru", **kwargs):
    ## Define user_id from msg (if sent), of from param, else fallback
    ##print(f"DBG: tr() called with key={key}, caller={caller}, kwargs={kwargs}")
    if msg is not None:
        user_id = msg.from_user.id
    if user_id is not None:
        lang = get_user_state(user_id).get("lang", lang)
    ## Get message
    parts = key.split(".")
    d = MESSAGES.get(lang, MESSAGES.get(lang))
    for part in parts:
        d = d.get(part, {})
    if isinstance(d, str):
        return d.format(**kwargs)
    ## Return something nonempty to satisfy telegram.
    return "PUSTO"

