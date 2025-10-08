import json

from aiogram import Router, types
from aiogram.filters import Command

from i18n.messages import tr
from menus.main_menu import main_reply_keyboard
from utils.userstate import get_user_state
from db.users import upsert_user


router = Router()


@router.message(Command("start"))
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
    await message.answer(msg_text, reply_markup=main_reply_keyboard(), parse_mode="HTML")