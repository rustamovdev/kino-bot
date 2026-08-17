import os
from dotenv import load_dotenv

load_dotenv()

# --- Asosiy sozlamalar (.env faylidan olinadi) ---

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin ID lar vergul bilan ajratilgan holda: 123456789,987654321
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Kinolar joylashgan kanal ID si (bot o'sha kanalda admin bo'lishi shart)
# Masalan: -1001234567890
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Majburiy obuna kanali (masalan: @mychannel). Bo'sh qoldirilsa, majburiy obuna o'chirilgan bo'ladi.
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")

# Ma'lumotlar bazasi fayli (SQLite) yoki Supabase PostgreSQL havolasi
DB_PATH = os.getenv("DB_PATH", "bot.db")
DATABASE_URL = os.getenv("DATABASE_URL", "")


# Start xabarida yuboriladigan premium animatsiyali stiker file_id
STICKER_ID = os.getenv("STICKER_ID", "")

# Zaxira nusxa fayllari saqlanadigan papka
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
