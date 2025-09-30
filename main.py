import asyncio
import logging
import re
import json
from itertools import groupby
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, CallbackQuery

from config import TELEGRAM_BOT_TOKEN, TRIBUTE_REQUEST_PRICE, TRIBUTE_PAYMENT_URL, USE_TRIBUTE, TESTMODE, TGPAYMENT_PHOTO, TGPAYMENT_PROVIDERS

from menu.base_menu import router, main_reply_keyboard, oplata_menu
from menu.tgpayment_menu import payment_confirmation_keyboard, get_currency_keyboard

from i18n.messages import tr
from texts.prompts import HELP_FORMAT
from korneslov import is_valid_korneslov_query, fetch_full_korneslov_response

##from utils.tribute import can_use, is_unlimited ## WILL DEPRECATED
from utils.utils import split_message, parse_references
from utils.userstate import get_user_state
from utils.tgpayments import get_provider_by_currency, can_use, is_unlimited, reset_payment_state

from db import get_conn
from db.books import find_book_entry
from db.users import upsert_user, get_user
from db.requests import add_request, update_request_response
from db.responses import add_response
##from db.tribute import get_user_amount, set_user_amount ## WILL DEPRECATED
from db.tgpayments import add_tgpayment, get_user_amount,  set_user_amount


##logging.basicConfig(level=logging.INFO)
##logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
dp.include_router(router)


## Critically required for continuation of payment process!! W/o it bot finished payment unsucc by timeout.
@dp.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    print("PRE_CHECKOUT:", pre_checkout_query.model_dump_json(indent=2))
    await pre_checkout_query.answer(ok=True)


def pay_keyboard_for(uid: int) -> InlineKeyboardMarkup:
    state = get_user_state(uid)
    url = f"{TRIBUTE_PAYMENT_URL}&uid={uid}"   ## Send user_id to to payment service!!
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr("tribute.pay_keyboard_for", lang=state['lang']), url=url)]
        ]
    )
    return kb


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    ## Set defaults on start
    state = get_user_state(message.from_user.id)
    state["method"] = "korneslov"
    state["direction"] = "masoret"
    state["level"] = "hard"
    state["lang"] = "ru"

    ## Log user to DB (upsert)
    user = message.from_user
    await upsert_user(
        user_id=user.id,
        firstname=user.first_name,
        lastname=user.last_name,
        username=user.username,
        lang=state.get("lang", "ru"),
        is_bot=user.is_bot
    )

    msg_text = tr("start.start_bot", lang=state['lang'])
    ## UI DBG
    msg_text += f"\n\n______________\nCurrent user_id: <code>{message.from_user.id}</code>\n<b>Current state:</b>\n<code>{json.dumps(state, ensure_ascii=False)}</code>"
    if TESTMODE:
        msg_text += tr("start.testmode_banner", lang=state['lang'])
    await message.answer(msg_text, reply_markup=main_reply_keyboard(), parse_mode="HTML")






## tgpayment block

@dp.callback_query(lambda c: c.data == "tgpay_confirm")
async def handle_tgpay_confirm(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id)
    currency = state.get("currency", "UAH")
    amount = state.get("amount")

    provider = get_provider_by_currency(currency)
    if not provider:
        await callback.message.answer(tr("tgpayment.tgbuy_invalid_currency", lang=state['lang'], currency=currency))
        await callback.answer()
        return

    if not amount or not str(amount).isdigit() or int(amount) <= 0:
        await callback.message.answer(tr("tgpayment.invalid_amount", lang=state['lang']))
        await callback.answer()
        return

    invoice_amount = int(amount) * 100

    await callback.message.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=tr("tgpayment.tgbuy_title", lang=state["lang"]),
        description=tr("tgpayment.tgbuy_desc", lang=state["lang"]),
        payload="balance_custom",
        provider_token=provider["provider_token"],
        currency=currency,
        prices=[LabeledPrice(label=tr("tgpayment.tgbuy_price_label", lang=state["lang"]), amount=invoice_amount)],
        start_parameter="buy_balance",
        photo_url=TGPAYMENT_PHOTO
    )
    await callback.answer()


@dp.message(lambda message: message.successful_payment is not None)
async def handle_successful_payment(message: types.Message):
    state = get_user_state(message.from_user.id)
    sp = message.successful_payment
    currency = sp.currency
    provider = get_provider_by_currency(currency)
    if not provider:
        await message.answer(tr("tgpayment.tgbuy_invalid_currency", lang=state['lang'], currency=currency))
        return

    exchange_rate = provider.get("exchange_rate", 1)  ## Default is 1

    ## Recount to base currency
    money_amount = int(sp.total_amount * exchange_rate / 100)

    tx_id = sp.provider_payment_charge_id or sp.telegram_payment_charge_id

    updated = await set_user_amount(
        message.from_user.id,
        money_amount,
        tx_id
    )

    ## Prepare other params to DB-write
    payload = getattr(sp, "invoice_payload", None)
    amount = money_amount
    datetime_val = datetime.now().isoformat()
    ## Func to serialize payment info.. some troubles with aiogram's json handlings
    def default_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    raw_json = json.dumps(message.model_dump(), default=default_serializer)

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
    if updated:
        await message.answer(tr("tgpayment.tgbuy_payment_successful", lang=state['lang'], money_amount=money_amount))
    else:
        await message.answer(tr("tgpayment.tgbuy_payment_repeat", lang=state['lang']))
    ## Show Payment menu - after payment process.
    await message.answer(
        tr("main_menu.welcome", lang=state['lang']),
        reply_markup=oplata_menu(msg=message, lang=state['lang'])
    )
    ## Afta succ payment - show main keyboard
    await message.answer(
        tr("main_menu.welcome", lang=state['lang']),
        reply_markup=main_reply_keyboard(msg=message, lang=state['lang'])
    )


## Callback func for show balance - instead of "/balance"
@dp.callback_query(lambda c: c.data == "tgpay_balance")
async def handle_balance_callback(callback: types.CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    balance = await get_user_amount(callback.from_user.id)
    await callback.message.answer(
        tr("tgpayment.balance_text", lang=lang, amount=balance)
    )
    await callback.answer()


## Pay option - choose currency
@dp.callback_query(lambda c: c.data == "tgpay_pay")
async def cmd_pay_callback(callback: types.CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    ## Flush flags befor menu forming (maybe no need)
    reset_payment_state(state)
    state["await_amount"] = False
    await callback.message.answer(
        tr("tgpayment.choose_currency", lang=lang),
        reply_markup=get_currency_keyboard(lang=lang)
    )
    await callback.answer()


## Choose currency from list. Next - enter sum.
@dp.callback_query(lambda c: c.data.startswith("tgpay_currency_"))
async def handle_currency_choice(callback: types.CallbackQuery):
    currency = callback.data.replace("tgpay_currency_", "")
    state = get_user_state(callback.from_user.id)
    state["await_amount"] = True
    state["currency"] = currency  ## Store chosen currency
    await callback.message.answer(
        tr("tgpayment.enter_amount", lang=state["lang"], currency=currency)
    )
    await callback.answer()


## Correct amount input (digits only)
@dp.message(lambda m: get_user_state(m.from_user.id).get("await_amount") is True and m.text.isdigit())
async def handle_amount_input(message: types.Message):
    state = get_user_state(message.from_user.id)
    lang = state.get("lang", "ru")
    amount = int(message.text)
    state["amount"] = amount
    state["await_amount"] = False
    await message.answer(
        tr("tgpayment.approve_amount", lang=lang, amount=amount, currency=state.get('currency', '')),
        reply_markup=payment_confirmation_keyboard(lang=lang)
    )


## Incorrect amount input (not a digits)
@dp.message(lambda m: get_user_state(m.from_user.id).get("await_amount") is True and not m.text.isdigit())
async def handle_wrong_amount(message: types.Message):
    state = get_user_state(message.from_user.id)
    lang = state.get("lang", "ru")
    await message.answer(tr("tgpayment.wrong_amount", lang=lang))
    ## Flush payment flags
    reset_payment_state(state)
    await message.answer(
        tr("oplata_menu.prompt", lang=lang),
        reply_markup=oplata_menu(lang=lang)
    )


@dp.callback_query(lambda c: c.data == "tgpay_back")
async def handle_tgpay_back(callback: CallbackQuery):
    state = get_user_state(callback.from_user.id)
    lang = state.get("lang", "ru")
    ## Flush awaiting amount/flags
    state.pop("await_amount", None)
    state.pop("amount", None)
    ## Return to Choose currency menu
    await callback.message.answer(
        tr("tgpayment.choose_currency", lang=state.get("lang", "ru")),
        reply_markup=get_currency_keyboard(lang=state.get("lang", "ru"))
    )
    await callback.answer()


## end of tgpayment


## Handle valid requests only.
@dp.message(is_valid_korneslov_query)
####async def handle_korneslov_query(message: types.Message):
async def handle_korneslov_query(message: types.Message, refs=None):
    text = message.text or ""
    uid = message.from_user.id
    state = get_user_state(uid)
    level = state.get("level", "hard")
    lang = state.get("lang", "ru")

    ## Check balance before request generation
    requests_left = await get_user_amount(uid)
    from config import TGPAYMENT_REQUEST_PRICES
    price = TGPAYMENT_REQUEST_PRICES.get(level, 1)
    ## check for unlim
    if requests_left != -1 and requests_left < price:
        kb = pay_keyboard_for(uid)
        await message.answer(
            tr("tribute.handle_korneslov_query_no_testmode_use_tribute", lang=state['lang']),
            reply_markup=kb, parse_mode="HTML"
        )
        return

    ## Logging user to DB (upsert)
    user = message.from_user
    await upsert_user(
        user_id=user.id,
        firstname=user.first_name,
        lastname=user.last_name,
        username=user.username,
        lang=lang,
        is_bot=user.is_bot
    )

    ## Save user request to DB
    req_id = await add_request(
        user_id=uid,
        user_state=state,
        request=text
    )

    ref = refs[0]
    book = ref["book"]
    chapter = ref["chapter"]
    verses = ref["verses"]

    ## Check is book exists in the DB
    async with await get_conn() as conn:
        row = await find_book_entry(book, conn)
    if not row:
        await message.answer(tr("handle_korneslov_query.book_not_found", book=book, lang=state['lang']))
        ## Refresh status as unsuccessful
        await update_request_response(req_id, status_oai=False, status_tg=False)
        return

    ## Format verses list (ex.: 1-3,5)
    def group_ranges(lst):
        ranges = []
        for k, g in groupby(enumerate(lst), lambda x: x[0]-x[1]):
            group = list(map(lambda x: x[1], g))
            if len(group) == 1:
                ranges.append(str(group[0]))
            else:
                ranges.append(f"{group[0]}-{group[-1]}")
        return ",".join(ranges)

    if len(verses) == 1:
        verses_str = str(verses[0])
    else:
        verses_str = group_ranges(verses)

    try:
        ## Response generation via Korneslov
        answer = await fetch_full_korneslov_response(
            book, chapter, verses_str, uid, level=level
        )
        for part in split_message(answer):
            part = re.sub(r'<br.*?>', '', part)
            await message.answer(part, parse_mode="HTML")
            await asyncio.sleep(2)
        ## Save response in `responses`
        await add_response(req_id, answer)
        ## Refresh status as successful
        await update_request_response(req_id, status_oai=True, status_tg=True)

        ## Decrement credits if not unlim and if success
        requests_left = await get_user_amount(uid)
        if requests_left != -1 and requests_left >= price:
            updated = await set_user_amount(uid, -price, str(req_id))
            print(f"DBG: New user balance for user {uid} — {requests_left - price}")

    except Exception as e:
        logging.exception(e)
        ## Refresh status as error
        await update_request_response(req_id, status_oai=False, status_tg=False)
        await message.answer(tr("tribute.handle_korneslov_query_exception", lang=state['lang']), parse_mode="HTML")


async def main():
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())

