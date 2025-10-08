from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


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