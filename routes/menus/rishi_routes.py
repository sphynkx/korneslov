import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state
from menus.rishi_menu import rishi_menu


router = Router()


@router.message(lambda m: m.text == tr("korneslov_menu.rishi", msg=m))
async def handle_rishi(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "rishi"
    await msg.answer(
        f"{tr('rishi_menu.prompt', msg=msg)}\n\n______________\nCurrent state:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=rishi_menu(msg=msg), parse_mode="HTML"
    )

