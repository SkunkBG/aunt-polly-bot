from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional


def start_keyboard():
    """Клавиатура для обычного пользователя."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❔ FAQ (Частые вопросы)", callback_data="faq")]
    ])


# ============================================================================
# ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ
# ============================================================================

def admin_start_keyboard():
    """Главная клавиатура для администратора с категориями."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_dashboard")],
        [
            InlineKeyboardButton(text="✨ Приветствие", callback_data="admin_welcome_menu"),
            InlineKeyboardButton(text="⏰ Автоответчик", callback_data="admin_autoresponder_menu"),
        ],
        [
            InlineKeyboardButton(text="🗂️ FAQ", callback_data="admin_manage_faq"),
            InlineKeyboardButton(text="🧠 ИИ", callback_data="admin_manage_ai"),
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_menu"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast_menu"),
        ],
        [
            InlineKeyboardButton(text="⚡ Быстрые ответы", callback_data="admin_quick_replies"),
            InlineKeyboardButton(text="🎯 Триггеры", callback_data="admin_triggers_menu"),
        ],
        [
            InlineKeyboardButton(text="🗄️ Бэкапы", callback_data="admin_manage_backups"),
            InlineKeyboardButton(text="🌐 Remnawave", callback_data="admin_remnawave_menu"),
        ],
        [
            InlineKeyboardButton(text="🌍 Языки", callback_data="admin_multilang_menu"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin_notifications_menu"),
        ],
        [InlineKeyboardButton(text="⚙️ Режим работы", callback_data="admin_work_mode_menu")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="admin_help_menu")],
    ])


# ============================================================================
# СТАТИСТИКА / ДАШБОРД
# ============================================================================

def dashboard_keyboard():
    """Клавиатура дашборда."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_dashboard_refresh")],
        [InlineKeyboardButton(text="📤 Экспорт пользователей (CSV)", callback_data="admin_export_users")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


# ============================================================================
# ПРИВЕТСТВИЕ
# ============================================================================

def welcome_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текст приветствия", callback_data="admin_welcome_change_text")],
        [InlineKeyboardButton(text="🖼️ Изображение приветствия", callback_data="admin_welcome_change_image")],
        [InlineKeyboardButton(text="👁️ Предпросмотр", callback_data="admin_welcome_preview")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


# ============================================================================
# АВТООТВЕТЧИК
# ============================================================================

def autoresponder_menu_keyboard(settings: dict):
    """Меню автоответчика."""
    work_mode = settings.get('work_mode', 'custom')  # '24/7' или 'custom'
    work_start = settings.get('work_hour_start', 9)
    work_end = settings.get('work_hour_end', 18)
    
    # Текст режима работы
    if work_mode == '24/7':
        mode_text = "🌐 Режим: 24/7 (всегда онлайн)"
    else:
        mode_text = f"🕘 Режим: {work_start:02d}:00 - {work_end:02d}:00"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mode_text, callback_data="admin_work_mode_info")],
        [
            InlineKeyboardButton(text="🌐 24/7", callback_data="admin_set_mode_247"),
            InlineKeyboardButton(text="🕘 По часам", callback_data="admin_set_mode_custom"),
        ],
        [InlineKeyboardButton(text="⏰ Настроить часы", callback_data="admin_change_hours")],
        [InlineKeyboardButton(text="💬 Сообщение вне часов", callback_data="admin_change_off_hours_msg")],
        [InlineKeyboardButton(text="👁️ Предпросмотр", callback_data="admin_autoresponder_preview")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


# ============================================================================
# FAQ
# ============================================================================

def faq_management_keyboard():
    """Клавиатура для управления FAQ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Просмотр всех FAQ", callback_data="admin_view_all_faq")],
        [
            InlineKeyboardButton(text="＋ Добавить", callback_data="admin_add_faq"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="admin_edit_faq_list"),
        ],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data="admin_delete_faq")],
        [InlineKeyboardButton(text="🔍 Порог поиска", callback_data="admin_faq_threshold")],
        [
            InlineKeyboardButton(text="📤 JSON", callback_data="admin_export_faq"),
            InlineKeyboardButton(text="📤 CSV", callback_data="admin_export_faq_csv"),
        ],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")]
    ])


def faq_questions_keyboard(faq_list: list):
    """Генерирует клавиатуру со списком вопросов FAQ для пользователя."""
    buttons = []
    for index, item in enumerate(faq_list):
        question_text = (item['question'][:50] + '...') if len(item['question']) > 50 else item['question']
        buttons.append([InlineKeyboardButton(
            text=f"❔ {question_text}",
            callback_data=f"show_faq_{index}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dynamic_delete_faq_keyboard(faq_list: list):
    """Генерирует клавиатуру со списком FAQ для удаления."""
    buttons = []
    for index, item in enumerate(faq_list):
        question_text = (item['question'][:25] + '...') if len(item['question']) > 25 else item['question']
        buttons.append([InlineKeyboardButton(
            text=f"🗑️ {question_text}",
            callback_data=f"admin_confirm_delete_faq_{index}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_manage_faq")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dynamic_edit_faq_keyboard(faq_list: list):
    """Генерирует клавиатуру со списком FAQ для редактирования."""
    buttons = []
    for index, item in enumerate(faq_list):
        question_text = (item['question'][:25] + '...') if len(item['question']) > 25 else item['question']
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {question_text}",
            callback_data=f"admin_edit_faq_{index}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_manage_faq")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def faq_edit_options_keyboard(faq_index: int):
    """Опции редактирования конкретного FAQ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить вопрос", callback_data=f"admin_edit_faq_q_{faq_index}")],
        [InlineKeyboardButton(text="💬 Изменить ответ", callback_data=f"admin_edit_faq_a_{faq_index}")],
        [InlineKeyboardButton(text="🖼️ Изменить медиа", callback_data=f"admin_edit_faq_m_{faq_index}")],
        [InlineKeyboardButton(text="🗑️ Удалить медиа", callback_data=f"admin_remove_faq_media_{faq_index}")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_edit_faq_list")],
    ])


def skip_media_keyboard():
    """Кнопка для пропуска добавления медиа к FAQ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="» Пропустить (без медиа)", callback_data="skip_faq_media")],
        [InlineKeyboardButton(text="‹ В админ-панель", callback_data="admin_back_to_main")]
    ])


def skip_edit_media_keyboard(faq_index: int):
    """Кнопка для пропуска редактирования медиа FAQ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="» Оставить текущее", callback_data=f"admin_skip_edit_media_{faq_index}")],
        [InlineKeyboardButton(text="‹ Назад", callback_data=f"admin_edit_faq_{faq_index}")]
    ])


# ============================================================================
# ИИ
# ============================================================================

def ai_management_keyboard(settings: dict):
    """Генерирует клавиатуру управления ИИ."""
    ai_enabled = settings.get('ai_enabled', False)
    active_ai = settings.get('active_ai', 'none')

    toggle_text = "🟢 ИИ: ВКЛЮЧЕН" if ai_enabled else "🔴 ИИ: ВЫКЛЮЧЕН"

    gemini_text = "✨ Gemini" + (" ✦" if active_ai == 'gemini' and ai_enabled else "")
    groq_text = "⚡️ Groq" + (" ✦" if active_ai == 'groq' and ai_enabled else "")

    buttons = [
        [InlineKeyboardButton(text=toggle_text, callback_data="admin_toggle_ai")],
        [
            InlineKeyboardButton(text=gemini_text, callback_data="admin_select_gemini"),
            InlineKeyboardButton(text=groq_text, callback_data="admin_select_groq")
        ],
        [InlineKeyboardButton(text="🪄 Системный промпт", callback_data="admin_change_prompt")],
        [InlineKeyboardButton(text="🔬 Выбор модели", callback_data="admin_select_ai_model")],
        [InlineKeyboardButton(text="🧪 Тест ИИ", callback_data="admin_test_ai")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ai_model_selection_keyboard(service: str, models: List[str], current_model: Optional[str]):
    """Клавиатура выбора конкретной модели ИИ."""
    buttons = []
    for model in models:
        mark = " ✓" if model == current_model else ""
        buttons.append([InlineKeyboardButton(
            text=f"{model}{mark}",
            callback_data=f"admin_set_model_{service}_{model}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_manage_ai")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ai_test_keyboard():
    """Клавиатура для тестирования ИИ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Тест ещё раз", callback_data="admin_test_ai")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_manage_ai")]
    ])


# ============================================================================
# БЭКАПЫ
# ============================================================================

def backup_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Создать бэкап сейчас", callback_data="admin_backup_create")],
        [InlineKeyboardButton(text="📤 Отправить последний бэкап", callback_data="admin_backup_send_last")],
        [InlineKeyboardButton(text="⏰ Время ежедневного бэкапа", callback_data="admin_backup_set_time")],
        [InlineKeyboardButton(text="♻️ Восстановить", callback_data="admin_backup_restore_menu")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")]
    ])


def backup_restore_keyboard(backup_titles: list[str]):
    buttons = []
    for i, title in enumerate(backup_titles):
        buttons.append([InlineKeyboardButton(text=f"♻️ {title}", callback_data=f"admin_restore_backup_{i}")])
    buttons.append([InlineKeyboardButton(text="⬆️ Восстановить из файла", callback_data="admin_backup_restore_upload")])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_manage_backups")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================================

def users_menu_keyboard():
    """Меню управления пользователями."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_users_search")],
        [
            InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_users_block"),
            InlineKeyboardButton(text="✅ Разблокировать", callback_data="admin_users_unblock"),
        ],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_users_stats")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


def users_list_keyboard(users: list, page: int = 0, per_page: int = 10):
    """Пагинированный список пользователей."""
    buttons = []
    start = page * per_page
    end = start + per_page
    page_users = users[start:end]
    
    for user in page_users:
        uid = user.get('user_id', 0)
        name = user.get('name', 'Unknown')[:20]
        username = user.get('username', '')
        blocked = "🚫" if user.get('blocked') else ""
        display = f"{blocked}{name}"
        if username:
            display += f" (@{username[:15]})"
        buttons.append([InlineKeyboardButton(
            text=display,
            callback_data=f"admin_user_info_{uid}"
        )])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
    if end < len(users):
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"admin_users_page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="‹ Меню пользователей", callback_data="admin_users_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_info_keyboard(user_id: int, is_blocked: bool):
    """Клавиатура информации о пользователе."""
    block_btn = InlineKeyboardButton(
        text="✅ Разблокировать" if is_blocked else "🚫 Заблокировать",
        callback_data=f"admin_toggle_block_{user_id}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [block_btn],
        [InlineKeyboardButton(text="💬 Написать", callback_data=f"reply_to_{user_id}")],
        [InlineKeyboardButton(text="‹ К списку", callback_data="admin_users_list")],
    ])


# ============================================================================
# РАССЫЛКА
# ============================================================================

def broadcast_menu_keyboard():
    """Меню рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Новая рассылка", callback_data="admin_broadcast_new")],
        [InlineKeyboardButton(text="📜 История рассылок", callback_data="admin_broadcast_history")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


def broadcast_confirm_keyboard():
    """Подтверждение рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить всем", callback_data="admin_broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast_cancel"),
        ],
    ])


def broadcast_done_keyboard():
    """После завершения рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Ещё рассылка", callback_data="admin_broadcast_new")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_broadcast_menu")],
    ])


# ============================================================================
# ОБЩИЕ
# ============================================================================

def admin_reply_keyboard(user_id: int):
    """Клавиатура для ответа админа пользователю."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить пользователю", callback_data=f"reply_to_{user_id}")]
    ])


def back_to_admin_panel():
    """Кнопка "Назад" для возврата в главное меню админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="‹ В админ-панель", callback_data="admin_back_to_main")]
    ])


def back_to_faq_management():
    """Кнопка возврата к управлению FAQ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="‹ К управлению FAQ", callback_data="admin_manage_faq")]
    ])


def confirm_action_keyboard(confirm_callback: str, cancel_callback: str):
    """Универсальная клавиатура подтверждения."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data=cancel_callback),
        ],
    ])


# ============================================================================
# СПРАВКА
# ============================================================================

def help_menu_keyboard():
    """Меню справки по админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 О статистике", callback_data="admin_help_dashboard")],
        [InlineKeyboardButton(text="✨ О приветствии", callback_data="admin_help_welcome")],
        [InlineKeyboardButton(text="⏰ Об автоответчике", callback_data="admin_help_autoresponder")],
        [InlineKeyboardButton(text="🗂️ О FAQ", callback_data="admin_help_faq")],
        [InlineKeyboardButton(text="🧠 Об ИИ", callback_data="admin_help_ai")],
        [InlineKeyboardButton(text="👥 О пользователях", callback_data="admin_help_users")],
        [InlineKeyboardButton(text="📢 О рассылке", callback_data="admin_help_broadcast")],
        [InlineKeyboardButton(text="🗄️ О бэкапах", callback_data="admin_help_backups")],
        [InlineKeyboardButton(text="📝 HTML-разметка", callback_data="admin_help_html")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])


def help_back_keyboard():
    """Кнопка возврата к справке."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="‹ К справке", callback_data="admin_help_menu")],
        [InlineKeyboardButton(text="‹ В админ-панель", callback_data="admin_back_to_main")],
    ])
