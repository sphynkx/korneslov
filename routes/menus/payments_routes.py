from aiogram import Router, types

from i18n.messages import tr
from menus.tgpayment_menu import oplata_menu
from menus.main_menu import main_reply_keyboard


router = Router()


@router.message(lambda m: m.text == tr("main_menu.payment", msg=m))
async def handle_oplata(msg: types.Message):
    await msg.answer(tr("oplata_menu.prompt", msg=msg), reply_markup=oplata_menu(msg=msg))


@router.message(lambda m: m.text == tr("oplata_menu.back_to_main", msg=m))
async def handle_back_to_main_from_oplata(msg: types.Message):
    await msg.answer(tr("main_menu.title", msg=msg), reply_markup=main_reply_keyboard(msg=msg))