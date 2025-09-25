from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import json
from utils.utils import get_statistics_text
from i18n.messages import tr
from utils.userstate import get_user_state

router = Router()


def main_reply_keyboard(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("main_menu.test1", msg=msg)),
            KeyboardButton(text=tr("main_menu.test2", msg=msg)),
            KeyboardButton(text=tr("main_menu.test3", msg=msg))
        ],
        [
            KeyboardButton(text=tr("main_menu.language", msg=msg)),
            KeyboardButton(text=tr("main_menu.korneslov", msg=msg))
        ],
        [
            KeyboardButton(text=tr("main_menu.payment", msg=msg)),
            KeyboardButton(text=tr("main_menu.stats", msg=msg)),
            KeyboardButton(text=tr("main_menu.help", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def korneslov_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("korneslov_menu.masoret", msg=msg)),
            KeyboardButton(text=tr("korneslov_menu.rishi", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("korneslov_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def masoret_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("masoret_menu.light", msg=msg)),
            KeyboardButton(text=tr("masoret_menu.smart", msg=msg)),
            KeyboardButton(text=tr("masoret_menu.hard", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("masoret_menu.back_to_korneslov", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def rishi_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("rishi_menu.light", msg=msg)),
            KeyboardButton(text=tr("rishi_menu.smart", msg=msg)),
            KeyboardButton(text=tr("rishi_menu.hard", msg=msg)),
        ],
        [
            KeyboardButton(text=tr("rishi_menu.back_to_korneslov", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def oplata_menu(msg=None):
    kb = [
        [
            KeyboardButton(text="/buy"),
            KeyboardButton(text="/tgbuy"),
            KeyboardButton(text="/balance"),
        ],
        [
            KeyboardButton(text=tr("oplata_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def language_menu(msg=None):
    kb = [
        [
            KeyboardButton(text=tr("language_menu.english", msg=msg))
        ],
        [
            KeyboardButton(text=tr("language_menu.back_to_main", msg=msg))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(lambda m: m.text == tr("main_menu.korneslov", msg=m))
async def handle_korneslov(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["method"] = "korneslov"
    ## Buggy - sets values to null. Below are identical.
    ##state["direction"] = None
    ##state["level"] = None
    await msg.answer(
        f"""{tr("korneslov_menu.prompt", msg=msg)}

______________
Current state:
<code>{json.dumps(state, ensure_ascii=False)}</code>""",
        reply_markup=korneslov_menu(msg=msg), parse_mode="HTML"
    )


@router.message(lambda m: m.text == tr("korneslov_menu.masoret", msg=m))
async def handle_masoret(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "masoret"
    ##state["level"] = None
    await msg.answer(
        f"""{tr("masoret_menu.prompt", msg=msg)}

______________
Current state:\n<code>{json.dumps(state, ensure_ascii=False)}</code>""",
        reply_markup=masoret_menu(msg=msg), parse_mode="HTML"
    )


@router.message(lambda m: m.text == tr("korneslov_menu.rishi", msg=m))
async def handle_rishi(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    state["direction"] = "rishi"
    ##state["level"] = None
    await msg.answer(
        f"{tr('rishi_menu.prompt', msg=msg)}\n\n______________\nCurrent state:\n<code>{json.dumps(state, ensure_ascii=False)}</code>",
        reply_markup=rishi_menu(msg=msg), parse_mode="HTML"
    )


@router.message(lambda m: m.text == tr("main_menu.payment", msg=m))
async def handle_oplata(msg: types.Message):
    await msg.answer(tr("oplata_menu.prompt", msg=msg), reply_markup=oplata_menu(msg=msg))


@router.message(lambda m: m.text == tr("oplata_menu.back_to_main", msg=m))
async def handle_back_to_main_from_oplata(msg: types.Message):
    await msg.answer(tr("main_menu.title", msg=msg), reply_markup=main_reply_keyboard(msg=msg))


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


@router.message(lambda m: m.text == tr("main_menu.language", msg=m))
async def handle_language_menu(msg: types.Message):
    state = get_user_state(msg.from_user.id)
    current_lang = state.get("lang", "ru")
    ## Swap language
    new_lang = "en" if current_lang == "ru" else "ru"
    state["lang"] = new_lang
    print("AFTA change:", get_user_state(msg.from_user.id))
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


@router.message(lambda m: m.text == tr("korneslov_menu.back_to_main", msg=m))
async def handle_back_to_main(msg: types.Message):
    await msg.answer(tr("main_menu.title", msg=msg), reply_markup=main_reply_keyboard(msg=msg))


@router.message(lambda m: m.text == tr("masoret_menu.back_to_korneslov", msg=m) or m.text == tr("rishi_menu.back_to_korneslov", msg=m))
async def handle_back_to_korneslov(msg: types.Message):
    await msg.answer(tr("korneslov_menu.title", msg=msg), reply_markup=korneslov_menu(msg=msg))


@router.message(lambda m: m.text == tr("main_menu.help", msg=m))
async def handle_help(msg: types.Message):
    await msg.answer(tr("main_menu.help_text", msg=msg), reply_markup=main_reply_keyboard(msg=msg))


@router.message(lambda m: m.text == tr("main_menu.stats", msg=m))
async def handle_statistika(msg: types.Message):
    await msg.answer(get_statistics_text(), parse_mode="HTML")


@router.message()
async def echo(msg: types.Message):
    state = get_user_state(msg.from_user.id)
##    await msg.answer(f"{tr('main_menu.unknown_command', msg=msg)}\n\n<code>{json.dumps(state, ensure_ascii=False)}</code>")
    await msg.answer(f"{tr('handle_korneslov_query.query_format_error', msg=msg)}\n\n<code>{json.dumps(state, ensure_ascii=False)}</code>")




