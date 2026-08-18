from aiogram.enums import ButtonStyle
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from custom_emojis import EMOJI_FALLBACKS, CUSTOM_EMOJIS
from emoji_helper import valid_custom_emoji_id


def _button_text(key: str, text: str) -> tuple[str, str | None]:
    """Return button label and actual Telegram Custom Emoji icon ID."""
    icon_id = valid_custom_emoji_id(key)
    if icon_id:
        return text, icon_id
    fallback = EMOJI_FALLBACKS.get(key, "")
    return f"{fallback} {text}".strip() if fallback else text, None


def _ikb_button(
    builder: InlineKeyboardBuilder,
    key: str,
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    switch_inline_query_current_chat: str | None = None,
    style: ButtonStyle | None = None,
):
    label, icon_id = _button_text(key, text)
    kwargs = {"text": label, "icon_custom_emoji_id": icon_id}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if switch_inline_query_current_chat is not None:
        kwargs["switch_inline_query_current_chat"] = switch_inline_query_current_chat
    if style is not None:
        kwargs["style"] = style
    builder.button(**kwargs)


# ==================== FOYDALANUVCHI KLAVIATURALARI ====================

def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Asosiy menyu — faqat Inline tugmalar, rangli va stiker emojili.
    """
    builder = InlineKeyboardBuilder()
    # VIP — PRIMARY (ko'k)
    builder.button(
        text="VIP",
        icon_custom_emoji_id="5843804967625821763",
        callback_data="menu_vip",
        style=ButtonStyle.PRIMARY,
    )
    # Yordam — PRIMARY (ko'k)
    builder.button(
        text="Yordam",
        icon_custom_emoji_id="5458481637362778614",
        callback_data="menu_help",
        style=ButtonStyle.PRIMARY,
    )
    # Kategoriyalar — PRIMARY (ko'k)
    builder.button(
        text="Kategoriyalar",
        icon_custom_emoji_id="5341492148468465410",
        callback_data="menu_categories",
        style=ButtonStyle.PRIMARY,
    )

    # Kino buyurtma qilish — SUCCESS (yashil)
    builder.button(
        text="Kino buyurtma",
        icon_custom_emoji_id="5258134813302332906",
        callback_data="menu_order",
        style=ButtonStyle.SUCCESS,
    )

    # Random kino — SUCCESS (yashil)
    builder.button(
        text="Random kino",
        icon_custom_emoji_id="5235588635885054955",
        callback_data="menu_random",
        style=ButtonStyle.SUCCESS,
    )

    # Kino qidirish — bosilganda to'g'ridan-to'g'ri Inline Mode ochiladi!
    builder.button(
        text="Kino qidirish",
        icon_custom_emoji_id="5429571366384842791",
        switch_inline_query_current_chat="",
        style=ButtonStyle.PRIMARY,
    )
    builder.adjust(2, 2, 2)
    return builder.as_markup()



def cancel_kb() -> InlineKeyboardMarkup:
    """Inline Bekor qilish tugmasi."""
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="cancel_action", style=ButtonStyle.DANGER)
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """Asosiy menyuga qaytish inline tugmasi."""
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "home", "Asosiy menyu", callback_data="back_to_main", style=ButtonStyle.PRIMARY)
    return builder.as_markup()


def subscribe_kb(channel_username: str) -> InlineKeyboardMarkup:
    ch = (channel_username or "").strip()
    if ch.startswith("https://") or ch.startswith("http://"):
        url = ch
    elif ch.startswith("-100"):
        url = f"https://t.me/c/{ch.replace('-100', '')}"
    else:
        username = ch.lstrip("@")
        url = f"https://t.me/{username}"
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "channel", "Kanalga a'zo bo'lish", url=url, style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "confirm", "Tekshirish", callback_data="check_sub", style=ButtonStyle.SUCCESS)
    builder.adjust(1)
    return builder.as_markup()


def categories_kb(categories: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in categories:
        _ikb_button(builder, "categories", str(c["name"]), callback_data=f"cat:{c['name']}", style=ButtonStyle.PRIMARY)
    builder.adjust(2)
    return builder.as_markup()


def search_results_kb(movies: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in movies:
        key = "confirm" if m["is_vip"] else "movie"
        style = ButtonStyle.SUCCESS if m["is_vip"] else ButtonStyle.PRIMARY
        title_str = f"#{m['code']} | {m['title']}"
        _ikb_button(builder, key, title_str, callback_data=f"movie:{m['code']}", style=style)
    builder.adjust(1)
    return builder.as_markup()


def vip_menu_kb(user_is_vip: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not user_is_vip:
        _ikb_button(builder, "confirm", "VIP olish", callback_data="vip_info", style=ButtonStyle.SUCCESS)
    builder.adjust(1)
    return builder.as_markup()


# ==================== ADMIN KLAVIATURALARI ====================

def admin_menu_kb() -> InlineKeyboardMarkup:
    """Admin menyusi — to'liq Inline klaviatura."""
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "movie", "Kino qo'shish", callback_data="adm_add_movie", style=ButtonStyle.SUCCESS)
    _ikb_button(builder, "delete", "Kino o'chirish", callback_data="adm_del_movie", style=ButtonStyle.DANGER)
    _ikb_button(builder, "edit", "Kino tahrirlash", callback_data="adm_edit_movie", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "categories", "Kategoriyalar", callback_data="adm_categories", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "channel", "Kanalni indekslash", callback_data="adm_index_channel", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "movie", "Buyurtmalar", callback_data="adm_orders", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "users", "Foydalanuvchilar", callback_data="adm_users", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "statistics", "Statistika", callback_data="adm_stats", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "broadcast", "Reklama yuborish", callback_data="adm_broadcast", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "confirm", "VIP foydalanuvchilar", callback_data="adm_vip_users", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "error", "Ban qilish", callback_data="adm_ban", style=ButtonStyle.DANGER)
    _ikb_button(builder, "success", "Bandan chiqarish", callback_data="adm_unban", style=ButtonStyle.SUCCESS)
    _ikb_button(builder, "settings", "Sozlamalar", callback_data="adm_settings", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "info", "Zaxira nusxa", callback_data="adm_backup", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "delete", "Tiklash", callback_data="adm_restore", style=ButtonStyle.DANGER)
    _ikb_button(builder, "test", "Emojilarni tekshirish", callback_data="adm_emoji_test", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "home", "Asosiy menyu", callback_data="back_to_main", style=ButtonStyle.PRIMARY)
    builder.adjust(2, 2, 2, 2, 2, 2, 2, 1, 1, 1)
    return builder.as_markup()


def admin_categories_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "movie", "Kategoriya qo'shish", callback_data="admcat_add", style=ButtonStyle.SUCCESS)
    _ikb_button(builder, "delete", "Kategoriya o'chirish", callback_data="admcat_del", style=ButtonStyle.DANGER)
    _ikb_button(builder, "channel", "Ro'yxat", callback_data="admcat_list", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "back", "Admin panelga qaytish", callback_data="adm_back_to_panel", style=ButtonStyle.PRIMARY)
    builder.adjust(1)
    return builder.as_markup()


def confirm_kb(action: str, code) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "confirm", "Ha, tasdiqlayman", callback_data=f"confirm:{action}:{code}", style=ButtonStyle.DANGER)
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="confirm_cancel", style=ButtonStyle.PRIMARY)
    builder.adjust(1)
    return builder.as_markup()


def category_pick_kb(categories: list, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in categories:
        _ikb_button(builder, "categories", str(c["name"]), callback_data=f"{prefix}:{c['name']}", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="cancel_action", style=ButtonStyle.DANGER)
    builder.adjust(2)
    return builder.as_markup()


def edit_movie_kb(code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "edit", "Nomini o'zgartirish", callback_data=f"editmovie_title:{code}", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "categories", "Kategoriyasini o'zgartirish", callback_data=f"editmovie_cat:{code}", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "confirm", "VIP holatini almashtirish", callback_data=f"editmovie_vip:{code}", style=ButtonStyle.PRIMARY)
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="cancel_action", style=ButtonStyle.DANGER)
    builder.adjust(1)
    return builder.as_markup()


def order_action_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "success", "Bajarildi deb belgilash", callback_data=f"order_done:{order_id}", style=ButtonStyle.SUCCESS)
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ikb_button(builder, "broadcast", "Yuborishni boshlash", callback_data="bcast_send", style=ButtonStyle.SUCCESS)
    _ikb_button(builder, "cancel", "Bekor qilish", callback_data="bcast_cancel", style=ButtonStyle.DANGER)
    builder.adjust(1)
    return builder.as_markup()
