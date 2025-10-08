from aiogram import Router, types

from utils.utils import get_statistics_text


router = Router()


## Will be filtered upstream by exact text in the aggregator
@router.message(lambda m: m.text == "Statistics" or True)  
async def handle_statistika(msg: types.Message):
    await msg.answer(get_statistics_text(), parse_mode="HTML")

