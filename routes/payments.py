import json
from datetime import datetime, date

from aiogram import exceptions ## BEFORE other aiogram imports!!
from aiogram import Router, types
from aiogram.types import CallbackQuery, LabeledPrice

from i18n.messages import tr
from utils.userstate import get_user_state
from utils.tgpayments import get_provider_by_currency, reset_payment_state
from db.tgpayments import add_tgpayment, get_user_amount, set_user_amount
from menus.tgpayment_menu import oplata_menu, get_currency_keyboard, payment_confirmation_keyboard
from menus.main_menu import main_reply_keyboard
from config import TGPAYMENT_PHOTO
import logging

router = Router()


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    print("PRE_CHECKOUT:", pre_checkout_query.model_dump_json(indent=2))
    await pre_checkout_query.answer(ok=True)


@router.callback_query(lambda c: c.data == "tgpay_confirm")
async def handle_tgpay_confirm(callback: types.CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    currency = state.get("currency", "UAH")
    invoice_amount_cents = state.get("invoice_amount_cents")
    koreshoks = state.get("koreshoks")

    provider = get_provider_by_currency(currency)
    if not provider:
        await callback.message.answer(tr("tgpayment.tgbuy_invalid_currency", lang=lang, currency=currency))
        await callback.answer()
        return

    if not invoice_amount_cents or not isinstance(invoice_amount_cents, int) or invoice_amount_cents <= 0:
        await callback.message.answer(tr("tgpayment.invalid_amount", lang=lang))
        await callback.answer()
        return

    try:
        await callback.message.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=tr("tgpayment.tgbuy_title", lang=lang),
            description=tr("tgpayment.tgbuy_desc", lang=lang),
            payload=f"balance_koreshoks:{koreshoks}",
            provider_token=provider["provider_token"],
            currency=currency,
            prices=[LabeledPrice(label=tr("tgpayment.tgbuy_price_label", lang=lang), amount=invoice_amount_cents)],
            start_parameter="buy_balance",
            photo_url=TGPAYMENT_PHOTO
        )
    except exceptions.TelegramBadRequest as e:
        ## Handle provider errors
        logging.exception("send_invoice failed: %s", e)
        reset_payment_state(state)
        if "PAYMENT_PROVIDER_INVALID" in str(e):
            await callback.message.answer(tr("tgpayment.provider_invalid", lang=lang, currency=currency))
            try: await callback.answer()
            except: pass
            return
        else:
            await callback.message.answer(tr("tgpayment.invoice_send_failed", lang=lang))
            try: await callback.answer()
            except: pass
            return

    try:
        await callback.answer()
    except: pass


@router.message(lambda m: get_user_state(m.from_user.id).get("await_amount") is True and m.text and m.text.isdigit())
async def handle_amount_input(message: types.Message):
    state = get_user_state(message.from_user.id)
    lang = state.get("lang", "ru")
    koreshoks = int(message.text)
    if koreshoks <= 0:
        await message.answer(tr("tgpayment.invalid_amount", lang=lang))
        reset_payment_state(state)
        await message.answer(tr("oplata_menu.prompt", lang=lang), reply_markup=oplata_menu(lang=lang))
        return

    ## Save Koreshki and compute amount in chosen currency
    state["koreshoks"] = koreshoks
    state["await_amount"] = False

    currency = state.get("currency", "UAH")
    provider = get_provider_by_currency(currency)
    if not provider:
        await message.answer(tr("tgpayment.tgbuy_invalid_currency", lang=lang, currency=currency))
        reset_payment_state(state)
        return

    exchange_rate = provider.get("exchange_rate", 1)  ## koreshoks per 1 major currency unit
    ## major_amount = koreshoks / exchange_rate  (units of currency)
    if exchange_rate == 0:
        await message.answer(tr("tgpayment.provider_invalid", lang=lang, currency=currency))
        reset_payment_state(state)
        return

    major_amount = koreshoks / exchange_rate
    ## invoice_amount in smallest currency unit (cents/kopecks)
    invoice_amount_cents = int(round(major_amount * 100))

    ## Save prepared invoice amount
    state["invoice_amount_cents"] = invoice_amount_cents

    ## Show approvement: Koreshki and real currency amount
    tgpayment.approve_amount_conversion
    await message.answer(
        tr("tgpayment.approve_amount_conversion", lang=lang,
           koreshoks=koreshoks,
           real_amount=f"{major_amount:.2f}",
           currency=currency),
        reply_markup=payment_confirmation_keyboard(lang=lang)
    )


@router.message(lambda m: get_user_state(m.from_user.id).get("await_amount") is True and (not m.text or not m.text.isdigit()))
async def handle_wrong_amount(message: types.Message):
    state = get_user_state(message.from_user.id)
    lang = state.get("lang", "ru")
    await message.answer(tr("tgpayment.wrong_amount", lang=lang))
    reset_payment_state(state)
    await message.answer(
        tr("oplata_menu.prompt", lang=lang),
        reply_markup=oplata_menu(lang=lang)
    )


@router.callback_query(lambda c: c.data == "tgpay_balance")
async def handle_balance_callback(callback: types.CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    balance = await get_user_amount(callback.from_user.id)
    await callback.message.answer(
        tr("tgpayment.balance_text", lang=lang, amount=balance)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "tgpay_pay")
async def cmd_pay_callback(callback: types.CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    reset_payment_state(state)
    state["await_amount"] = False
    await callback.message.answer(
        tr("tgpayment.choose_currency", lang=lang),
        reply_markup=get_currency_keyboard(lang=lang)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("tgpay_currency_"))
async def handle_currency_choice(callback: types.CallbackQuery):
    currency = callback.data.replace("tgpay_currency_", "")
    state = get_user_state(callback.from_user.id)
    ## Ask Koreshki amount
    state["await_amount"] = True
    state["currency"] = currency
    await callback.message.answer(
        tr("tgpayment.enter_amount_koreshoks", lang=state.get("lang", "ru"), currency=currency)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "tgpay_back")
async def handle_tgpay_back(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id)
    state.pop("await_amount", None)
    state.pop("amount", None)
    await callback.message.answer(
        tr("tgpayment.choose_currency", lang=state.get("lang", "ru")),
        reply_markup=get_currency_keyboard(lang=state.get("lang", "ru"))
    )
    await callback.answer()


## Back button for currencies list
@router.callback_query(lambda c: c.data == "tgpay_back2")
async def handle_tgpay_back2(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    ## Flush amount if was entered
    state.pop("await_amount", None)
    state.pop("amount", None)
    await callback.message.answer(
        tr("oplata_menu.prompt", lang=lang),
        reply_markup=oplata_menu(lang=lang)
    )
    await callback.answer()


## Back button for Payment+Balance message
@router.callback_query(lambda c: c.data == "tgpay_main_back")
async def handle_tgpay_main_back(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    reset_payment_state(state)
    await callback.message.answer(
        tr("main_menu.title", lang=lang),
        reply_markup=main_reply_keyboard(msg=callback.message)
    )
    await callback.answer()


@router.message(lambda message: message.successful_payment is not None)
async def handle_successful_payment(message: types.Message):
    state = get_user_state(message.from_user.id)
    sp = message.successful_payment
    currency = sp.currency
    provider = get_provider_by_currency(currency)
    if not provider:
        await message.answer(tr("tgpayment.tgbuy_invalid_currency", lang=state['lang'], currency=currency))
        return

    ## exchange_rate = koreshoks per 1 major currency unit
    exchange_rate = provider.get("exchange_rate", 1)

    ## sp.total_amount is in smallest currency units (cents / kopecks)
    ## koreshoks_paid = (sp.total_amount / 100) * exchange_rate
    koreshoks_paid = int(sp.total_amount * exchange_rate / 100)

    tx_id = sp.provider_payment_charge_id or sp.telegram_payment_charge_id

    ## Atomically add koreshoks to user's balance. set_user_amount expects delta in internal units.
    updated = await set_user_amount(
        message.from_user.id,
        koreshoks_paid,
        tx_id
    )

    payload = getattr(sp, "invoice_payload", None)
    amount = koreshoks_paid
    datetime_val = datetime.now().isoformat()

    def default_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    raw_json = json.dumps(message.model_dump(), default=default_serializer)

    ## Store payment record: amount should be in koreshoks (internal unit)
    await add_tgpayment(
        user_id=message.from_user.id,
        payload=payload,
        amount=amount,
        currency=currency,
        status="paid",
        provider_payment_charge_id=sp.provider_payment_charge_id,
        telegram_payment_charge_id=sp.telegram_payment_charge_id,
        datetime_val=datetime_val,
        raw_json=raw_json,
    )

    ## Notify user: use koreshoks_paid in message
    if updated:
        await message.answer(tr("tgpayment.tgbuy_payment_successful", lang=state['lang'], money_amount=koreshoks_paid))
    else:
        await message.answer(tr("tgpayment.tgbuy_payment_repeat", lang=state['lang']))

    ## Return user to menus
    await message.answer(
        tr("main_menu.welcome", lang=state['lang']),
        reply_markup=oplata_menu(msg=message, lang=state['lang'])
    )
    await message.answer(
        tr("main_menu.welcome", lang=state['lang']),
        reply_markup=main_reply_keyboard(msg=message)
    )

