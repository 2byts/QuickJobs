import csv
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.database_csv import CSVDatabase
from utils.config import LOGS_CHANNEL_ID, ADMIN_IDS, bot

# Setup UTF-8 safe logging (Windows consoles often default to cp1252)
import sys
import codecs
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = Router()
db = CSVDatabase(base_path="data")


class WithdrawStates(StatesGroup):
    awaiting_binance_id = State()


@router.message(F.text.lower() == "💰 balance")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    main_balance = db.get_user_main_balance(user_id)
    hold_balances_list = db._read_all_hold_balances()
    hold_balance = 0.0
    for row in hold_balances_list:
        if row["user_id"] == str(user_id):
            hold_balance += db._normalize_balance(row.get("hold_balance", 0))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Withdraw All", callback_data="withdraw_all")]
    ])

    response = (
        "💳 *Your Balance Summary* 💳\n\n"
        "✨ *Total Earnings:*\n"
        f"   ${main_balance + hold_balance:.2f} USD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *Available Balance:*\n"
        f"   ${main_balance:.2f} USD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⏳ *Hold Balance:*\n"
        f"   ${hold_balance:.2f} USD\n\n"
        "🔹 Minimum withdrawal: $1.00"
    )
    await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "withdraw_all")
async def withdraw_all_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    main_balance = db.get_user_main_balance(user_id)

    if main_balance < 1.0:
        await callback.answer("❌ You need at least $1.00 in your main balance to withdraw.", show_alert=True)
        return

    await callback.message.edit_text(
        "💳 *Withdraw All Funds*\n\n"
        f"Your available balance is: ${main_balance:.2f}\n\n"
        "Please send your *Binance ID* to receive the withdrawal.\n\n"
        "⚠️ Only Binance withdrawals are supported.\n\n"
        "Send /cancel to abort.",
        parse_mode="Markdown"
    )
    await state.set_state(WithdrawStates.awaiting_binance_id)
    await callback.answer()


@router.message(WithdrawStates.awaiting_binance_id, F.text)
async def process_binance_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    binance_id = message.text.strip()

    if binance_id.lower() == "/cancel":
        await message.reply("❌ Withdrawal cancelled.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return

    main_balance = db.get_user_main_balance(user_id)
    if main_balance < 1.0:
        await message.reply("❌ Insufficient balance to withdraw. Withdrawal requires minimum $1.00.")
        await state.clear()
        return

    success = db.add_withdrawal(
        user_id=user_id,
        amount=main_balance,
        wallet=binance_id,
        payment_method="Binance",
        status="pending"
    )
    if not success:
        await message.reply("⚠️ Failed to create withdrawal request. Please try again later.")
        await state.clear()
        return

    db.update_user_main_balance(user_id, 0.0)

    # Admin inline keyboard to approve/reject
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Mark Paid",
                callback_data=f"admin_withdraw_paid_{user_id}_{binance_id}"
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"admin_withdraw_reject_{user_id}_{binance_id}"
            )
        ]
    ])

    await message.reply(
        f"✅ Withdrawal request sent!\n\n"
        f"Amount: ${main_balance:.2f}\n"
        f"Method: Binance\n"
        f"Binance ID: {binance_id}\n\n"
        "⏳ Status: Pending approval.\n"
        "You will be notified once processed.",
        reply_markup=None  # User message no buttons
    )

    # Notify admins with inline buttons
    notify_text = (
        f"💰 *New Withdrawal Request*\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"💵 Amount: ${main_balance:.2f}\n"
        f"📤 Payment Method: Binance\n"
        f"🔢 Binance ID: {binance_id}\n"
        f"⏰ Timestamp: {message.date.isoformat()}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, notify_text, parse_mode="Markdown", reply_markup=admin_keyboard)
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")

    try:
        await bot.send_message(LOGS_CHANNEL_ID, notify_text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Failed to notify logs channel: {e}")

    await state.clear()


@router.callback_query(F.data.startswith("admin_withdraw_paid_"))
async def handle_withdraw_paid(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("Invalid data format.", show_alert=True)
        return

    _, _, action, user_id_str, *binance_id_parts = parts
    binance_id = "_".join(binance_id_parts)
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer("Invalid user ID.", show_alert=True)
        return

    withdrawals = db.get_all_withdrawals()
    updated = False
    for w in withdrawals:
        if w["user_id"] == str(user_id) and w["wallet"] == binance_id and w["status"] == "pending":
            w["status"] = "paid"
            updated = True
            break

    if not updated:
        await callback.answer("No matching pending withdrawal found.", show_alert=True)
        return

    try:
        with open(db.withdrawals_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "user_id", "amount", "wallet", "method", "status", "timestamp"])
            for w in withdrawals:
                writer.writerow([w["id"], w["user_id"], w["amount"], w["wallet"], w["method"], w["status"], w["timestamp"]])
    except Exception as e:
        logger.error(f"Failed to update withdrawal status to paid: {e}")
        await callback.answer("Failed to update withdrawal status.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Withdrawal marked as PAID for User ID: <code>{user_id}</code>, Binance ID: {binance_id}.",
        parse_mode="HTML"
    )
    await callback.answer("Withdrawal marked as paid.")


@router.callback_query(F.data.startswith("admin_withdraw_reject_"))
async def handle_withdraw_reject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Unauthorized.", show_alert=True)
        return

    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("Invalid data format.", show_alert=True)
        return

    _, _, action, user_id_str, *binance_id_parts = parts
    binance_id = "_".join(binance_id_parts)
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer("Invalid user ID.", show_alert=True)
        return

    withdrawals = db.get_all_withdrawals()
    new_withdrawals = [
        w for w in withdrawals
        if not (w["user_id"] == str(user_id) and w["wallet"] == binance_id and w["status"] == "pending")
    ]

    if len(new_withdrawals) == len(withdrawals):
        await callback.answer("No matching pending withdrawal found.", show_alert=True)
        return

    try:
        with open(db.withdrawals_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "user_id", "amount", "wallet", "method", "status", "timestamp"])
            for w in new_withdrawals:
                writer.writerow([w["id"], w["user_id"], w["amount"], w["wallet"], w["method"], w["status"], w["timestamp"]])
    except Exception as e:
        logger.error(f"Failed to remove withdrawal request: {e}")
        await callback.answer("Failed to remove withdrawal request.", show_alert=True)
        return

    await callback.message.edit_text(
        f"❌ Withdrawal request REJECTED and removed for User ID: <code>{user_id}</code>, Binance ID: {binance_id}.",
        parse_mode="HTML"
    )
    await callback.answer("Withdrawal request rejected and removed.")
