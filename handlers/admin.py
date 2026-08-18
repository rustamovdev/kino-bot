import asyncio
import os
import shutil
import datetime

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.enums import ButtonStyle
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
from utils import get_required_channel

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


@router.message(AdminStates.delete_waiting_code)
async def delete_movie_get_code(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, faqat raqamli kod kiriting.")
        return
    code = int(message.text.strip())
    movie = await db.get_movie(code)
    await state.clear()
    if not movie:
        await answer_ui(message, "😔 Bunday kodli kino topilmadi.", reply_markup=admin_menu_kb())
        return

    await answer_ui(
        message,
        f"🗑 <b>Kinoni o'chirishni tasdiqlaysizmi?</b>\n\n"
        f"🎬 <b>{movie['title']}</b>\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"📂 Kategoriya: {movie.get('category', 'Umumiy')}",
        reply_markup=confirm_kb("del_movie", code),
    )


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_action_cb(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    action = parts[1]
    param = parts[2] if len(parts) > 2 else ""

    if action == "del_movie":
        code = int(param)
        deleted = await db.delete_movie(code)
        await callback.answer("O'chirildi" if deleted else "Topilmadi")
        if deleted:
            await edit_ui(callback.message, f"✅ <code>{code}</code> kodli kino muvaffaqiyatli o'chirildi.")
        else:
            await edit_ui(callback.message, f"❌ <code>{code}</code> kodli kino topilmadi yoki allaqachon o'chirilgan.")
        await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


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


@router.callback_query(F.data == "admcat_add")
async def admcat_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.category_waiting_name)
    await callback.answer()
    await answer_ui(callback.message, "➕ <b>Yangi kategoriya nomini kiriting:</b>", reply_markup=cancel_kb())


@router.message(AdminStates.category_waiting_name)
async def admcat_add_process(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.clear()
    success = await db.add_category(name)
    if success:
        await answer_ui(message, f"✅ <b>'{name}'</b> kategoriyasi qo'shildi!", reply_markup=admin_categories_kb())
    else:
        await answer_ui(message, f"⚠️ <b>'{name}'</b> kategoriyasi allaqachon mavjud!", reply_markup=admin_categories_kb())


@router.callback_query(F.data == "admcat_del")
async def admcat_del_start(callback: CallbackQuery):
    cats = await db.all_categories()
    if not cats:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for c in cats:
        if c["name"] != "Umumiy":
            builder.button(text=f"🗑 {c['name']}", callback_data=f"catdel:{c['name']}")
    builder.button(text="🔙 Orqaga", callback_data="adm_categories")
    builder.adjust(2)
    await callback.answer()
    await edit_ui(callback.message, "🗑 <b>O'chirmoqchi bo'lgan kategoriyani tanlang:</b>", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("catdel:"))
async def admcat_del_process(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    deleted = await db.delete_category(name)
    await callback.answer("O'chirildi" if deleted else "Xatolik")
    await edit_ui(callback.message, f"✅ <b>'{name}'</b> kategoriyasi o'chirildi.", reply_markup=admin_categories_kb())


@router.callback_query(F.data == "admcat_list")
async def admcat_list_cb(callback: CallbackQuery):
    cats = await db.all_categories()
    await callback.answer()
    text = f"📂 <b>Kategoriyalar ro'yxati ({len(cats)} ta):</b>\n\n"
    for idx, c in enumerate(cats, start=1):
        text += f"{idx}. {c['name']}\n"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="adm_categories")
    await edit_ui(callback.message, text, reply_markup=builder.as_markup())


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

    start_code = 1
    added = 0
    empty_streak = 0
    checked = 0
    max_checked = 2000
    max_empty_streak = 40

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


@router.callback_query(F.data.startswith("order_done:"))
async def order_done_cb(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split(":", 1)[1])
    order = await db.get_order(order_id)
    await db.close_order(order_id)
    await callback.answer("✅ Bajarildi deb belgilandi")
    await edit_ui(callback.message, f"✅ Buyurtma #{order_id} <b>bajarildi</b> deb belgilandi.")

    # Notify ordering user if found
    if order and order.get("user_id"):
        try:
            await send_ui(
                bot,
                order["user_id"],
                f"🎬 <b>Siz so'ragan kino qo'shildi!</b>\n\n"
                f"🍿 <b>So'rov:</b> <i>{order['text']}</i>\n"
                "Kino qidirish yoki kod orqali tomosha qilishingiz mumkin! 🎉",
            )
        except Exception:
            pass


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


@router.message(AdminStates.broadcast_waiting_content)
async def broadcast_get_content(message: Message, state: FSMContext):
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    total_users = await db.users_count()
    await answer_ui(
        message,
        f"📢 <b>Reklama xabari qabul qilindi.</b>\n\n"
        f"👥 Qabul qiluvchilar soni: <b>{total_users} ta foydalanuvchi</b>\n\n"
        "Haqiqatan ham ushbu xabarni barcha foydalanuvchilarga yubormoqchimisiz?",
        reply_markup=broadcast_confirm_kb(),
    )


@router.callback_query(F.data == "bcast_send")
async def broadcast_send_cb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    await state.clear()
    await callback.answer("Yuborish boshlandi...")

    if not from_chat_id or not message_id:
        await edit_ui(callback.message, "❌ Xatolik yuz berdi. Reklama xabari topilmadi.")
        await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())
        return

    users = await db.all_users()
    total = len(users)
    sent = 0
    blocked = 0
    failed = 0

    status_msg = await edit_ui(
        callback.message,
        f"⏳ <b>Xabar yuborilmoqda...</b>\n\n"
        f"📊 Jami: {total}\n"
        f"✅ Yuborildi: {sent}\n"
        f"🚫 Bloklagan: {blocked}\n"
        f"❌ Xatolik: {failed}",
    )

    for idx, u in enumerate(users, start=1):
        uid = u["user_id"]
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
            sent += 1
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "chat not found" in err_str or "user is deactivated" in err_str:
                blocked += 1
            else:
                failed += 1

        if idx % 25 == 0 or idx == total:
            try:
                await edit_ui(
                    status_msg,
                    f"⏳ <b>Xabar yuborilmoqda...</b>\n\n"
                    f"📊 Jami: {total}\n"
                    f"✅ Yuborildi: {sent}\n"
                    f"🚫 Bloklagan: {blocked}\n"
                    f"❌ Xatolik: {failed}\n"
                    f"📈 Jarayon: {int((idx / total) * 100)}%",
                )
            except Exception:
                pass
        await asyncio.sleep(0.04)

    await edit_ui(
        status_msg,
        f"📢 <b>Reklama yuborish yakunlandi!</b>\n\n"
        f"📊 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"✅ Muvaffaqiyatli yetkazildi: <b>{sent}</b>\n"
        f"🚫 Botni bloklaganlar: <b>{blocked}</b>\n"
        f"❌ Boshqa xatoliklar: <b>{failed}</b>",
    )
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "bcast_cancel")
async def broadcast_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    await edit_ui(callback.message, "❌ Reklama yuborish bekor qilindi.")
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


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


@router.callback_query(F.data == "vip_add_start")
async def vip_add_start_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.vip_waiting_id)
    await callback.answer()
    await answer_ui(callback.message, "💎 <b>VIP bermoqchi bo'lgan foydalanuvchi ID sini kiriting:</b>", reply_markup=cancel_kb())


@router.message(AdminStates.vip_waiting_id)
async def vip_get_id(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, to'g'ri raqamli ID kiriting.")
        return
    user_id = int(message.text.strip())
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.vip_waiting_days)
    await answer_ui(message, f"👤 Foydalanuvchi: <code>{user_id}</code>\n\n🗓 <b>Necha kunga VIP berilsin?</b> (masalan: 30):", reply_markup=cancel_kb())


@router.message(AdminStates.vip_waiting_days)
async def vip_get_days(message: Message, state: FSMContext, bot: Bot):
    if not message.text or not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, kunlar sonini raqamda kiriting (masalan: 30).")
        return
    days = int(message.text.strip())
    data = await state.get_data()
    user_id = data.get("target_user_id")
    await state.clear()

    if not user_id:
        await answer_ui(message, "❌ Xatolik yuz berdi.", reply_markup=admin_menu_kb())
        return

    until = await db.set_vip(user_id, days)
    await answer_ui(
        message,
        f"✅ <code>{user_id}</code> ga <b>{days} kunlik</b> VIP a'zolik berildi!\n\n"
        f"🕒 Muddati: <b>{until}</b> gacha.",
        reply_markup=admin_menu_kb(),
    )
    # Foydalanuvchini xabardor qilish
    try:
        await send_ui(
            bot,
            user_id,
            f"🎉 <b>Tabriklaymiz! Sizga {days} kunlik VIP a'zolik berildi!</b>\n\n"
            f"🕒 Muddati: <b>{until}</b> gacha.\n"
            "Endi barcha VIP kinolarni cheklovlarsiz tomosha qilishingiz mumkin. 💎",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("vip_remove:"))
async def vip_remove_cb(callback: CallbackQuery, bot: Bot):
    user_id = int(callback.data.split(":", 1)[1])
    await db.remove_vip(user_id)
    await callback.answer("VIP olib tashlandi")
    await edit_ui(callback.message, f"➖ <code>{user_id}</code> dan VIP holati olib tashlandi.")
    try:
        await send_ui(
            bot,
            user_id,
            "ℹ️ <b>Sizning VIP a'zolik muddatingiz yakunlandi.</b>",
        )
    except Exception:
        pass
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


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


@router.message(AdminStates.ban_waiting_id)
async def ban_process(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, to'g'ri raqamli ID kiriting.")
        return
    user_id = int(message.text.strip())
    await state.clear()
    await db.ban_user(user_id)
    await answer_ui(message, f"🚫 <code>{user_id}</code> foydalanuvchisi <b>ban qilindi</b>.", reply_markup=admin_menu_kb())


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


@router.message(AdminStates.unban_waiting_id)
async def unban_process(message: Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await answer_ui(message, "❗ Iltimos, to'g'ri raqamli ID kiriting.")
        return
    user_id = int(message.text.strip())
    await state.clear()
    await db.unban_user(user_id)
    await answer_ui(message, f"✅ <code>{user_id}</code> foydalanuvchisi <b>bandan chiqarildi</b>.", reply_markup=admin_menu_kb())


# ==================== SOZLAMALAR ====================

@router.callback_query(F.data == "adm_settings")
@router.message(F.text == "Sozlamalar")
async def settings_menu(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()

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


@router.callback_query(F.data == "set_req_channel")
async def set_req_channel_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.settings_waiting_channel)
    await callback.answer()
    await answer_ui(
        callback.message,
        "📢 <b>Yangi majburiy obuna kanalini kiriting:</b>\n\n"
        "Masalan: <code>@kanal_nomi</code> yoki <code>-1001234567890</code>",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.settings_waiting_channel)
async def set_req_channel_save(message: Message, state: FSMContext):
    channel = message.text.strip()
    await state.clear()
    await db.set_setting("required_channel", channel)
    await answer_ui(
        message,
        f"✅ Majburiy obuna kanali <code>{channel}</code> ga o'zgartirildi!",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "del_req_channel")
async def del_req_channel_cb(callback: CallbackQuery):
    await db.set_setting("required_channel", "")
    await callback.answer("O'chirildi")
    await edit_ui(callback.message, "✅ Majburiy obuna kanali o'chirildi.")
    await answer_ui(callback.message, "🛠 Admin panel:", reply_markup=admin_menu_kb())


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


@router.message(AdminStates.restore_waiting_file, F.document)
async def restore_db_file(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    if not doc.file_name or not doc.file_name.endswith(".db"):
        await answer_ui(message, "❗ Iltimos, faqat <code>.db</code> kengaytmali fayl yuboring.")
        return
    await state.clear()
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, DB_PATH)
        await db.init_db()
        await answer_ui(message, "✅ <b>Ma'lumotlar bazasi muvaffaqiyatli tiklandi!</b>", reply_markup=admin_menu_kb())
    except Exception as e:
        await answer_ui(message, f"❌ Bazani tiklashda xatolik yuz berdi: {e}", reply_markup=admin_menu_kb())


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
