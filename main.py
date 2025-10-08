import asyncio

from aiogram import Bot, Dispatcher

from config import TELEGRAM_BOT_TOKEN

from routes.commands.commands import router as commands_router
from routes.payments import router as payments_router
from routes.methods.korneslov_mtd import router as methods_router
from routes.menus.base_menu_routes import router as base_router


##logging.basicConfig(level=logging.INFO)
##logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

## IMPORTANT: routers include order
## 1) commands_router — command handlers like /start
## 2) payments_router — intercept amount inputs before generic text handlers
## 3) methods_router — parse biblical refs like "genesis 1 1"
## 4) base_router — menus and other generic handlers
dp.include_router(commands_router)
dp.include_router(payments_router)
dp.include_router(methods_router)
dp.include_router(base_router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())