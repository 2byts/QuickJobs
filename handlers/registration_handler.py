import random
import re
import string
import time
import logging
import requests

import pyotp
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from utils.database_csv import CSVDatabase
from utils.config import ADMIN_IDS, LOGS_CHANNEL_ID, bot
from . import RegistrationStates

router = Router()
logger = logging.getLogger(__name__)
db = CSVDatabase()

first_names = [
    "Rahim", "Karim", "Hasan", "Jahid", "Amina", "Fatema", "Rumana", "Sajjad", "Rafi", "Tania", "Nusrat",
    "Fahim", "Samiul", "Rakib", "Sabbir", "Sadia", "Jannat", "Mizan", "Kawsar", "Sumaiya", "Sultana",
    "Shuvo", "Munna", "Shanto", "Naim", "Sakib", "Morshed", "Nishat", "Shohag", "Masud", "Sumon",
    "Jubayer", "Farzana", "Mim", "Nabila", "Shahriar", "Emon", "Niloy", "Tushar", "Zahid", "Mahfuz",
    "Afsana", "Tanjila", "Rabbi", "Tuhin", "Mehedi", "Tamim", "Nafisa", "Rafsan", "Arafat", "Imran",
    "Asif", "Towhid", "Ovi", "Rasel", "Rasel", "Sohan", "Rayhan", "Sohanur", "Shamim", "Shohel", "Shams",
    "Tariq", "Ridoy", "Shakil", "Nadim", "Sifat", "Salman", "Arif", "Ifty", "Shanto", "Yasin", "Sadi",
    "Arman", "Tariqul", "Hridoy", "Faisal", "Iftekhar", "Tanzim", "Omar", "Hamid", "Mahmud", "Wasim",
    "Shorif", "Alif", "Mahi", "Rana", "Kamal", "Shimul", "Anik", "Noman", "Hasib", "Nayem", "Samin",
    "Oishi", "Priya", "Lamia", "Aklima", "Rokeya", "Mahira", "Farhana", "Shamima", "Nusrat", "Maliha",
    "Tonni", "Riya", "Nishi", "Mim", "Tumpa", "Nargis", "Keya", "Nodi", "Brishti", "Nabila", "Shila",
    "Rokhshana", "Parvin", "Nasima", "Marufa", "Jerin", "Sharmin", "Minu", "Rumana", "Sanjida", "Shormi",
    "Mouri", "Lima", "Shathi", "Jui", "Sinthia", "Rokhshana", "Faria", "Sadia", "Moumita", "Ritika",
    "Zannat", "Sumaiya", "Anamika", "Trisha", "Sanjana", "Farzana", "Afia", "Jerin", "Afsara", "Afrin",
    "Nusrat", "Tarannum", "Tamanna", "Ishrat", "Tahiya", "Anika", "Lubna", "Sadia", "Maliha", "Shamima",
    "Bushra", "Ahona", "Rupkotha", "Pranto", "Pavel", "Ehsan", "Rafiul", "Ruhul", "Abir", "Nafis",
    "Ishmam", "Noman", "Adib", "Tanvir", "Sajib", "Farhan", "Zunayed", "Tasin", "Tawhid", "Jayed",
    "Touhid", "Emon", "Saklain", "Ashik", "Sohanur", "Shahriar", "Omar", "Tanjim", "Mamun", "Helal",
    "Badhon", "Rasel", "Shamol", "Ripon", "Milton", "Badsha", "Nazmul", "Habib", "Khairul", "Latif",
    "Barkat", "Wahid", "Hossen", "Rubel", "Masum", "Selim", "Mokhles", "Motaleb", "Mobarak", "Sabuj",
    "Bokul", "Liton", "Zubair", "Zakir", "Azad", "Ruhul", "Manik", "Kabir", "Basir", "Mostafizur", "Lutfar",
    "Noor", "Shawon", "Aminul", "Anamul", "Rasel", "Saddam", "Habibur", "Kamrul", "Shamim", "Ashraful"
]

last_names = [
    "Khan", "Ahmed", "Islam", "Rahman", "Hasan", "Hossain", "Uddin", "Chowdhury", "Mollah", "Biswas",
    "Sarkar", "Mia", "Mian", "Bhuiyan", "Talukder", "Siddique", "Kabir", "Azad", "Rashid", "Karim",
    "Alam", "Mahmud", "Kamal", "Salam", "Mazumder", "Bhuiya", "Shikder", "Patwary", "Howlader", "Faruk",
    "Munshi", "Naser", "Shaikh", "Sharif", "Morshed", "Bokshi", "Hasnat", "Mostafa", "Haque", "Halder",
    "Rana", "Nabi", "Babu", "Sabbir", "Ahsan", "Mallick", "Tarek", "Sobhan", "Zaman", "Shuvo",
    "Rafique", "Mujib", "Sumon", "Saif", "Naim", "Raihan", "Tanim", "Shakil", "Siddiq", "Jahan",
    "Amin", "Bashar", "Mahfuz", "Sohag", "Rasel", "Kawsar", "Khokon", "Fahad", "Towhid", "Rayhan",
    "Mehedi", "Shanto", "Imran", "Babu", "Sajib", "Jamal", "Monir", "Tuhin", "Tanvir", "Ovi",
    "Raihan", "Tushar", "Niloy", "Biplob", "Jubayer", "Sagar", "Rafsan", "Arafat", "Sohail", "Noman",
    "Anik", "Rakib", "Sohan", "Mahi", "Shamim", "Masum", "Rubel", "Saddam", "Mamun", "Faisal"
]


def generate_password() -> str:
    return ''.join(random.choices(string.ascii_lowercase, k=6)) + time.strftime('%d')

async def notify_admin_about_account(user_id: int, data: dict):
    text = (
        f"🆕 New Account Registered\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"🔐 Password: <code>{data['password']}</code>\n"
        f"👤 Name: {data['first_name']} {data['last_name']}\n"
        f"📘 Facebook ID: <code>{data.get('facebook_id', 'N/A')}</code>\n"
        f"🔑 2FA Key: <code>{data.get('two_step_key', 'N/A')}</code>\n"
        f"📧 Webmail: <code>{data.get('webmail', 'N/A')}</code>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_{user_id}_{data['password']}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_{user_id}_{data['password']}")
    ]])

    try:
        await bot.send_message(chat_id=LOGS_CHANNEL_ID, text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to notify admin: {e}")

def check_facebook_account(fuid: str) -> bool | None:
    url = f"https://www.facebook.com/{fuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            page_text = response.text.lower()
            if ("page isn't available" in page_text) or ("content isn't available" in page_text):
                return False  # Not alive or deactivated
            else:
                return True  # Account exists
        elif response.status_code == 404:
            return False  # Not found
        else:
            return None  # Could not determine
    except requests.RequestException as e:
        logger.warning(f"Facebook check request failed: {e}")
        return None


@router.message(F.text == "📲 Register a New FB")
async def register_fb(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    password = generate_password()
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)

    db.add_user(user_id, username)
    reg_data = {"first_name": first_name, "last_name": last_name, "password": password}
    db.store_registration_data(user_id, reg_data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ DONE", callback_data="done_registration")],
        [InlineKeyboardButton(text="❌ CANCEL", callback_data="cancel_registration")]
    ])

    await message.reply(
        f"👤 First Name : `{first_name}`\n"
        f"👤 Last Name  : `{last_name}`\n"
        f"🔐 Password   : `{password}`\n\n"
        "📧 *Use your own Gmail account to register.*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "done_registration")
async def done_registration_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = db.get_registration_data(user_id)
    await callback.message.edit_reply_markup()
    if not data:
        await callback.message.answer("❗ No registration data found. Please start again.")
        return
    await callback.message.answer("📌 Please send your Facebook ID or profile URL to continue.")
    await state.set_state(RegistrationStates.awaiting_facebook_id)


@router.callback_query(F.data == "cancel_registration")
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    db.clear_registration_data(user_id)
    await callback.message.edit_reply_markup()
    await callback.message.answer("❌ Registration cancelled and data deleted.")
    await state.clear()


@router.message(RegistrationStates.awaiting_facebook_id, F.text)
async def handle_facebook_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    reg_data = db.get_registration_data(user_id)
    if not reg_data:
        await message.answer("❗ Registration data not found.")
        await state.clear()
        return

    text = message.text.strip()
    fb_id = None
    if text.startswith("https://www.facebook.com/"):
        match = re.search(r'/([0-9]+)', text)
        fb_id = match.group(1) if match else None
    elif text.isdigit():
        fb_id = text

    if not fb_id:
        await message.reply("⚠️ Please enter a valid Facebook numeric ID or profile URL.")
        return

    # Check Facebook account live status
    status = check_facebook_account(fb_id)

    if status is True:
        reg_data["facebook_id"] = fb_id
        db.store_registration_data(user_id, reg_data)
        await message.reply("✅ Facebook ID verified and saved.\n\n🔐 Now send your *Two-Step Verification Key*.", parse_mode="Markdown")
        await state.set_state(RegistrationStates.awaiting_two_step_key)

    elif status is False:
        await message.reply("❌ Facebook ID not found or deactivated. Please enter a valid Facebook numeric ID or profile URL.")

    else:
        await message.reply("⚠️ Unable to verify Facebook ID at the moment. Please try again later.")


@router.message(RegistrationStates.awaiting_two_step_key, F.text)
async def handle_two_step_key(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    reg_data = db.get_registration_data(user_id)
    key = message.text.strip().replace(" ", "").upper()

    if not re.fullmatch(r'[A-Z2-7]{16,32}', key):
        await message.reply("❗ Invalid format. Provide a base32 key (A-Z, 2-7).")
        return

    reg_data["two_step_key"] = key
    db.store_registration_data(user_id, reg_data)

    totp = pyotp.TOTP(key)
    code = totp.now()
    seconds_left = 30 - (int(time.time()) % 30)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"twofa_done_{user_id}"),
            InlineKeyboardButton(text="🔄 Update", callback_data=f"twofa_update_{user_id}")
        ]
    ])

    await message.reply(
        f"🔐 Your current 2FA code is: `{code}`\n"
        f"⏳ Expires in `{seconds_left}` seconds\nConfirm if it's correct.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(RegistrationStates.awaiting_twofa_confirm)


@router.callback_query(F.data.startswith("twofa_done_"))
async def twofa_done_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await callback.message.answer("✅ 2FA confirmed. Now send your temporary webmail address.")
    await state.set_state(RegistrationStates.awaiting_webmail)


@router.callback_query(F.data.startswith("twofa_update_"))
async def twofa_update_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = db.get_registration_data(user_id)
    if not data or "two_step_key" not in data:
        await callback.answer("❗ Key missing. Please resend.")
        return
    totp = pyotp.TOTP(data["two_step_key"])
    code = totp.now()
    seconds_left = 30 - (int(time.time()) % 30)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"twofa_done_{user_id}"),
            InlineKeyboardButton(text="🔄 Update", callback_data=f"twofa_update_{user_id}")
        ]
    ])

    await callback.message.edit_text(
        f"🔐 Updated 2FA Code: `{code}`\n⏳ Expires in `{seconds_left}` seconds",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer("🔄 Code refreshed")


@router.message(RegistrationStates.awaiting_webmail, F.text)
async def handle_webmail(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    reg_data = db.get_registration_data(user_id)
    email = message.text.strip().lower()
    domain = email.split("@")[-1]
    allowed_domains = [
        "mailto.plus", "fexpost.com", "fexbox.org", "mailbox.in.ua", "rover.info",
        "chitthi.in", "fextemp.com", "any.pink", "merepost.com"
    ]
    if not any(domain == d or domain.endswith("." + d) for d in allowed_domains):
        await message.reply("❌ Invalid email. Use mailto.plus or other allowed services.")
        return

    reg_data["webmail"] = email
    db.store_registration_data(user_id, reg_data)

    fb_id = reg_data.get("facebook_id")
    if fb_id:
        db.add_hold_balance_for_facebook_id(user_id, fb_id, 0.50)  # updated to $0.50
        hold = db.get_hold_balance_for_facebook_id(user_id, fb_id)
    else:
        hold = 0.0

    await message.reply(
        f"✅ Webmail `{email}` saved.\n<b>{fb_id or 'N/A'}</b>\n"
        f"______________________________\n<b>${hold:.2f}</b> credited to hold.\n\n"
        "📛 Add 30 friends and logout.",
        parse_mode="HTML"
    )
    await notify_admin_about_account(user_id, reg_data)
    await state.clear()
