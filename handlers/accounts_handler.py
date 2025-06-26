from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.database_csv import CSVDatabase
import logging
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

ACCOUNTS_PER_PAGE = 5
STATUS_EMOJIS = {
    'hold': '🟡',
    'success': '🟢',
    'rejected': '🔴'  # Rejected are removed so usually 0
}

def format_account_status(counts: dict) -> str:
    return (
        f"📊 <b>Account Status</b>\n"
        f"{STATUS_EMOJIS['hold']} Hold: <b>{counts.get('hold', 0)}</b>\n"
        f"{STATUS_EMOJIS['success']} Success: <b>{counts.get('success', 0)}</b>\n"
        f"{STATUS_EMOJIS['rejected']} Rejected: <b>{counts.get('rejected', 0)}</b>\n"
    )

def format_account_list(accounts: list) -> str:
    if not accounts:
        return "No accounts found for this page."

    lines = []
    for acc in accounts:
        emoji = STATUS_EMOJIS.get(acc['status'].lower(), '⚪')
        try:
            date = datetime.strptime(acc['timestamp'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%b %d, %Y')
        except Exception:
            date = acc['timestamp']
        
        lines.append(
            f"{emoji} <code>{acc['id']}</code> | "
            f"<b>{acc['status'].capitalize()}</b> | "
            f"<i>{date}</i>"
        )
    return "\n".join(lines)

def build_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if total_pages > 1:
        if current_page > 0:
            builder.button(text="⬅️ Previous", callback_data=f"accounts_page:{current_page - 1}")
        if current_page < total_pages - 1:
            builder.button(text="➡️ Next", callback_data=f"accounts_page:{current_page + 1}")
    return builder.as_markup()

async def send_accounts_message(
    message_or_callback: types.Message | types.CallbackQuery,
    page: int = 0
) -> None:
    user_id = message_or_callback.from_user.id
    db = CSVDatabase()

    try:
        status_counts = db.get_account_status(user_id)
        accounts = db.get_user_accounts(
            user_id,
            limit=ACCOUNTS_PER_PAGE,
            offset=page * ACCOUNTS_PER_PAGE
        )
        
        total_accounts = sum(status_counts.values())
        total_pages = max(1, (total_accounts + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        
        response = (
            "📋 <b>Your Accounts</b>\n\n"
            f"{format_account_status(status_counts)}\n"
            f"📌 <b>Page {page + 1}/{total_pages}</b>\n\n"
            f"{format_account_list(accounts)}"
        )
        
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(
                response,
                reply_markup=build_pagination_keyboard(page, total_pages),
                parse_mode="HTML"
            )
            logger.info(f"Sent accounts message for user {user_id}, page {page}")
        else:
            await message_or_callback.message.edit_text(
                response,
                reply_markup=build_pagination_keyboard(page, total_pages),
                parse_mode="HTML"
            )
            logger.info(f"Edited accounts message for user {user_id}, page {page}")
            
    except Exception as e:
        logger.error(f"Error processing accounts for user {user_id}, page {page}: {e}", exc_info=True)
        error_msg = "⚠️ Error retrieving accounts. Please try again later."
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(error_msg)
        else:
            await message_or_callback.message.edit_text(error_msg)


@router.message(F.text == "📋 My accounts")
async def handle_my_accounts(message: types.Message):
    logger.info(f"Account request from user {message.from_user.id}")
    await send_accounts_message(message)

@router.callback_query(F.data.startswith("accounts_page:"))
async def handle_accounts_page(callback: types.CallbackQuery):
    _, page = callback.data.split(":")
    await send_accounts_message(callback, int(page))
    await callback.answer()
