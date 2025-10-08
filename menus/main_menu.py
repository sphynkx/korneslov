from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


def main_reply_keyboard(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("main_menu.test1", msg=msg)),
            KeyboardButton(text=tr("main_menu.test2", msg=msg)),
            KeyboardButton(text=tr("main_menu.test3", msg=msg))
        ],
        [
            KeyboardButton(text=tr("main_menu.language", msg=msg)),
            KeyboardButton(text=tr("main_menu.korneslov", msg=msg))
        ],
        [
            KeyboardButton(text=tr("main_menu.payment", msg=msg)),
            KeyboardButton(text=tr("main_menu.stats", msg=msg)),
            KeyboardButton(text=tr("main_menu.help", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)