import logging
import asyncio
from datetime import datetime
import html
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOGS_CHANNEL_ID = os.getenv("LOGS_CHANNEL_ID")

class TelegramLogHandler(logging.Handler):
    def __init__(self, bot: Bot, chat_id: str | int):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            record = await self.queue.get()
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=record,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception as e:
                print(f"Failed to send log message to Telegram: {e}")
            self.queue.task_done()

    def emit(self, record):
        try:
            emoji_map = {
                "DEBUG": "🐛",
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🆘",
            }
            emoji = emoji_map.get(record.levelname, "📌")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = (
                f"{emoji} <b>{record.levelname.title()}</b>\n"
                f"🕒 <i>{timestamp}</i>\n"
                f"📝 {html.escape(record.getMessage())}\n"
                f"━━━━━━━━━━━━━━"
            )
            # Schedule putting the message in the async queue
            asyncio.create_task(self.queue.put(message))
        except Exception:
            self.handleError(record)


async def create_telegram_log_handler():
    if not BOT_TOKEN or not LOGS_CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or LOGS_CHANNEL_ID missing in environment variables")

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    return TelegramLogHandler(bot, LOGS_CHANNEL_ID)
