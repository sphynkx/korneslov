import json

from aiogram import Router, types

from i18n.messages import tr
from utils.userstate import get_user_state
from menus.main_menu import main_reply_keyboard


router = Router()


@router.message(lambda m: m.text == tr("main_menu.language", msg=m))
async def handle_language_menu(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    current_lang = state.get("lang", "ru")
    ## Swap language
    new_lang = "en" if current_lang == "ru" else "ru"
    state["lang"] = new_lang
    print("DBG: Lang AFTA change:", get_user_state(msg.from_user.id))
    ## Send new menu with new keyboard and welcome-msg.
    await msg.answer(
        tr("main_menu.welcome", msg=msg),
        reply_markup=main_reply_keyboard(msg=msg)
    )


## Now this button probably lost.. No need??
@router.message(lambda m: m.text == tr("language_menu.english", msg=m))
async def handle_language_english(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["lang"] = "en"
    await msg.answer(
        f"{tr('language_menu.set_to_english', msg=msg)}\n\n______________\nCurrent state:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        parse_mode="HTML"
    )