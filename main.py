import asyncio

from aiogram import Bot, Dispatcher

from aiohttp import ClientTimeout
from aiogram.client.session.aiohttp import AiohttpSession
from config import TG_POLLING_TIMEOUT, TG_SOCK_CONNECT_TIMEOUT, TG_SOCK_READ_TIMEOUT

from config import TELEGRAM_BOT_TOKEN

from routes.errors import router as errors_router

from routes.commands.commands import router as commands_router
from routes.payments import router as payments_router
from routes.methods.korneslov_mtd import router as methods_router

from routes.menus.methods_routes import router as menu_methods_router
from routes.menus.masoret_routes import router as menu_masoret_router
from routes.menus.rishi_routes import router as menu_rishi_router
from routes.menus.levels_routes import router as menu_levels_router
from routes.menus.payments_routes import router as menu_payments_router
from routes.menus.language_routes import router as menu_language_router
from routes.menus.main_routes import router as menu_main_router
from routes.menus.help_routes import router as menu_help_router
from routes.menus.statistics_routes import router as menu_stats_router
from routes.menus.echo_routes import router as menu_echo_router


##logging.basicConfig(level=logging.INFO)
##logging.basicConfig(level=logging.DEBUG)

timeout = ClientTimeout(total=None, sock_connect=TG_SOCK_CONNECT_TIMEOUT, sock_read=TG_SOCK_READ_TIMEOUT)
session = AiohttpSession(timeout=timeout)


bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

## IMPORTANT:
## 0. Global error-router must be connected first - before any other routes!!
dp.include_router(errors_router)

## IMPORTANT: routers must include in the strait order:
## 1. commands_router — command handlers like /start
## 2. payments_router — intercept amount inputs before generic text handlers
## 3. methods_router — parse biblical refs like "genesis 1 1"
## 4. menu_* routers — menus and other generic handlers
## 5. menu_echo_router — must be last
dp.include_router(commands_router)
dp.include_router(payments_router)
dp.include_router(methods_router)

dp.include_router(menu_methods_router)
dp.include_router(menu_masoret_router)
dp.include_router(menu_rishi_router)
dp.include_router(menu_levels_router)
dp.include_router(menu_payments_router)
dp.include_router(menu_language_router)
dp.include_router(menu_main_router)
dp.include_router(menu_help_router)
dp.include_router(menu_stats_router)

dp.include_router(menu_echo_router)


async def main():
##    await dp.start_polling(bot)
    await dp.start_polling(bot, polling_timeout=TG_POLLING_TIMEOUT)


if __name__ == "__main__":
    asyncio.run(main())
