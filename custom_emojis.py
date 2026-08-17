"""
Telegram Premium Custom Emoji configuration.

All Custom Emoji IDs are kept here.
If an ID is empty, the bot falls back to the normal Unicode emoji.
"""

CUSTOM_EMOJIS: dict[str, str] = {
    "movie": "5368653135101310687",
    "search": "5429571366384842791",
    "settings": "5341715473882955310",
    "statistics": "5458905456145612048",
    "users": "5258513401784573443",
    "broadcast": "5422439358441497122",
    "delete": "5258130763148172425",
    "edit": "5956143844457189176",
    "back": "5388781950305580591",
    "cancel": "5260342697075416641",
    "success": "5260416304224936047",
    "error": "5260342697075416641",
    "warning": "5461137215641895106",
    "info": "6258179044362161727",
    "channel": "5402108679774282930",
    "admin": "5422364797809230911",
    "home": "6255948496046657099",
    "categories": "5341492148468465410",
    "help": "5458481637362778614",
    "confirm": "5260416304224936047",
    "vip": "5843804967625821763",
    "genre": "5350658016700013471",
    "year": "5274055917766202507",
    "code": "5226513232549664618",
    "emoji_settings": "6258088596645875061",
    "test": "5411138633765757782",
    "tech": "5258023599419171861",


    # Qo'shimcha UI emojilari
    "greeting": "5418115103763494597",
    "popcorn": "5371081166013078244",
    "random": "5235588635885054955",
    "lightbulb": "",
    "package": "5258134813302332906",
    "alert": "6255733820696300839",


    "question": "",
    "sparkles": "",
    "bolt": "",
    "gift": "",
    "down": "5470177992950946662",
    "pray": "",
    "sad": "",
    "id_card": "",
    "clock": "",
    "hourglass": "",
    "point_up": "",
    "money": "",
    "refresh": "",
    "plus": "",
    "minus": "",
    "ban": "",
    "folder": "5341492148468465410",
    "tools": "",
    "trash": "",
    "paperclip": "",
    "calendar": "",
    "recycle": "",
    "danger": "",
    "pending": "",
}

EMOJI_FALLBACKS: dict[str, str] = {
    "movie": "🎬",
    "search": "🔎",
    "settings": "⚙️",
    "statistics": "📊",
    "users": "👥",
    "broadcast": "📢",
    "delete": "🗑",
    "edit": "✏️",
    "back": "🔙",
    "cancel": "❌",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "channel": "📋",
    "admin": "👤",
    "home": "🏠",
    "categories": "📚",
    "help": "❓",
    "confirm": "✅",
    "genre": "🎭",
    "year": "📅",
    "code": "🔢",
    "emoji_settings": "🎨",
    "test": "🧪",
    "tech": "🔧",
    "greeting": "👋",
    "popcorn": "🍿",
    "random": "🎲",
    "lightbulb": "💡",
    "vip": "💎",
    "package": "📦",
    "alert": "❗",
    "question": "❓",
    "sparkles": "✨",
    "bolt": "⚡",
    "gift": "🎁",
    "down": "👇",
    "pray": "🙏",
    "sad": "😔",
    "id_card": "🆔",
    "clock": "🕒",
    "hourglass": "⏳",
    "point_up": "👆",
    "money": "💾",
    "refresh": "🔄",
    "plus": "➕",
    "minus": "➖",
    "ban": "🚫",
    "folder": "📂",
    "tools": "🛠",
    "trash": "🗑",
    "paperclip": "📎",
    "calendar": "📅",
    "recycle": "♻",
    "danger": "❗",
    "pending": "⏳",
}


def emoji_id(key: str) -> str | None:
    """Return a configured Custom Emoji ID, or None for Unicode fallback."""
    value = str(CUSTOM_EMOJIS.get(key, "") or "").strip()
    return value or None


def emoji_char(key: str) -> str:
    """Return the Unicode character used as the fallback/entity carrier."""
    return EMOJI_FALLBACKS.get(key, "🔹")
