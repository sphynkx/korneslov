import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state


router = Router()


@router.message(lambda m: m.text in [tr("masoret_menu.light", msg=m), tr("masoret_menu.smart", msg=m), tr("masoret_menu.hard", msg=m)])
async def handle_level_choice(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    level_map = {
        tr("masoret_menu.light", msg=msg): "light",
        tr("masoret_menu.smart", msg=msg): "smart",
        tr("masoret_menu.hard", msg=msg): "hard"
    }
    state["level"] = level_map.get(msg.text, "hard")
    await msg.answer(
        f"{tr('masoret_menu.level_set', msg=msg)}: {msg.text}\n\n______________\nCurrent state:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        parse_mode="HTML"
    )

