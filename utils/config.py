from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)


# Logs Channel ID
LOGS_CHANNEL_ID = os.getenv("LOGS_CHANNEL_ID")

# Admin IDs
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(',')]

# Webmail Domains (for manual use)
WEBMAIL_DOMAINS = [
    "temp-mail.io",
    "mail.cx",
    "getnada.cc"
]