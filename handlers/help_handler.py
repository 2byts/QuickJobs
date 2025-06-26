from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import logging

router = Router()
logger = logging.getLogger(__name__)

def get_help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Creating Account", callback_data="help_creating_account")],
            [InlineKeyboardButton(text="💸 Withdraw", callback_data="help_withdraw")],
            [InlineKeyboardButton(text="📞 Contact Support", callback_data="help_contact_support")]
        ]
    )

def get_help_message() -> str:
    return (
        "🛠 *Help Center* 🛠\n\n"
        "Select a topic below to get more information:\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "We're here to assist you with any questions!"
    )

async def show_help_menu(message_or_call: types.Message | types.CallbackQuery):
    try:
        if isinstance(message_or_call, types.Message):
            await message_or_call.answer(
                get_help_message(),
                reply_markup=get_help_keyboard(),
                parse_mode="Markdown"
            )
            logger.debug(f"Help menu sent for user {message_or_call.from_user.id}")
        else:
            await message_or_call.message.edit_text(
                get_help_message(),
                reply_markup=get_help_keyboard(),
                parse_mode="Markdown"
            )
            logger.debug(f"Help menu edited for user {message_or_call.from_user.id}")
    except TelegramBadRequest as e:
        logger.debug(f"Help menu update failed: {e}")

@router.message(F.text == "❓ Help")
async def help_command(message: types.Message):
    await show_help_menu(message)

@router.callback_query(F.data.startswith("help_"))
async def help_callback_handler(callback: types.CallbackQuery):
    help_topic = callback.data.split("_", 1)[1]  # safer in case there's more than one "_"
    logger.debug(f"Help callback: {help_topic} from user {callback.from_user.id}")

    responses = {
        "creating_account": (
            "📝 *Creating Account*\n\n"
            "To create an account:\n"
            "1. Click on /start\n"
            "2. Follow the registration process\n"
            "Need more help? Contact support!"
        ),
        "withdraw": (
            "💸 *Withdraw Funds*\n\n"
            "To withdraw your earnings:\n"
            "1. Ensure you have at least $1.00\n"
            "3. Select payment method\n"
            "4. Enter your wallet details\n\n"
            "Processing time: 1-2 hours\n"
            "Minimum withdrawal: $1.00"
        ),
        "contact_support": (
            "📞 *Contact Support*\n\n"
            "Need more help? Contact our support team:\n"
        "- Email: mainincivi1s@gmail.com\n"
        "- Telegram: t.me/arafathosenzihad\n"
        "- WhatsApp: Message Arafat Hoshen Zihad on WhatsApp https://wa.me/8801710094115\n"
        "- Hours: 24/7\n\n"
            "Please include your User ID in messages:\n"
            f"`{callback.from_user.id}`\n\n"
            "We'll respond within 12 hours!"
        )
    }

    if help_topic == "back":
        await show_help_menu(callback)
        return

    response_text = responses.get(help_topic, "Sorry, this help topic isn't available right now.")

    try:
        await callback.message.edit_text(
            response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Back to Help Menu", callback_data="help_back")]
                ]
            )
        )
    except TelegramBadRequest as e:
        logger.debug(f"Message edit failed: {e}")
    
    await callback.answer()

@router.callback_query(F.data == "help_back")
async def help_back_handler(callback: types.CallbackQuery):
    await show_help_menu(callback)
