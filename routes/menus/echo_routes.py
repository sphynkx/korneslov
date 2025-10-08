import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state


router = Router()


@router.message()
async def echo(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    await msg.answer(f"{tr('handle_korneslov_query.query_format_error', msg=msg)}\n\n<code>{json.dumps(state, ensure_ascii=False)}</code>")