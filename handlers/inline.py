"""
Inline mode handler.
Foydalanuvchilar boshqa chatlarda @bot_username yozganda barcha kinolar ro'yxati chiqadi,
yoki nomini yozganda qidirib beradi.
Barcha Custom Emojilar to'g'ridan-to'g'ri MessageEntity orqali render qilinadi.
"""
from aiogram import Router, Bot
from aiogram.enums import ButtonStyle
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultsButton,
)
import hashlib
import logging

import database as db
from emoji_helper import render_ui_text

router = Router()


def _make_id(text: str) -> str:
    """InlineQueryResult uchun unikal ID hosil qiladi."""
    return hashlib.md5(text.encode()).hexdigest()[:16]


@router.inline_query()
async def inline_search(query: InlineQuery, bot: Bot):
    text = (query.query or "").strip()
    offset = int(query.offset or 0)
    limit = 50
    results = []
    bot_info = await bot.get_me()
    logging.info(f"🔎 Inline query keldi: user={query.from_user.id}, query='{text}', offset={offset}")

    # Barcha kinolar yoki qidiruv bo'yicha kinolarni olish
    movies = await db.search_movies(text, limit=limit, offset=offset)
    logging.info(f"🔎 Topilgan kinolar soni: {len(movies)}")

    for movie in movies:
        code = movie["code"]
        title = movie["title"]
        category = movie["category"] or "Umumiy"
        vip_tag = "💎 " if movie["is_vip"] else ""
        description = f"Kod: {code} | Janr: {category}"

        # Tugma orqali to'g'ridan-to'g'ri botda ochish (rangli va stikerli)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Kinoni tomosha qilish",
                        url=f"https://t.me/{bot_info.username}?start=movie_{code}",
                        icon_custom_emoji_id="5368653135101310687",
                        style=ButtonStyle.SUCCESS,
                    )
                ]
            ]
        )

        # Matn va Custom Emoji entitylarini tayyorlash
        raw_html = (
            f"🎬 <b>{title}</b>\n"
            f"📂 <b>Janr:</b> {category}\n"
            f"🔢 <b>Kino kodi:</b> <code>{code}</code>\n\n"
            f"👇 <b>Kinoni tomosha qilish uchun pastdagi tugmani bosing:</b>"
        )
        plain_text, entities = render_ui_text(raw_html)

        results.append(
            InlineQueryResultArticle(
                id=_make_id(f"m_{code}_{offset}"),
                title=f"{vip_tag}{title}",
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=plain_text,
                    entities=entities,
                ),
                reply_markup=kb,
            )
        )

    if not results and offset == 0:
        not_found_html = (
            f"😔 <b>{text}</b> nomli kino topilmadi.\n\n"
            f"🤖 Botga kirib buyurtma berishingiz mumkin: @{bot_info.username}"
            if text else
            f"😔 Hozircha bazada kinolar mavjud emas.\n👉 @{bot_info.username}"
        )
        nf_plain, nf_entities = render_ui_text(not_found_html)
        results.append(
            InlineQueryResultArticle(
                id=_make_id("not_found"),
                title="😔 Hech qanday kino topilmadi",
                description=f'"{text}" so\'rovi bo\'yicha hech narsa topilmadi' if text else "Hozircha bazada kinolar yo'q",
                input_message_content=InputTextMessageContent(
                    message_text=nf_plain,
                    entities=nf_entities,
                ),
            )
        )

    # Keyingi sahifa offseti
    next_offset = str(offset + limit) if len(movies) == limit else ""

    await query.answer(
        results=results,
        cache_time=1,
        is_personal=True,
        next_offset=next_offset,
        button=InlineQueryResultsButton(
            text="🎬 Bot menyusiga o'tish",
            start_parameter="inline_open",
        ),
    )
