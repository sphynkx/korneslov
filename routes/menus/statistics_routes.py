from aiogram import Router, types
from utils.utils import get_statistics_text
from utils.userstate import get_user_state

router = Router()


## Will be filtered upstream by exact text in the aggregator
@router.message(lambda m: m.text == "Statistics" or True)  
async def handle_statistika(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    await msg.answer(get_statistics_text(state, msg.from_user.id), parse_mode="HTML")

