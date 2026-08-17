from aiogram import Bot
from config import REQUIRED_CHANNEL, ADMIN_IDS
import database as db


async def get_required_channel() -> str:
    """Majburiy obuna kanalini avval bazadan, topilmasa .env dan oladi."""
    value = await db.get_setting("required_channel", REQUIRED_CHANNEL)
    return value or ""


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi majburiy kanalga a'zo bo'lsa True qaytaradi.
    Agar majburiy kanal sozlanmagan bo'lsa, har doim True."""
    channel = await get_required_channel()
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in ("left", "kicked")
    except Exception:
        return True


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
