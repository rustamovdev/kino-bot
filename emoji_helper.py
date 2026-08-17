"""
Telegram Custom Emoji rendering helpers.

This module converts the bot's existing HTML-formatted text into Telegram
MessageEntity objects and attaches Custom Emoji entities to the UI emoji
characters. This is necessary because putting a numeric Custom Emoji ID into
a string does NOT render a Premium Custom Emoji.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, MessageEntity
from aiogram.enums import MessageEntityType

from custom_emojis import CUSTOM_EMOJIS, EMOJI_FALLBACKS, emoji_id


# IDs confirmed by getCustomEmojiStickers. If startup validation cannot run,
# configured IDs are used and Telegram errors are handled with a safe fallback.
_VALID_CUSTOM_EMOJI_IDS: set[str] | None = None


def set_valid_custom_emoji_ids(ids: set[str] | None) -> None:
    global _VALID_CUSTOM_EMOJI_IDS
    _VALID_CUSTOM_EMOJI_IDS = ids


def valid_custom_emoji_id(key: str) -> str | None:
    value = emoji_id(key)
    if not value:
        return None
    if _VALID_CUSTOM_EMOJI_IDS is None:
        return value
    return value if value in _VALID_CUSTOM_EMOJI_IDS else None


def _utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _emoji_patterns() -> list[tuple[str, str]]:
    pairs = []
    for key, char in EMOJI_FALLBACKS.items():
        if char and valid_custom_emoji_id(key):
            pairs.append((char, key))
    # Longest first: e.g. "⚙️" before "⚙".
    return sorted(pairs, key=lambda item: len(item[0]), reverse=True)


class _UIHTMLParser(HTMLParser):
    """Small HTML -> MessageEntity renderer for the bot's existing UI text."""

    TAG_TO_ENTITY = {
        "b": MessageEntityType.BOLD,
        "strong": MessageEntityType.BOLD,
        "i": MessageEntityType.ITALIC,
        "em": MessageEntityType.ITALIC,
        "u": MessageEntityType.UNDERLINE,
        "ins": MessageEntityType.UNDERLINE,
        "s": MessageEntityType.STRIKETHROUGH,
        "strike": MessageEntityType.STRIKETHROUGH,
        "del": MessageEntityType.STRIKETHROUGH,
        "tg-spoiler": MessageEntityType.SPOILER,
        "spoiler": MessageEntityType.SPOILER,
        "code": MessageEntityType.CODE,
        "pre": MessageEntityType.PRE,
        "blockquote": MessageEntityType.BLOCKQUOTE,
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.entities: list[MessageEntity] = []
        self._stack: list[tuple[str, str, int, dict[str, Any]]] = []
        self._offset = 0

    @property
    def text(self) -> str:
        return "".join(self.text_parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag == "br":
            self.text_parts.append("\n")
            self._offset += 1
            return

        entity_type = self.TAG_TO_ENTITY.get(tag)
        if entity_type:
            self._stack.append((tag, entity_type, self._offset, {}))
            return

        if tag == "a":
            href = attrs_dict.get("href")
            if href:
                self._stack.append((tag, MessageEntityType.TEXT_LINK, self._offset, {"url": href}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        # Find the most recent matching tag. This also keeps malformed but
        # harmless UI markup from crashing the bot.
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                _, entity_type, start, params = self._stack.pop(index)
                length = self._offset - start
                if length > 0:
                    self.entities.append(
                        MessageEntity(
                            type=entity_type,
                            offset=start,
                            length=length,
                            **params,
                        )
                    )
                break

    def _append_plain(self, value: str) -> None:
        if not value:
            return
        self.text_parts.append(value)
        self._offset += _utf16_len(value)

    def _inside_code(self) -> bool:
        return any(tag in {"code", "pre"} for tag, *_ in self._stack)

    def handle_data(self, data: str) -> None:
        if not data:
            return

        patterns = _emoji_patterns()
        if not patterns or self._inside_code():
            self._append_plain(data)
            return

        cursor = 0
        while cursor < len(data):
            best_pos = None
            best_char = None
            best_key = None

            for char, key in patterns:
                pos = data.find(char, cursor)
                if pos != -1 and (best_pos is None or pos < best_pos):
                    best_pos = pos
                    best_char = char
                    best_key = key

            if best_pos is None:
                self._append_plain(data[cursor:])
                break

            self._append_plain(data[cursor:best_pos])

            # The original Unicode emoji remains in the text. Telegram uses
            # this character range as the carrier for the custom_emoji entity.
            start = self._offset
            self._append_plain(best_char)
            self.entities.append(
                MessageEntity(
                    type=MessageEntityType.CUSTOM_EMOJI,
                    offset=start,
                    length=_utf16_len(best_char),
                    custom_emoji_id=valid_custom_emoji_id(best_key) or "",
                )
            )
            cursor = best_pos + len(best_char)


def render_ui_text(text: str) -> tuple[str, list[MessageEntity]]:
    """
    Render existing HTML text into plain text + entities, including
    Telegram Custom Emoji entities.

    This intentionally returns parse_mode=None-compatible data.
    """
    parser = _UIHTMLParser()
    parser.feed(text)
    parser.close()

    # Remove accidental empty/invalid custom emoji entities.
    parser.entities = [
        e for e in parser.entities
        if e.type != MessageEntityType.CUSTOM_EMOJI or e.custom_emoji_id
    ]
    parser.entities.sort(key=lambda e: (e.offset, -e.length))
    return parser.text, parser.entities



def _fallback_reply_markup(markup: Any) -> Any:
    """
    Remove Custom Emoji button icons and put the matching Unicode fallback
    back into button text. Used when Telegram rejects custom emoji buttons.
    """
    if markup is None or not hasattr(markup, "model_dump"):
        return markup

    data = markup.model_dump(exclude_none=True)
    reverse = {
        str(value): key
        for key, value in CUSTOM_EMOJIS.items()
        if str(value or "").strip()
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            icon = value.get("icon_custom_emoji_id")
            if icon:
                key = reverse.get(str(icon))
                value.pop("icon_custom_emoji_id", None)
                if key:
                    fallback = EMOJI_FALLBACKS.get(key, "")
                    text = str(value.get("text", ""))
                    if fallback and not text.startswith(fallback):
                        value["text"] = f"{fallback} {text}".strip()
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return type(markup)(**data)

async def answer_ui(message: Message, text: str, **kwargs: Any) -> Message:
    """Send a UI text message with Custom Emoji entities."""
    rendered_text, entities = render_ui_text(text)
    try:
        return await message.answer(
            text=rendered_text,
            entities=entities,
            parse_mode=None,
            **kwargs,
        )
    except TelegramBadRequest:
        # If Telegram rejects a custom emoji ID/capability, retry the same UI
        # with Unicode only. The bot must never crash because of an emoji.
        fallback_text, fallback_entities = render_ui_text_without_custom(text)
        retry_kwargs = dict(kwargs)
        if "reply_markup" in retry_kwargs:
            retry_kwargs["reply_markup"] = _fallback_reply_markup(retry_kwargs["reply_markup"])
        return await message.answer(
            text=fallback_text,
            entities=fallback_entities,
            parse_mode=None,
            **retry_kwargs,
        )


async def send_ui(bot: Bot, chat_id: int | str, text: str, **kwargs: Any) -> Message:
    """Bot.send_message equivalent with Custom Emoji entities."""
    rendered_text, entities = render_ui_text(text)
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=rendered_text,
            entities=entities,
            parse_mode=None,
            **kwargs,
        )
    except TelegramBadRequest:
        fallback_text, fallback_entities = render_ui_text_without_custom(text)
        retry_kwargs = dict(kwargs)
        if "reply_markup" in retry_kwargs:
            retry_kwargs["reply_markup"] = _fallback_reply_markup(retry_kwargs["reply_markup"])
        return await bot.send_message(
            chat_id=chat_id,
            text=fallback_text,
            entities=fallback_entities,
            parse_mode=None,
            **retry_kwargs,
        )


async def edit_ui(message: Message, text: str, **kwargs: Any) -> Message:
    """Edit an existing UI text message using Custom Emoji entities."""
    rendered_text, entities = render_ui_text(text)
    try:
        return await message.edit_text(
            text=rendered_text,
            entities=entities,
            parse_mode=None,
            **kwargs,
        )
    except TelegramBadRequest:
        fallback_text, fallback_entities = render_ui_text_without_custom(text)
        retry_kwargs = dict(kwargs)
        if "reply_markup" in retry_kwargs:
            retry_kwargs["reply_markup"] = _fallback_reply_markup(retry_kwargs["reply_markup"])
        return await message.edit_text(
            text=fallback_text,
            entities=fallback_entities,
            parse_mode=None,
            **retry_kwargs,
        )


def render_ui_text_without_custom(text: str) -> tuple[str, list[MessageEntity]]:
    """Same HTML renderer, but with all Custom Emoji IDs disabled."""
    global _VALID_CUSTOM_EMOJI_IDS
    old = _VALID_CUSTOM_EMOJI_IDS
    _VALID_CUSTOM_EMOJI_IDS = set()
    try:
        parser = _UIHTMLParser()
        parser.feed(text)
        parser.close()
        return parser.text, [
            e for e in parser.entities if e.type != MessageEntityType.CUSTOM_EMOJI
        ]
    finally:
        _VALID_CUSTOM_EMOJI_IDS = old


async def validate_custom_emojis(bot: Bot) -> tuple[set[str], dict[str, str]]:
    """
    Ask Telegram for the configured Custom Emoji stickers.

    Returns:
      valid IDs and a key -> error/status mapping.
    """
    ids = sorted({value for value in CUSTOM_EMOJIS.values() if str(value).strip()})
    if not ids:
        set_valid_custom_emoji_ids(set())
        return set(), {}

    try:
        stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=ids)
        valid = {str(s.custom_emoji_id) for s in stickers if s.custom_emoji_id}
        set_valid_custom_emoji_ids(valid)

        status: dict[str, str] = {}
        for key, value in CUSTOM_EMOJIS.items():
            value = str(value or "").strip()
            if not value:
                status[key] = "ID kiritilmagan — Unicode fallback"
            elif value in valid:
                status[key] = "OK"
            else:
                status[key] = "Telegram bu ID uchun sticker qaytarmadi"
        return valid, status
    except Exception as exc:
        # Do not disable everything just because validation endpoint failed.
        # Actual sends still have a safe fallback.
        set_valid_custom_emoji_ids(None)
        return set(), {"_global": f"Tekshiruv API xatosi: {type(exc).__name__}: {exc}"}
