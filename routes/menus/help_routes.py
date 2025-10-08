from aiogram import Router, types

from i18n.messages import tr
from menus.main_menu import main_reply_keyboard


router = Router()


@router.message(lambda m: m.text == tr("main_menu.help", msg=m))
async def handle_help(msg: types.Message):
    await msg.answer(tr("main_menu.help_text", msg=msg), reply_markup=main_reply_keyboard(msg=msg))