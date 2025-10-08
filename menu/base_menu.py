from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from i18n.messages import tr
from utils.userstate import get_user_state


def main_reply_keyboard(msg=None, lang="ru"):
    kb = [
        [
            KeyboardButton(text=tr("main_menu.test1", msg=msg, lang=lang)),
            KeyboardButton(text=tr("main_menu.test2", msg=msg, lang=lang)),
            KeyboardButton(text=tr("main_menu.test3", msg=msg, lang=lang))
        ],
        [
            KeyboardButton(text=tr("main_menu.language", msg=msg, lang=lang)),
            KeyboardButton(text=tr("main_menu.korneslov", msg=msg, lang=lang))
        ],
        [
            KeyboardButton(text=tr("main_menu.payment", msg=msg, lang=lang)),
            KeyboardButton(text=tr("main_menu.stats", msg=msg, lang=lang)),
            KeyboardButton(text=tr("main_menu.help", msg=msg, lang=lang))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def korneslov_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("korneslov_menu.masoret", msg=msg)),
            KeyboardButton(text=tr("korneslov_menu.rishi", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("korneslov_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def masoret_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("masoret_menu.light", msg=msg)),
            KeyboardButton(text=tr("masoret_menu.smart", msg=msg)),
            KeyboardButton(text=tr("masoret_menu.hard", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("masoret_menu.back_to_korneslov", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def rishi_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("rishi_menu.light", msg=msg)),
            KeyboardButton(text=tr("rishi_menu.smart", msg=msg)),
            KeyboardButton(text=tr("rishi_menu.hard", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("rishi_menu.back_to_korneslov", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def oplata_menu(msg=None, lang="ru"):
    if msg is not None:
        lang = get_user_state(msg.from_user.id).get("lang", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr("tgpayment.pay_button", lang=lang), callback_data="tgpay_pay")],
        [InlineKeyboardButton(text=tr("tgpayment.balance_button", lang=lang), callback_data="tgpay_balance")],
    ])


def language_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("language_menu.english", msg=msg))
        ],
        [
            KeyboardButton(text=tr("language_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)