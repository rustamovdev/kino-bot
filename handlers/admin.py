import asyncio
import os
import shutil
import datetime

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, MessageOriginChannel, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from states import AdminStates
from keyboards import (
    admin_menu_kb,
    main_menu_kb,
    cancel_kb,
    admin_categories_kb,
    confirm_kb,
    category_pick_kb,
    edit_movie_kb,
    order_action_kb,
    broadcast_confirm_kb,
)
from config import ADMIN_IDS, CHANNEL_ID, DB_PATH, BACKUP_DIR
from emoji_helper import answer_ui, send_ui, edit_ui, validate_custom_emojis, valid_custom_emoji_id
from custom_emojis import CUSTOM_EMOJIS, EMOJI_FALLBACKS

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


# ==================== ADMIN MENYUSI ====================

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await answer_ui(message, 
        "🛠 <b>Admin paneliga xush kelibsiz!</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "adm_back_to_panel")
async def adm_back_to_panel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await edit_ui(callback.message,
        "🛠 <b>Admin paneliga xush kelibsiz!</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text == "Asosiy menyu")
async def back_to_user_menu(message: Message, state: FSMContext):
    await state.clear()
    await answer_ui(message, "🔙 Asosiy menyuga qaytdingiz.", reply_markup=main_menu_kb())


@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await edit_ui(callback.message, "❌ Amal bekor qilindi.")
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())



# ==================== KINO QO'SHISH ====================

@router.callback_query(F.data == "adm_add_movie")
@router.message(F.text == "Kino qo'shish")
async def add_movie_start(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_waiting_post)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await answer_ui(msg, 
        "🎬 <b>Kino qo'shish</b>\n\n"
        f"Kinoni <b>{CHANNEL_ID}</b> kanaliga joylang, so'ng o'sha postni shu botga "
        "forward qiling (yoki kino postining raqamli kodini yuboring).",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_waiting_post)
async def add_movie_get_post(message: Message, state: FSMContext):
    origin = getattr(message, "forward_origin", None)
    if origin and isinstance(origin, MessageOriginChannel):
        code = origin.message_id
    elif message.text and message.text.strip().isdigit():
        code = int(message.text.strip())
    else:
        await answer_ui(message, 
            "❗ Iltimos, kanaldagi kino postini forward qilib yuboring yoki post raqamli kodini kiriting."
        )
        return

    existing = await db.get_movie(code)
    if existing:
        await answer_ui(message, 
            f"⚠️ Bu post allaqachon <code>{code}</code> kodi bilan bazada mavjud:\n"
            f"🎬 {existing['title']}"
        )
        await state.clear()
        return

    default_title = (message.caption or message.text or "").strip().split("\n")[0][:150]
    if default_title.isdigit():
        default_title = ""
    await state.update_data(code=code, default_title=default_title)
    await state.set_state(AdminStates.add_waiting_title)
    hint = f"\n\n💡 Taklif etilgan nom: <i>{default_title}</i>" if default_title else ""
    await answer_ui(message, 
        f"🔢 Post kodi: <code>{code}</code>\n\n"
        f"✏ Endi kino nomini kiriting:{hint}",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_waiting_title)
async def add_movie_get_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    cats = await db.all_categories()
    await state.set_state(AdminStates.add_waiting_category)
    await answer_ui(message, 
        "📂 <b>Kino uchun kategoriyani tanlang:</b>",
        reply_markup=category_pick_kb(cats, "addmoviecat"),
    )


@router.callback_query(AdminStates.add_waiting_category, F.data.startswith("addmoviecat:"))
async def add_movie_pick_category(callback: CallbackQuery, state: FSMContext, bot: Bot):
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    code = data["code"]
    title = data["title"]
    await db.add_movie(code, title, category, is_vip_movie=0)
    await state.clear()
    await callback.answer("✅ Qo'shildi")

    # 1. Adminga xabar
    await edit_ui(callback.message, 
        "✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"🎬 Nomi: {title}\n"
        f"📂 Kategoriya: {category}"
    )
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())

    # 2. Kanalga e'lon posti yuborish
    try:
        bot_info = await bot.get_me()
        channel_post_text = (
            "🎬 <b>Yangi kino qo'shildi!</b>\n\n"
            f"🍿 <b>Nomi:</b> {title}\n"
            f"📂 <b>Kategoriya / Janri:</b> {category}\n"
            f"🔢 <b>Kino kodi:</b> <code>{code}</code>\n\n"
            f"📥 <b>Kinoni tomosha qilish uchun botimizga kiring:</b>\n"
            f"👉 @{bot_info.username}"
        )
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🎬 Kinoni tomosha qilish",
            url=f"https://t.me/{bot_info.username}?start=movie_{code}",
            style=ButtonStyle.SUCCESS,
        )
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_post_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception as e:
        await answer_ui(callback.message, f"⚠️ Kanalga xabar yuborishda xatolik: {e}")


# ==================== KINO O'CHIRISH ====================

@router.callback_query(F.data == "adm_del_movie")
@router.message(F.text == "Kino o'chirish")
async def delete_movie_start(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.delete_waiting_code)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await answer_ui(msg, 
        "➖ <b>O'chirmoqchi bo'lgan kino kodini kiriting:</b>",
        reply_markup=cancel_kb(),
    )


# ==================== KINO TAHRIRLASH ====================


@router.callback_query(F.data == "adm_edit_movie")
@router.message(F.text == "Kino tahrirlash")
async def edit_movie_start(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.edit_waiting_code)
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await answer_ui(msg, 
        "✏ <b>Tahrirlamoqchi bo'lgan kino kodini kiriting:</b>",
        reply_markup=cancel_kb(),
    )



@router.message(AdminStates.edit_waiting_code)
async def edit_movie_get_code(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, faqat raqamli kod kiriting.")
        return
    code = int(message.text.strip())
    movie = await db.get_movie(code)
    await state.clear()
    if not movie:
        await answer_ui(message, "😔 Bunday kodli kino topilmadi.", reply_markup=admin_menu_kb())
        return
    vip_text = "💎 Ha" if movie["is_vip"] else "➖ Yo'q"
    await answer_ui(message, 
        f"🎬 <b>{movie['title']}</b>\n"
        f"🔢 Kod: <code>{movie['code']}</code>\n"
        f"📂 Kategoriya: {movie['category']}\n"
        f"💎 VIP: {vip_text}\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=edit_movie_kb(code),
    )


@router.callback_query(F.data.startswith("editmovie_title:"))
async def edit_movie_title_start(callback: CallbackQuery, state: FSMContext):
    code = int(callback.data.split(":", 1)[1])
    await state.update_data(code=code)
    await state.set_state(AdminStates.edit_waiting_title)
    await callback.answer()
    await answer_ui(callback.message, 
        "✏ <b>Yangi nomni kiriting:</b>", reply_markup=cancel_kb()
    )


@router.message(AdminStates.edit_waiting_title)
async def edit_movie_title_save(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    await db.edit_movie_title(code, message.text.strip())
    await state.clear()
    await answer_ui(message, "✅ Kino nomi yangilandi.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("editmovie_cat:"))
async def edit_movie_cat_start(callback: CallbackQuery, state: FSMContext):
    code = int(callback.data.split(":", 1)[1])
    await state.update_data(code=code)
    cats = await db.all_categories()
    builder = InlineKeyboardBuilder()
    for c in cats:
        builder.button(text=c["name"], callback_data=f"editcatpick:{c['name']}")
    builder.adjust(2)
    await callback.answer()
    await answer_ui(callback.message, 
        "📂 <b>Yangi kategoriyani tanlang:</b>", reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("editcatpick:"))
async def edit_movie_cat_save(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    code = data.get("code")
    if not code:
        await callback.answer("❗ Xatolik, qaytadan boshlang.", show_alert=True)
        return
    await db.edit_movie_category(code, category)
    await state.clear()
    await callback.answer("✅ Yangilandi")
    await edit_ui(callback.message, f"✅ Kategoriya '{category}' ga o'zgartirildi.")
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("editmovie_vip:"))
async def edit_movie_vip_toggle(callback: CallbackQuery):
    code = int(callback.data.split(":", 1)[1])
    movie = await db.get_movie(code)
    if not movie:
        await callback.answer("😔 Topilmadi", show_alert=True)
        return
    new_value = 0 if movie["is_vip"] else 1
    await db.toggle_movie_vip(code, new_value)
    await callback.answer("✅ Yangilandi")
    status = "💎 VIP qilib belgilandi" if new_value else "➖ VIP holati olib tashlandi"
    await edit_ui(callback.message, f"✅ {status}.")
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


# ==================== KATEGORIYALAR ====================

@router.callback_query(F.data == "adm_categories")
@router.message(F.text == "Kategoriyalar")
async def admin_categories_menu(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await answer_ui(msg, 
        "📂 <b>Kategoriyalarni boshqarish</b>", reply_markup=admin_categories_kb()
    )


# ==================== KANALNI INDEKSLASH ====================

@router.callback_query(F.data == "adm_index_channel")
@router.message(F.text == "Kanalni indekslash")
async def index_channel_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    if not CHANNEL_ID:
        await answer_ui(msg, "⚠️ CHANNEL_ID sozlamalarda ko'rsatilmagan.")
        return
    status_msg = await answer_ui(msg, 
        "🔄 <b>Kanal indekslash boshlandi...</b>\n\nIltimos kuting, bu biroz vaqt olishi mumkin."
    )

    start_code = await db.last_movie_code() + 1
    added = 0
    empty_streak = 0
    checked = 0
    max_checked = 3000
    max_empty_streak = 25

    code = start_code
    while empty_streak < max_empty_streak and checked < max_checked:
        checked += 1
        try:
            fwd = await msg.bot.forward_message(
                chat_id=msg.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=code,
                disable_notification=True,
            )
            caption = (fwd.caption or fwd.text or f"Kino #{code}").strip().split("\n")[0][:150]
            await db.add_movie(code, caption, "Umumiy", is_vip_movie=0)
            added += 1
            empty_streak = 0
            try:
                await fwd.delete()
            except Exception:
                pass
        except Exception:
            empty_streak += 1
        code += 1
        await asyncio.sleep(0.05)

        if checked % 50 == 0:
            try:
                await edit_ui(status_msg, 
                    f"🔄 <b>Indekslanmoqda...</b>\n\n"
                    f"✅ Qo'shildi: {added}\n"
                    f"🔎 Tekshirildi: {checked}"
                )
            except Exception:
                pass

    await edit_ui(status_msg, 
        "✅ <b>Indekslash yakunlandi!</b>\n\n"
        f"➕ Yangi qo'shilgan kinolar: {added}\n"
        f"🔎 Jami tekshirilgan postlar: {checked}"
    )
    await answer_ui(msg, "🛠 Admin panel:", reply_markup=admin_menu_kb())


# ==================== BUYURTMALAR ====================

@router.callback_query(F.data == "adm_orders")
@router.message(F.text == "Buyurtmalar")
async def orders_list(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    orders = await db.pending_orders()
    if not orders:
        await answer_ui(msg, "📦 Hozircha kutilayotgan buyurtmalar yo'q.", reply_markup=admin_menu_kb())
        return
    await answer_ui(msg, f"📦 <b>Kutilayotgan buyurtmalar: {len(orders)} ta</b>")
    for o in orders[:20]:
        text = (
            f"🆔 Buyurtma #{o['id']}\n"
            f"👤 Foydalanuvchi: <code>{o['user_id']}</code>\n"
            f"🎬 So'ralgan kino: {o['text']}\n"
            f"🕒 {o['created_at']}"
        )
        await answer_ui(msg, text, reply_markup=order_action_kb(o["id"]))


# ==================== FOYDALANUVCHILAR ====================

@router.callback_query(F.data == "adm_users")
@router.message(F.text == "Foydalanuvchilar")
async def users_list(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    total = await db.users_count()
    users = await db.all_users()
    recent = users[:15]
    text = f"👥 <b>Jami foydalanuvchilar: {total} ta</b>\n\n<b>So'nggi qo'shilganlar:</b>\n"
    for u in recent:
        uname = f"@{u['username']}" if u["username"] else "—"
        text += f"• <code>{u['user_id']}</code> — {u['full_name']} ({uname})\n"
    await answer_ui(msg, text, reply_markup=admin_menu_kb())


# ==================== STATISTIKA ====================

@router.callback_query(F.data == "adm_stats")
@router.message(F.text == "Statistika")
async def statistics(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    users_total = await db.users_count()
    movies_total = await db.movies_count()
    vip_total = len(await db.vip_users())
    banned_total = len(await db.banned_users())
    orders_total = await db.orders_count()
    pending_total = len(await db.pending_orders())
    cats_total = len(await db.all_categories())

    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_total}</b>\n"
        f"🎬 Kinolar: <b>{movies_total}</b>\n"
        f"📂 Kategoriyalar: <b>{cats_total}</b>\n"
        f"💎 VIP foydalanuvchilar: <b>{vip_total}</b>\n"
        f"🚫 Ban qilinganlar: <b>{banned_total}</b>\n"
        f"📦 Jami buyurtmalar: <b>{orders_total}</b>\n"
        f"⏳ Kutilayotgan buyurtmalar: <b>{pending_total}</b>\n"
    )
    await answer_ui(msg, text, reply_markup=admin_menu_kb())


# ==================== REKLAMA (BROADCAST) ====================

@router.callback_query(F.data == "adm_broadcast")
@router.message(F.text == "Reklama yuborish")
async def broadcast_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await state.set_state(AdminStates.broadcast_waiting_content)
    await answer_ui(msg, 
        "📢 <b>Yubormoqchi bo'lgan xabaringizni yuboring</b>\n\n"
        "(matn, rasm, video — istalgan turdagi xabar bo'lishi mumkin)",
        reply_markup=cancel_kb(),
    )


# ==================== VIP FOYDALANUVCHILAR ====================

@router.callback_query(F.data == "adm_vip_users")
@router.message(F.text == "VIP foydalanuvchilar")
async def vip_users_menu(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    vips = await db.vip_users()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ VIP qo'shish", callback_data="vip_add_start")
    text = f"💎 <b>VIP foydalanuvchilar: {len(vips)} ta</b>\n\n"
    if vips:
        for v in vips[:20]:
            uname = f"@{v['username']}" if v["username"] else "—"
            until = v["vip_until"] or "cheksiz"
            text += f"• <code>{v['user_id']}</code> ({uname}) — {until} gacha\n"
            builder.button(text=f"❌ {v['user_id']}", callback_data=f"vip_remove:{v['user_id']}")
    builder.button(text="Admin panel", callback_data="adm_back_to_panel")
    builder.adjust(1)
    await answer_ui(msg, text, reply_markup=builder.as_markup())


# ==================== BAN / UNBAN ====================

@router.callback_query(F.data == "adm_ban")
@router.message(F.text == "Ban qilish")
async def ban_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await state.set_state(AdminStates.ban_waiting_id)
    await answer_ui(msg, 
        "🚫 <b>Ban qilmoqchi bo'lgan foydalanuvchi ID sini kiriting:</b>",
        reply_markup=cancel_kb(),
    )


@router.callback_query(F.data == "adm_unban")
@router.message(F.text == "Bandan chiqarish")
async def unban_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await state.set_state(AdminStates.unban_waiting_id)
    await answer_ui(msg, 
        "✅ <b>Bandan chiqarmoqchi bo'lgan foydalanuvchi ID sini kiriting:</b>",
        reply_markup=cancel_kb(),
    )


# ==================== SOZLAMALAR ====================

@router.callback_query(F.data == "adm_settings")
@router.message(F.text == "Sozlamalar")
async def settings_menu(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    from utils import get_required_channel

    channel = await get_required_channel()
    channel_text = channel if channel else "o'rnatilmagan"
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Majburiy kanalni o'zgartirish", callback_data="set_req_channel")
    builder.button(text="🗑 Majburiy kanalni o'chirish", callback_data="del_req_channel")
    builder.button(text="Admin panel", callback_data="adm_back_to_panel")
    builder.adjust(1)
    await answer_ui(msg, 
        "⚙ <b>Bot sozlamalari</b>\n\n"
        f"📢 Majburiy obuna kanali: <code>{channel_text}</code>",
        reply_markup=builder.as_markup(),
    )


# ==================== ZAXIRA NUSXA / TIKLASH ====================

@router.callback_query(F.data == "adm_backup")
@router.message(F.text == "Zaxira nusxa")
async def backup_db(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{ts}.db")
    shutil.copy(DB_PATH, backup_path)
    await msg.answer_document(
        FSInputFile(backup_path),
        caption="💾 <b>Ma'lumotlar bazasi zaxira nusxasi</b>",
    )
    await answer_ui(msg, "🛠 Admin panel:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_restore")
@router.message(F.text == "Tiklash")
async def restore_db_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await state.set_state(AdminStates.restore_waiting_file)
    await answer_ui(msg, 
        "♻ <b>Tiklash</b>\n\n"
        "⚠️ Diqqat! Joriy baza o'rniga yangi baza fayli (.db) o'rnatiladi.\n"
        "Iltimos, avval saqlangan zaxira faylini (.db) yuboring:",
        reply_markup=cancel_kb(),
    )


# ==================== PREMIUM CUSTOM EMOJI TEST ====================

@router.callback_query(F.data == "adm_emoji_test")
@router.message(F.text == "Emojilarni tekshirish")
async def emoji_test(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    valid_ids, status = await validate_custom_emojis(msg.bot)

    lines = ["🧪 <b>Telegram Premium Custom Emoji tekshiruvi</b>", ""]
    for key, emoji_id in CUSTOM_EMOJIS.items():
        configured = str(emoji_id or "").strip()
        if not configured:
            lines.append(
                f"{EMOJI_FALLBACKS.get(key, '🔹')} <code>{key}</code> — "
                "⚪ ID kiritilmagan, Unicode ishlatiladi"
            )
        elif configured in valid_ids:
            lines.append(
                f"{EMOJI_FALLBACKS.get(key, '🔹')} <code>{key}</code> — "
                "🟢 ID Telegram tomonidan topildi"
            )
        else:
            lines.append(
                f"{EMOJI_FALLBACKS.get(key, '🔹')} <code>{key}</code> — "
                "🔴 ID Telegram tomonidan topilmadi"
            )

    if "_global" in status:
        lines.append("")
        lines.append(f"⚠️ <b>Tekshiruv:</b> {status['_global']}")

    lines.append("")
    lines.append(
        "ℹ️ Pastdagi xabarda emoji belgilarining o'zi Custom Emoji entity "
        "sifatida yuboriladi. Pastdagi tugmalarda esa "
        "<code>icon_custom_emoji_id</code> ishlatiladi."
    )

    await answer_ui(msg, "\n".join(lines), reply_markup=_emoji_test_kb())



def _emoji_test_kb():
    builder = InlineKeyboardBuilder()
    for key in CUSTOM_EMOJIS:
        icon_id = valid_custom_emoji_id(key)
        builder.button(
            text=key,
            icon_custom_emoji_id=icon_id,
            callback_data=f"emoji_test:{key}",
        )
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(F.data.startswith("emoji_test:"))
async def emoji_test_callback(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    configured = str(CUSTOM_EMOJIS.get(key, "") or "").strip()
    icon_id = valid_custom_emoji_id(key)

    if configured and icon_id:
        await callback.answer(f"🟢 {key}: Custom Emoji ishlayapti")
    elif configured:
        await callback.answer(f"🔴 {key}: ID topilmadi, Unicode fallback")
    else:
        await callback.answer(f"⚪ {key}: ID kiritilmagan")
