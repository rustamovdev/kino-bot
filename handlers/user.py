from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from states import UserStates
from keyboards import (
    main_menu_kb,
    cancel_kb,
    subscribe_kb,
    categories_kb,
    search_results_kb,
    vip_menu_kb,
)
from utils import check_subscription, is_admin, get_required_channel
from config import CHANNEL_ID, STICKER_ID
from emoji_helper import answer_ui, send_ui, edit_ui

router = Router()


WELCOME_TEXT = (
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "🎬 Kino botimizga xush kelibsiz.\n\n"
    "🍿 Ushbu bot orqali siz:\n\n"
    "🔎 Kino nomi bo'yicha izlash\n"
    "🎲 Tasodifiy kino olish\n"
    "📂 Kategoriyalar bo'yicha izlash\n"
    "💎 VIP kinolarni ko'rish\n"
    "📦 Kino buyurtma qilish\n\n"
    "imkoniyatiga egasiz.\n\n"
    "❗ <b>Eslatma:</b>\n"
    "Kino kodini yoki nomini vergul va ortiqcha belgilar ishlatmasdan yuboring."
)

HELP_TEXT = (
    "💡 <b>Yordam bo'limi</b>\n\n"
    "🔹 Kino kodini bilsangiz — shunchaki raqamni yuboring. Masalan: <code>125</code>\n"
    "🔹 <b>🔎 Kino izlash</b> — kino nomi bo'yicha qidirish\n"
    "🔹 <b>🎲 Random kino</b> — tasodifiy kino olish\n"
    "🔹 <b>📂 Kategoriyalar</b> — janrlar bo'yicha kinolarni ko'rish\n"
    "🔹 <b>💎 VIP</b> — VIP a'zolik haqida ma'lumot\n"
    "🔹 <b>📦 Kino buyurtma qilish</b> — topolmagan kinongizni so'rang\n\n"
    "❓ Qo'shimcha savollar bo'lsa, administratorga murojaat qiling."
)

VIP_TEXT = (
    "💎 <b>VIP a'zolik</b>\n\n"
    "✨ VIP a'zolar uchun maxsus imkoniyatlar:\n\n"
    "🎬 Eksklyuziv VIP kinolarga kirish\n"
    "⚡ Tezkor xizmat ko'rsatish\n"
    "🎁 Maxsus takliflar va yangiliklar\n\n"
    "💬 VIP a'zolik olish uchun administrator bilan bog'laning."
)


async def send_welcome(message: Message):
    try:
        if STICKER_ID:
            await message.answer_sticker(STICKER_ID)
    except Exception:
        pass
    await answer_ui(message, WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_new = await db.add_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
    )
    if await db.is_banned(message.from_user.id):
        await answer_ui(message, "🚫 Siz botdan foydalanish huquqidan mahrum qilingansiz.")
        return

    if not await check_subscription(message.bot, message.from_user.id):
        channel = await get_required_channel()
        await answer_ui(message, 
            "📢 <b>Botdan foydalanish uchun quyidagi kanalga a'zo bo'ling:</b>",
            reply_markup=subscribe_kb(channel),
        )
        return

    await send_welcome(message)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    if await check_subscription(callback.bot, callback.from_user.id):
        await callback.message.delete()
        await send_welcome(callback.message)
    else:
        await callback.answer("❗ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)


@router.message(F.text == "Bekor qilish")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await answer_ui(message, "🔙 Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(F.text == "Yordam")
async def help_menu(message: Message):
    await answer_ui(message, HELP_TEXT, reply_markup=main_menu_kb())


@router.message(F.text == "VIP")
async def vip_menu(message: Message):
    user_vip = await db.is_vip(message.from_user.id)
    text = VIP_TEXT
    if user_vip:
        text = "💎 <b>Siz allaqachon VIP a'zosiz!</b>\n\nBarcha VIP kinolar sizga ochiq. 🎉"
    await answer_ui(message, text, reply_markup=vip_menu_kb(user_vip))


@router.callback_query(F.data == "vip_info")
async def vip_info_cb(callback: CallbackQuery):
    await callback.answer()
    await answer_ui(callback.message, 
        "💬 VIP a'zolik olish uchun administratorga yozing."
    )


@router.message(F.text == "Kategoriyalar")
async def categories_menu(message: Message):
    cats = await db.all_categories()
    if not cats:
        await answer_ui(message, "📂 Hozircha kategoriyalar mavjud emas.")
        return
    await answer_ui(message, 
        "📂 <b>Quyidagi kategoriyalardan birini tanlang:</b>",
        reply_markup=categories_kb(cats),
    )


@router.callback_query(F.data.startswith("cat:"))
async def category_movies_cb(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    movies = await db.movies_by_category(category)
    await callback.answer()
    if not movies:
        await answer_ui(callback.message, f"📂 <b>{category}</b> kategoriyasida hozircha kino yo'q.")
        return
    await answer_ui(callback.message, 
        f"📂 <b>{category}</b> kategoriyasidagi kinolar:",
        reply_markup=search_results_kb(movies),
    )


@router.message(F.text == "Random kino")
async def random_movie_handler(message: Message):
    movie = await db.random_movie()
    if not movie:
        await answer_ui(message, "😔 Hozircha bazada kinolar mavjud emas.")
        return
    await deliver_movie(message.bot, message.chat.id, message.from_user.id, movie)


@router.message(F.text == "Kino izlash")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_search_query)
    await answer_ui(message, 
        "🔎 <b>Qidirmoqchi bo'lgan kino nomini yozing:</b>",
        reply_markup=cancel_kb(),
    )


@router.message(UserStates.waiting_search_query)
async def search_process(message: Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()
    movies = await db.search_movies(query)
    if not movies:
        await answer_ui(message, 
            "😔 Hech narsa topilmadi. Boshqa nom bilan urinib ko'ring yoki "
            "📦 <b>Kino buyurtma qilish</b> orqali so'rov qoldiring.",
            reply_markup=main_menu_kb(),
        )
        return
    await answer_ui(message, 
        "🔎 <b>Qidiruv natijalari:</b>",
        reply_markup=search_results_kb(movies),
    )
    await answer_ui(message, "👇 Kerakli kinoni tanlang", reply_markup=main_menu_kb())


@router.callback_query(F.data.startswith("movie:"))
async def movie_deliver_cb(callback: CallbackQuery):
    code = int(callback.data.split(":", 1)[1])
    movie = await db.get_movie(code)
    await callback.answer()
    if not movie:
        await answer_ui(callback.message, "😔 Ushbu kino topilmadi.")
        return
    await deliver_movie(callback.bot, callback.message.chat.id, callback.from_user.id, movie)


@router.message(F.text == "Kino buyurtma qilish")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_order_text)
    await answer_ui(message, 
        "📦 <b>Qaysi kinoni topa olmadingiz?</b>\n\n"
        "Kino nomini (yil va janri bilan bo'lsa, yanada yaxshi) yozib yuboring:",
        reply_markup=cancel_kb(),
    )


@router.message(UserStates.waiting_order_text)
async def order_process(message: Message, state: FSMContext):
    await state.clear()
    await db.add_order(message.from_user.id, message.text.strip())
    await answer_ui(message, 
        "✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
        "Tez orada administratorlarimiz siz so'ragan kinoni qo'shishga harakat qilishadi. 🙏",
        reply_markup=main_menu_kb(),
    )


async def deliver_movie(bot: Bot, chat_id: int, user_id: int, movie):
    if movie["is_vip"] and not (await db.is_vip(user_id)) and not is_admin(user_id):
        await send_ui(bot, 
            chat_id,
            "💎 <b>Bu kino faqat VIP a'zolar uchun!</b>\n\n"
            "VIP olish uchun administrator bilan bog'laning.",
        )
        return
    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=movie["code"],
        )
    except Exception:
        await send_ui(bot, 
            chat_id,
            "⚠️ Kechirasiz, ushbu kinoni yuborishda xatolik yuz berdi. "
            "Iltimos, keyinroq urinib ko'ring.",
        )


@router.message(F.text.regexp(r"^\d+$"))
async def movie_by_code(message: Message, state: FSMContext):
    """Foydalanuvchi raqamli kod yuborsa, bevosita kino yuboradi."""
    if await state.get_state() is not None:
        return
    if await db.is_banned(message.from_user.id):
        await answer_ui(message, "🚫 Siz botdan foydalanish huquqidan mahrum qilingansiz.")
        return
    if not await check_subscription(message.bot, message.from_user.id):
        channel = await get_required_channel()
        await answer_ui(message,
            "📢 <b>Botdan foydalanish uchun quyidagi kanalga a'zo bo'ling:</b>",
            reply_markup=subscribe_kb(channel),
        )
        return

    code = int(message.text.strip())
    movie = await db.get_movie(code)
    if not movie:
        # Baza bo'sh yoki kod topilmasa, to'g'ridan-to'g'ri kanaldan yuborishga urinib ko'ramiz
        try:
            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=code,
            )
        except Exception:
            await answer_ui(message,
                "😔 <b>Bunday kodli kino topilmadi.</b>\n\n"
                "Kodni tekshirib qaytadan yuboring yoki 🔎 <b>Kino izlash</b> "
                "orqali nom bo'yicha qidiring."
            )
        return

    await deliver_movie(message.bot, message.chat.id, message.from_user.id, movie)


@router.message(F.text)
async def movie_by_title_direct(message: Message, state: FSMContext):
    """
    Direct title search: users may simply type a movie name without pressing
    the search button first. Numeric messages are handled by movie_by_code
    handler above, and active FSM states are left untouched.
    """
    if await state.get_state() is not None:
        return

    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # Do not treat the UI buttons as movie titles.
    known_ui = {
        "Kino izlash",
        "Random kino",
        "Yordam",
        "Kategoriyalar",
        "VIP",
        "Kino buyurtma qilish",
        "Bekor qilish",
        "Asosiy menyu",
        "Kino qo'shish",
        "Kino o'chirish",
        "Kino tahrirlash",
        "Kanalni indekslash",
        "Buyurtmalar",
        "Foydalanuvchilar",
        "Statistika",
        "Reklama yuborish",
        "VIP foydalanuvchilar",
        "Ban qilish",
        "Bandan chiqarish",
        "Sozlamalar",
        "Zaxira nusxa",
        "Tiklash",
        "Emojilarni tekshirish",
    }
    if text in known_ui:
        return

    # Admin messages are handled by the admin router.
    if is_admin(message.from_user.id):
        return

    if await db.is_banned(message.from_user.id):
        await answer_ui(message, "🚫 Siz botdan foydalanish huquqidan mahrum qilingansiz.")
        return

    if not await check_subscription(message.bot, message.from_user.id):
        channel = await get_required_channel()
        await answer_ui(
            message,
            "📢 <b>Botdan foydalanish uchun quyidagi kanalga a'zo bo'ling:</b>",
            reply_markup=subscribe_kb(channel),
        )
        return

    movies = await db.search_movies(text, limit=15)
    if not movies:
        await answer_ui(
            message,
            "😔 <b>Bunday nomli kino topilmadi.</b>\n\n"
            "Kino kodini yuboring yoki boshqa nom bilan urinib ko'ring.",
            reply_markup=main_menu_kb(),
        )
        return

    await answer_ui(
        message,
        "🔎 <b>Topilgan kinolar:</b>",
        reply_markup=search_results_kb(movies),
    )
