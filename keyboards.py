from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from custom_emojis import EMOJI_FALLBACKS
from emoji_helper import valid_custom_emoji_id


def _button_text(key: str, text: str) -> tuple[str, str | None]:
    """Return button label and actual Telegram Custom Emoji icon ID."""
    icon_id = valid_custom_emoji_id(key)
    if icon_id:
        return text, icon_id
    return f"{EMOJI_FALLBACKS.get(key, '')} {text}".strip(), None


def _kb_button(key: str, text: str) -> KeyboardButton:
    # ReplyKeyboard tugmalarida icon_custom_emoji_id qo'llab-quvvatlanmaydi.
    # Emoji belgisini to'g'ridan-to'g'ri matn ichiga qo'shamiz.
    fallback = EMOJI_FALLBACKS.get(key, "")
    label = f"{fallback} {text}".strip() if fallback else text
    return KeyboardButton(text=label)


def _ikb_button(builder: InlineKeyboardBuilder, key: str, text: str, callback_data: str | None = None, url: str | None = None):
    label, icon_id = _button_text(key, text)
    kwargs = {"text": label, "icon_custom_emoji_id": icon_id}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    builder.button(**kwargs)


# ==================== FOYDALANUVCHI KLAVIATURALARI ====================

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb_button("search", "Kino izlash")],
            [_kb_button("movie", "Random kino"), _kb_button("help", "Yordam")],
            [_kb_button("categories", "Kategoriyalar"), _kb_button("confirm", "VIP")],
            [_kb_button("movie", "Kino buyurtma qilish")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[_kb_button("back", "Bekor qilish")]],
        resize_keyboard=True,
    )


def subscribe_kb(channel_username: str) -> InlineKeyboardMarkup:
    username = channel_username.lstrip("@")
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "channel", "Kanalga a'zo bo'lish", url=f"https://t.me/{username}")
    _ikb_button(builder, "confirm", "Tekshirish", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()


def categories_kb(categories: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in categories:
        _ikb_button(builder, "categories", str(c["name"]), callback_data=f"cat:{c['name']}")
    builder.adjust(2)
    return builder.as_markup()


def search_results_kb(movies: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in movies:
        key = "confirm" if m["is_vip"] else "movie"
        _ikb_button(builder, key, str(m["title"]), callback_data=f"movie:{m['code']}")
    builder.adjust(1)
    return builder.as_markup()


def vip_menu_kb(user_is_vip: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not user_is_vip:
        _ikb_button(builder, "confirm", "VIP olish", callback_data="vip_info")
    builder.adjust(1)
    return builder.as_markup()


# ==================== ADMIN KLAVIATURALARI ====================

def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb_button("movie", "Kino qo'shish"), _kb_button("delete", "Kino o'chirish")],
            [_kb_button("edit", "Kino tahrirlash"), _kb_button("categories", "Kategoriyalar")],
            [_kb_button("channel", "Kanalni indekslash"), _kb_button("movie", "Buyurtmalar")],
            [_kb_button("users", "Foydalanuvchilar"), _kb_button("statistics", "Statistika")],
            [_kb_button("broadcast", "Reklama yuborish"), _kb_button("confirm", "VIP foydalanuvchilar")],
            [_kb_button("error", "Ban qilish"), _kb_button("success", "Bandan chiqarish")],
            [_kb_button("settings", "Sozlamalar"), _kb_button("info", "Zaxira nusxa")],
            [_kb_button("delete", "Tiklash")],
            [_kb_button("home", "Asosiy menyu")],
            [_kb_button("test", "Emojilarni tekshirish")],
        ],
        resize_keyboard=True,
    )


def admin_categories_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "movie", "Kategoriya qo'shish", callback_data="admcat_add")
    _ikb_button(builder, "delete", "Kategoriya o'chirish", callback_data="admcat_del")
    _ikb_button(builder, "channel", "Ro'yxat", callback_data="admcat_list")
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(action: str, code) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "confirm", "Ha, tasdiqlayman", callback_data=f"confirm:{action}:{code}")
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="confirm_cancel")
    builder.adjust(1)
    return builder.as_markup()


def category_pick_kb(categories: list, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in categories:
        _ikb_button(builder, "categories", str(c["name"]), callback_data=f"{prefix}:{c['name']}")
    builder.adjust(2)
    return builder.as_markup()


def edit_movie_kb(code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "edit", "Nomini o'zgartirish", callback_data=f"editmovie_title:{code}")
    _ikb_button(builder, "categories", "Kategoriyasini o'zgartirish", callback_data=f"editmovie_cat:{code}")
    _ikb_button(builder, "confirm", "VIP holatini almashtirish", callback_data=f"editmovie_vip:{code}")
    builder.adjust(1)
    return builder.as_markup()


def order_action_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "success", "Bajarildi deb belgilash", callback_data=f"order_done:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "broadcast", "Yuborishni boshlash", callback_data="bcast_send")
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="bcast_cancel")
    builder.adjust(1)
    return builder.as_markup()
