from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    waiting_search_query = State()
    waiting_order_text = State()


class AdminStates(StatesGroup):
    # Kino qo'shish
    add_waiting_post = State()
    add_waiting_title = State()
    add_waiting_category = State()

    # Kino o'chirish
    delete_waiting_code = State()

    # Kino tahrirlash
    edit_waiting_code = State()
    edit_waiting_title = State()
    edit_waiting_category = State()

    # Kategoriyalar
    category_waiting_name = State()
    category_waiting_delete = State()

    # Kanalni indekslash
    indexing_in_progress = State()

    # Buyurtmalar
    order_waiting_reply = State()

    # Foydalanuvchilar / VIP / Ban
    vip_waiting_id = State()
    vip_waiting_days = State()
    vip_remove_waiting_id = State()
    ban_waiting_id = State()
    unban_waiting_id = State()

    # Reklama
    broadcast_waiting_content = State()

    # Sozlamalar
    settings_waiting_channel = State()

    # Zaxira / Tiklash
    restore_waiting_file = State()
