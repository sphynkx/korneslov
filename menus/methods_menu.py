from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


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