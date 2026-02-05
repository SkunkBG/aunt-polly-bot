from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    # === Состояния для основных настроек ===
    waiting_for_welcome_message = State()
    waiting_for_work_hours = State()
    waiting_for_welcome_image = State()
    
    # === Состояния для FAQ ===
    waiting_for_faq_question = State()
    waiting_for_faq_answer = State()
    waiting_for_faq_media = State()
    
    # Редактирование FAQ
    waiting_for_faq_edit_question = State()
    waiting_for_faq_edit_answer = State()
    waiting_for_faq_edit_media = State()
    
    # Порог поиска FAQ
    waiting_for_faq_threshold = State()
    
    # === Состояния для ИИ ===
    waiting_for_ai_prompt = State()
    waiting_for_ai_test_message = State()
    
    # === Состояния для бэкапов ===
    waiting_for_backup_upload = State()
    waiting_for_backup_time = State()
    
    # === Состояния для рассылки ===
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_confirm = State()
    
    # === Состояния для автоответчика ===
    waiting_for_off_hours_message = State()
    
    # === Состояния для управления пользователями ===
    waiting_for_user_id_to_block = State()
    waiting_for_user_id_to_unblock = State()
    waiting_for_user_search = State()
    
    # === Состояния для Remnawave ===
    waiting_for_server_mapping = State()
    
    # === Состояния для режима работы ===
    waiting_for_group_id = State()
    
    # === Быстрые ответы ===
    waiting_for_quick_reply_name = State()
    waiting_for_quick_reply_text = State()
    
    # === Заметки о пользователях ===
    waiting_for_user_note = State()
    
    # === Триггеры (автоответы по ключевым словам) ===
    waiting_for_trigger_keyword = State()
    waiting_for_trigger_response = State()
