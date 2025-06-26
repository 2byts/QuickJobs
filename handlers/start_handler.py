from aiogram import Router, types 
from aiogram.filters import Command
from utils.config import ADMIN_IDS
from utils.database_csv import CSVDatabase
import logging

router = Router()
logger = logging.getLogger(__name__)

# Define custom keyboard
keyboard = [
    [types.KeyboardButton(text="📲 Register a New FB")],
    [types.KeyboardButton(text="💰 Balance"), types.KeyboardButton(text="📋 My accounts")],
    [types.KeyboardButton(text="❓ Help")]
]
markup = types.ReplyKeyboardMarkup(
    keyboard=keyboard,
    resize_keyboard=True
)

@router.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    db = CSVDatabase()

    # Insert user to database (handle errors if needed)
    try:
        await db.add_user(user_id, username)  # Ensure this is an async function
        logger.info(f"User {user_id} ({username}) added to database.")
    except Exception as e:
        logger.warning(f"Failed to add user {user_id} to database: {e}")

    # Send message
    if user_id in ADMIN_IDS:
        await message.reply("👑 Welcome Admin! Choose an option:", reply_markup=markup)
    else:
        await message.reply("👋 Welcome to QuickFB Jobs!\n\n"
    "We’re glad to have you here.\n"
    "This bot helps you easily register and manage Facebook jobs in a secure and efficient way.\n\n"
    "Please choose one of the options below to get started:", reply_markup=markup)
