import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from emoji_helper import validate_custom_emojis
from handlers import admin, user, inline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "❗ BOT_TOKEN topilmadi! .env faylida BOT_TOKEN qiymatini kiriting."
        )

    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Validate the configured Telegram Custom Emoji IDs before the bot starts
    # serving users. Invalid IDs are automatically treated as Unicode fallback.
    try:
        valid_ids, emoji_status = await validate_custom_emojis(bot)
        logging.info("Custom Emoji: %d/%d ID Telegram tomonidan tasdiqlandi.", len(valid_ids), len(emoji_status))
        if "_global" in emoji_status:
            logging.warning(emoji_status["_global"])
        for key, status in emoji_status.items():
            if key != "_global" and status != "OK":
                logging.warning("Custom Emoji [%s]: %s", key, status)
    except Exception:
        logging.exception("Custom Emoji tekshiruvida kutilmagan xato. Unicode fallback ishlatiladi.")

    dp = Dispatcher(storage=MemoryStorage())

    # Admin router birinchi bo'lib ulanadi (ustuvorlik uchun)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(inline.router)

    from aiogram.types import BotCommand, BotCommandScopeDefault

    # Bot buyruqlari menyusi (/ bosganda chiqadigan buyruqlar)
    commands = [
        BotCommand(command="start", description="🎬 Botni ishga tushirish / Asosiy menyu"),
        BotCommand(command="admin", description="🛠 Admin panel (Faqat adminlar uchun)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🤖 Bot ishga tushdi...")

    # Render Web Service uchun Health Check serveri (PORT tinglash)
    try:
        import os
        from aiohttp import web

        async def handle_ping(request):
            return web.Response(text="Bot is running! 🤖")

        app = web.Application()
        app.router.add_get("/", handle_ping)
        app.router.add_get("/ping", handle_ping)
        app.router.add_get("/health", handle_ping)

        port = int(os.getenv("PORT", "10000"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logging.info(f"🌐 Health-check server PORT {port} da ishga tushdi.")
    except Exception as e:
        logging.warning(f"⚠️ Health-check serverni ishga tushirishda ogohlantirish: {e}")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())




if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot to'xtatildi.")
