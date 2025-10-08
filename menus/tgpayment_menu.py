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
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def oplata_menu(msg=None, lang="ru"):
    if msg is not None:
        lang = get_user_state(msg.from_user.id).get("lang", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr("tgpayment.pay_button", lang=lang), callback_data="tgpay_pay")],
        [InlineKeyboardButton(text=tr("tgpayment.balance_button", lang=lang), callback_data="tgpay_balance")],
    ])