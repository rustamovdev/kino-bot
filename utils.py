import logging
from aiogram import Bot
from config import REQUIRED_CHANNEL, ADMIN_IDS
import database as db


async def get_required_channel() -> str:
    """Majburiy obuna kanalini avval bazadan, topilmasa .env dan oladi."""
    value = await db.get_setting("required_channel", REQUIRED_CHANNEL)
    return (value or "").strip()


def normalize_channel(channel: str) -> str:
    """Kanal nomini Telegram API ga mos formatga keltiradi."""
    ch = channel.strip()
    if not ch:
        return ""
    if ch.startswith("https://t.me/") or ch.startswith("http://t.me/"):
        ch = ch.split("t.me/")[1].split("/")[0].split("?")[0]
        if not ch.startswith("@") and not ch.startswith("-100"):
            ch = f"@{ch}"
        return ch
    if ch.startswith("-100") or ch.startswith("@"):
        return ch
    if ch.isdigit():
        return f"-100{ch}"
    return f"@{ch}"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """
    Foydalanuvchi majburiy kanalga a'zo bo'lsa True qaytaradi.
    Agar majburiy kanal sozlanmagan bo'lsa, har doim True.
    """
    if is_admin(user_id):
        return True

    channel = await get_required_channel()
    if not channel:
        return True

    chat_id = normalize_channel(channel)
    if not chat_id:
        return True

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ("creator", "administrator", "member", "restricted"):
            return True
        return False
    except Exception as e:
        err_msg = str(e).lower()
        logging.warning(f"⚠️ check_subscription xatosi (kanal: {chat_id}, user: {user_id}): {e}")
        # Agar user a'zo bo'lmasa yoki bot tekshira olmasa -> False (kanalga obuna bo'lish so'raladi)
        return False
