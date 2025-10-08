from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from i18n.messages import tr


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

