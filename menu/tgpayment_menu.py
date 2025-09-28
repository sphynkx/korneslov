from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TGPAYMENT_PROVIDERS
from utils.userstate import get_user_state
from i18n.messages import tr



def payment_confirmation_keyboard(lang="ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr("tgpayment.back", lang=lang), callback_data="tgpay_back")],
        [InlineKeyboardButton(text=tr("tgpayment.make_payment", lang=lang), callback_data="tgpay_confirm")]
    ])


def get_currency_keyboard(lang="ru"):
    ## Gather all uniq currencies
    currencies = list({p["currency"] for p in TGPAYMENT_PROVIDERS})
    keyboard = []
    for cur in currencies:
        keyboard.append([InlineKeyboardButton(
            text=f"{cur}",  ## Here could set translation or symbol for currency
            callback_data=f"tgpay_currency_{cur}"
        )])
    keyboard.append([
        InlineKeyboardButton(
            text=tr("oplata_menu.back_to_main", lang=lang),
            callback_data="tgpay_back_to_payment_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

