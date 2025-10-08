from aiogram import Router, types

from i18n.messages import tr
from menus.main_menu import main_reply_keyboard
from menus.directions_menu import korneslov_menu


router = Router()


@router.message(lambda m: m.text == tr("korneslov_menu.back_to_main", msg=m))
async def handle_back_to_main(msg: types.Message):
    await msg.answer(tr("main_menu.title", msg=msg), reply_markup=main_reply_keyboard(msg=msg))


@router.message(lambda m: m.text == tr("masoret_menu.back_to_korneslov", msg=m) or m.text == tr("rishi_menu.back_to_korneslov", msg=m))
async def handle_back_to_korneslov(msg: types.Message):
    await msg.answer(tr("korneslov_menu.title", msg=msg), reply_markup=korneslov_menu(msg=msg))

