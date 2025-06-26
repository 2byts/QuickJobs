import os
import logging
import asyncio
from aiogram import Bot, Dispatcher
from log_handler import create_telegram_log_handler
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Import your CSV database class (ensure handlers import/use it as needed)
from utils.database_csv import CSVDatabase

# Import handlers
from handlers import (
    start_handler,
    admin_handler,
    help_handler,
    registration_handler,
    balance_handler,
    accounts_handler,
    
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(logging.FileHandler("bot.log"))
    root_logger.addHandler(logging.StreamHandler())

    # Create and add Telegram log handler
    telegram_log_handler = await create_telegram_log_handler()
    root_logger.addHandler(telegram_log_handler)

# ==================== Main Bot Setup ====================

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Setup basic logging to console and file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ],
    )

    # Include routers
    for router in [
        start_handler.router,
        balance_handler.router,
        admin_handler.router,
        accounts_handler.router,
        help_handler.router,
        registration_handler.router, 
    ]:
        dp.include_router(router)
        logging.info(f"Included router: {router.__class__.__name__}")

    logging.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Bot crashed: {e}", exc_info=True)
    finally:
        logging.info("Closing bot session...")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Fatal error in main: {e}", exc_info=True)
