# 🎬 Kino Bot — Premium Telegram Kino Boti

To'liq o'zbek tilida ishlaydigan, zamonaviy va professional ko'rinishga ega Telegram kino boti.
Kino kod bo'yicha, nom bo'yicha izlash, kategoriyalar, VIP tizimi, buyurtma tizimi va to'liq admin panelga ega.

## ⚙️ Imkoniyatlar

- 🔎 Kino nomi bo'yicha izlash
- 🔢 Kod orqali kino olish (kanal post ID si)
- 🎲 Tasodifiy kino
- 📂 Kategoriyalar bo'yicha kinolar
- 💎 VIP tizimi (VIP kinolar, muddatli VIP a'zolik)
- 📦 Kino buyurtma qilish (foydalanuvchi so'rovlari)
- 📢 Majburiy obuna (ixtiyoriy)
- 🛠 To'liq admin panel:
  - Kino qo'shish / o'chirish / tahrirlash
  - Kategoriyalarni boshqarish
  - Kanalni avtomatik indekslash
  - Buyurtmalarni ko'rish va bajarish
  - Foydalanuvchilar ro'yxati va statistika
  - Reklama (broadcast) yuborish
  - VIP foydalanuvchilarni boshqarish
  - Ban / Bandan chiqarish
  - Sozlamalar (majburiy kanal)
  - Zaxira nusxa olish va tiklash

## 📦 O'rnatish

1. Python 3.10+ o'rnatilgan bo'lishi kerak.

2. Kerakli kutubxonalarni o'rnating:

```bash
pip install -r requirements.txt
```

3. `.env.example` faylidan nusxa oling va `.env` deb nomlang:

```bash
cp .env.example .env
```

4. `.env` faylini o'zingizga moslab to'ldiring:
   - `BOT_TOKEN` — @BotFather dan olingan token
   - `ADMIN_IDS` — sizning Telegram ID(lar)ingiz
   - `CHANNEL_ID` — kinolar joylashadigan kanal ID si (bot o'sha kanalda **admin** bo'lishi shart)
   - `REQUIRED_CHANNEL` — majburiy obuna kanali (ixtiyoriy)
   - `STICKER_ID` — start xabarida yuboriladigan stiker file_id (ixtiyoriy)

5. Botni ishga tushiring:

```bash
python main.py
```

## 🎬 Kinolarni qo'shish

**Usul 1 — Qo'lda qo'shish:**
Admin panelda `➕ Kino qo'shish` tugmasini bosing, so'ng kanaldagi kerakli postni botga forward qiling, nom va kategoriyani kiriting.

**Usul 2 — Avtomatik indekslash:**
Admin panelda `🔄 Kanalni indekslash` tugmasini bosing — bot kanaldagi barcha postlarni avtomatik tarzda skanerlab, bazaga qo'shadi (nomlarni keyinchalik `✏ Kino tahrirlash` orqali to'g'rilashingiz mumkin).

## 🔑 Admin buyrug'i

Botga `/admin` buyrug'ini yuborish orqali admin panelga kirasiz (faqat `.env` da ko'rsatilgan ADMIN_IDS uchun ishlaydi).

## 🗂 Loyiha tuzilishi

```
kino_bot/
├── main.py             # Botni ishga tushirish
├── config.py           # Sozlamalar (.env dan o'qiydi)
├── database.py         # SQLite bilan ishlash
├── keyboards.py        # Barcha klaviaturalar
├── states.py           # FSM holatlari
├── utils.py            # Yordamchi funksiyalar
├── handlers/
│   ├── user.py          # Foydalanuvchi funksiyalari
│   └── admin.py         # Admin panel funksiyalari
├── requirements.txt
└── .env.example
```

## ⚠️ Eslatmalar

- Bot media fayllarni **hech qachon qayta yuklamaydi** — `copyMessage()` orqali to'g'ridan-to'g'ri kanaldan nusxalab yuboradi.
- Zaxira nusxa faqat ma'lumotlar bazasini (foydalanuvchilar, kinolar ro'yxati va h.k.) o'z ichiga oladi, kino fayllarining o'zini emas — bular kanalda saqlanadi.


## 🎨 Telegram Premium Custom Emoji

Botning barcha UI emoji sozlamalari `custom_emojis.py` va `emoji_helper.py` orqali boshqariladi.

### ID qayerga yoziladi?

`custom_emojis.py` faylida:

```python
CUSTOM_EMOJIS = {
    "movie": "5375464961822695044",
    "search": "5429571366384842791",

    # ID topilmagan emoji uchun:
    "greeting": "",
}
```

ID topilmasa qiymatni bo'sh qoldiring. Bot oddiy Unicode emoji bilan davom etadi.

Bot ishga tushganda `getCustomEmojiStickers` orqali kiritilgan IDlar tekshiriladi. Noto'g'ri IDlar avtomatik Unicode fallbackga o'tadi.

### Buttonlar

Reply va Inline buttonlar `icon_custom_emoji_id` orqali haqiqiy Telegram Custom Emoji ikonkasini ishlatadi. Shu sababli button matnining boshida oddiy `🎬` kabi emoji yozilmaydi — Telegram ikonka sifatida Custom Emoji'ni o'zi ko'rsatadi.

Bu funksiya Bot API 9.4 va undan yuqori hamda mos aiogram versiyasini talab qiladi. Bot egasining Telegram Premium obunasi ham kerak. 

### Haqiqiy test

Admin panelda:

`🧪 Emojilarni tekshirish`

tugmasini bosing.

U ikki narsani tekshiradi:

1. Custom Emoji ID Telegram tomonidan topiladimi.
2. Xabarda `custom_emoji` entity va buttonlarda `icon_custom_emoji_id` ishlatiladimi.

Agar Premium imkoniyati yoki ID bilan muammo bo'lsa, bot yiqilmaydi — Unicode fallback ishlaydi.

### Muhim

Bot tokenini `.env` ichida saqlang va uni hech qachon GitHub yoki chatga joylamang.
