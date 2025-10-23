import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state
from menus.masoret_menu import masoret_menu


router = Router()


@router.message(lambda m: m.text == tr("korneslov_menu.masoret", msg=m))
async def handle_masoret(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "masoret"
    await msg.answer(
        tr("masoret_menu.prompt", msg=msg),
        reply_markup=masoret_menu(msg=msg), parse_mode="HTML"
    )

