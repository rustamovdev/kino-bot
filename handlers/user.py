from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

import database as db
from states import UserStates
from keyboards import (
    main_menu_kb,
    cancel_kb,
    back_to_main_kb,
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
    '<tg-emoji emoji-id="5418115103763494597">👋</tg-emoji> <b>Assalomu alaykum!</b>\n\n'
    '<tg-emoji emoji-id="5368653135101310687">🎬</tg-emoji> <b>Kino botimizga xush kelibsiz.</b>\n\n'
    '<tg-emoji emoji-id="5371081166013078244">🍿</tg-emoji> <b>Ushbu bot orqali siz:</b>\n\n'
    '<tg-emoji emoji-id="5429571366384842791">🔎</tg-emoji> <b>Kino nomi bo\'yicha izlash</b>\n'
    '<tg-emoji emoji-id="5235588635885054955">🎲</tg-emoji> <b>Tasodifiy kino olish</b>\n'
    '<tg-emoji emoji-id="5341492148468465410">📂</tg-emoji> <b>Kategoriyalar bo\'yicha izlash</b>\n'
    '<tg-emoji emoji-id="5843804967625821763">💎</tg-emoji> <b>VIP kinolarni ko\'rish</b>\n'
    '<tg-emoji emoji-id="5258134813302332906">📦</tg-emoji> <b>Kino buyurtma qilish</b>\n\n'
    'imkoniyatiga egasiz.\n\n'
    '<tg-emoji emoji-id="6255733820696300839">❗</tg-emoji> <b>Eslatma:</b>\n'
    'Kino kodini yoki nomini to\'g\'ridan-to\'g\'ri yuborishingiz mumkin.'
)

HELP_TEXT = (
    '<tg-emoji emoji-id="5458481637362778614">💡</tg-emoji> <b>Yordam bo\'limi</b>\n\n'
    '<tg-emoji emoji-id="5226513232549664618">🔢</tg-emoji> Kino kodini bilsangiz — shunchaki raqamni yuboring. Masalan: <code>107</code>\n'
    '<tg-emoji emoji-id="5429571366384842791">🔎</tg-emoji> <b>Kino izlash</b> — kino nomi bo\'yicha qidirish\n'
    '<tg-emoji emoji-id="5235588635885054955">🎲</tg-emoji> <b>Random kino</b> — tasodifiy kino olish\n'
    '<tg-emoji emoji-id="5341492148468465410">📂</tg-emoji> <b>Kategoriyalar</b> — janrlar bo\'yicha kinolarni ko\'rish\n'
    '<tg-emoji emoji-id="5843804967625821763">💎</tg-emoji> <b>VIP</b> — VIP a\'zolik haqida ma\'lumot\n'
    '<tg-emoji emoji-id="5258134813302332906">📦</tg-emoji> <b>Kino buyurtma qilish</b> — topolmagan kinongizni so\'rang\n\n'
    '<tg-emoji emoji-id="5458481637362778614">❓</tg-emoji> Qo\'shimcha savollar bo\'lsa, administratorga murojaat qiling.'
)

VIP_TEXT = (
    '<tg-emoji emoji-id="5843804967625821763">💎</tg-emoji> <b>VIP a\'zolik</b>\n\n'
    '✨ VIP a\'zolar uchun maxsus imkoniyatlar:\n\n'
    '<tg-emoji emoji-id="5368653135101310687">🎬</tg-emoji> Eksklyuziv VIP kinolarga kirish\n'
    '⚡ Tezkor xizmat ko\'rsatish\n'
    '🎁 Maxsus takliflar va yangiliklar\n\n'
    '💬 VIP a\'zolik olish uchun administrator bilan bog\'laning.'
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

    # Deep-link tekshiruvi: masalan /start movie_123
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("movie_"):
        try:
            code = int(parts[1].replace("movie_", ""))
            movie = await db.get_movie(code)
            if movie:
                await deliver_movie(message.bot, message.chat.id, message.from_user.id, movie)
                return
        except ValueError:
            pass

    await send_welcome(message)



@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    if await check_subscription(callback.bot, callback.from_user.id):
        await callback.message.delete()
        await send_welcome(callback.message)
    else:
        await callback.answer("❗ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)


@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await edit_ui(callback.message, "🔙 Bekor qilindi.")
    await answer_ui(callback.message, "🎬 Asosiy menyu:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await edit_ui(callback.message, WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(F.text == "Bekor qilish")
async def cancel_action_msg(message: Message, state: FSMContext):
    await state.clear()
    await answer_ui(message, "🔙 Bekor qilindi.", reply_markup=main_menu_kb())



# ==================== INLINE MENYU CALLBACK'LARI ====================

@router.callback_query(F.data == "menu_help")
async def cb_menu_help(callback: CallbackQuery):
    await callback.answer()
    await answer_ui(callback.message, HELP_TEXT)


@router.callback_query(F.data == "menu_vip")
async def cb_menu_vip(callback: CallbackQuery):
    await callback.answer()
    user_vip = await db.is_vip(callback.from_user.id)
    text = VIP_TEXT
    if user_vip:
        text = "💎 <b>Siz allaqachon VIP a'zosiz!</b>\n\nBarcha VIP kinolar sizga ochiq. 🎉"
    await answer_ui(callback.message, text, reply_markup=vip_menu_kb(user_vip))


@router.callback_query(F.data == "menu_categories")
async def cb_menu_categories(callback: CallbackQuery):
    await callback.answer()
    cats = await db.all_categories()
    if not cats:
        await answer_ui(callback.message, "📂 Hozircha kategoriyalar mavjud emas.")
        return
    await answer_ui(callback.message,
        "📂 <b>Quyidagi kategoriyalardan birini tanlang:</b>",
        reply_markup=categories_kb(cats),
    )


@router.callback_query(F.data == "menu_order")
async def cb_menu_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserStates.waiting_order_text)
    await answer_ui(callback.message,
        "📦 <b>Qaysi kinoni topa olmadingiz?</b>\n\n"
        "Kino nomini (yil va janri bilan bo'lsa, yanada yaxshi) yozib yuboring:",
        reply_markup=cancel_kb(),
    )


@router.callback_query(F.data == "menu_random")
async def cb_menu_random(callback: CallbackQuery):
    await callback.answer()
    movie = await db.random_movie()
    if not movie:
        await answer_ui(callback.message, "😔 Hozircha bazada kinolar mavjud emas.")
        return
    await deliver_movie(callback.bot, callback.message.chat.id, callback.from_user.id, movie)


@router.callback_query(F.data == "menu_search")
async def cb_menu_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserStates.waiting_search_query)
    await answer_ui(callback.message,
        "🔎 <b>Qidirmoqchi bo'lgan kino nomini yozing:</b>",
        reply_markup=cancel_kb(),
    )


# ==================== ESKI MATN HANDLER'LAR (Reply KB uchun fallback) ====================

@router.message(F.text == "Yordam")
async def help_menu(message: Message):
    await answer_ui(message, HELP_TEXT)


@router.message(F.text == "VIP")
async def vip_menu(message: Message):
    user_vip = await db.is_vip(message.from_user.id)
    text = VIP_TEXT
    if user_vip:
        text = "💎 <b>Siz allaqachon VIP a'zosiz!</b>\n\nBarcha VIP kinolar sizga ochiq. 🎉"
    await answer_ui(message, text, reply_markup=vip_menu_kb(user_vip))


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


@router.callback_query(F.data == "vip_info")
async def vip_info_cb(callback: CallbackQuery):
    await callback.answer()
    await answer_ui(callback.message,
        "💬 VIP a'zolik olish uchun administratorga yozing."
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
        # copy_message — forward qilish bloklanadi (protect_content yo'q, lekin original kanal ko'rinmaydi)
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=movie["code"],
            protect_content=True,
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
                protect_content=True,
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
