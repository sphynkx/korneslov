import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state
from menus.directions_menu import korneslov_menu


router = Router()


@router.message(lambda m: m.text == tr("main_menu.korneslov", msg=m))
async def handle_korneslov(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["method"] = "korneslov"
    ## Buggy - sets values to null. Below are identical.
    ##state["direction"] = None
    ##state["level"] = None
    await msg.answer(
        tr("korneslov_menu.prompt", msg=msg),
        reply_markup=korneslov_menu(msg=msg), parse_mode="HTML"
    )

