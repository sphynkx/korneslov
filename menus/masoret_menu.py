from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


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

