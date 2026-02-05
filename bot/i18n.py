"""
Модуль мультиязычности.
Поддержка русского и английского языков с автоопределением.
"""
import logging
from typing import Optional
from bot.config import load_json, SETTINGS_FILE

logger = logging.getLogger(__name__)

# Переводы
TRANSLATIONS = {
    "ru": {
        # Приветствие
        "welcome_default": "Здравствуйте! 👋 Чем могу помочь?",
        "welcome_new_user": "🆕 Добро пожаловать! Это ваше первое сообщение.",
        
        # FAQ
        "faq_found": "📖 <b>Нашёл ответ:</b>\n\n",
        "faq_button": "❔ FAQ (Частые вопросы)",
        
        # Автоответчик
        "off_hours_default": "Спасибо за сообщение! Ответим в рабочее время.",
        
        # Общие
        "message_received": "Сообщение получено. Ответим в ближайшее время.",
        "please_wait": "Подождите немного...",
        "error_occurred": "Произошла ошибка. Попробуйте позже.",
        
        # Rate limiting
        "rate_limit": "⚠️ Слишком много запросов. Подождите немного.",
        "user_banned": "🚫 Вы временно заблокированы за спам.",
    },
    "en": {
        # Welcome
        "welcome_default": "Hello! 👋 How can I help you?",
        "welcome_new_user": "🆕 Welcome! This is your first message.",
        
        # FAQ
        "faq_found": "📖 <b>Found an answer:</b>\n\n",
        "faq_button": "❔ FAQ (Frequently Asked Questions)",
        
        # Auto-responder
        "off_hours_default": "Thank you for your message! We'll respond during business hours.",
        
        # General
        "message_received": "Message received. We'll respond soon.",
        "please_wait": "Please wait...",
        "error_occurred": "An error occurred. Please try again later.",
        
        # Rate limiting
        "rate_limit": "⚠️ Too many requests. Please wait.",
        "user_banned": "🚫 You are temporarily banned for spam.",
    },
    # Украинский
    "uk": {
        "welcome_default": "Вітаю! 👋 Чим можу допомогти?",
        "welcome_new_user": "🆕 Ласкаво просимо! Це ваше перше повідомлення.",
        "faq_found": "📖 <b>Знайшов відповідь:</b>\n\n",
        "faq_button": "❔ FAQ (Часті питання)",
        "off_hours_default": "Дякуємо за повідомлення! Відповімо у робочий час.",
        "message_received": "Повідомлення отримано. Відповімо найближчим часом.",
        "please_wait": "Зачекайте трохи...",
        "error_occurred": "Виникла помилка. Спробуйте пізніше.",
        "rate_limit": "⚠️ Забагато запитів. Зачекайте.",
        "user_banned": "🚫 Вас тимчасово заблоковано за спам.",
    },
}

# Маппинг языковых кодов
LANGUAGE_MAP = {
    "ru": "ru",
    "be": "ru",  # Белорусский -> русский
    "uk": "uk",  # Украинский
    "ua": "uk",
    "en": "en",
    "en-US": "en",
    "en-GB": "en",
}

# Язык по умолчанию
DEFAULT_LANGUAGE = "ru"


def detect_language(language_code: Optional[str]) -> str:
    """
    Определяет язык пользователя.
    
    Args:
        language_code: Код языка из Telegram (например, 'ru', 'en', 'uk')
    
    Returns:
        Код языка для использования в переводах
    """
    if not language_code:
        return DEFAULT_LANGUAGE
    
    # Приводим к нижнему регистру
    lang = language_code.lower().split('-')[0]
    
    # Проверяем маппинг
    if lang in LANGUAGE_MAP:
        return LANGUAGE_MAP[lang]
    
    # Проверяем наличие переводов
    if lang in TRANSLATIONS:
        return lang
    
    return DEFAULT_LANGUAGE


def get_text(key: str, language_code: Optional[str] = None, **kwargs) -> str:
    """
    Получает переведённый текст.
    
    Args:
        key: Ключ перевода
        language_code: Код языка пользователя
        **kwargs: Параметры для форматирования
    
    Returns:
        Переведённый текст
    """
    # Проверяем настройки мультиязычности
    settings = load_json(SETTINGS_FILE, default_data={})
    if not settings.get('multilang_enabled', False):
        # Мультиязычность отключена - используем язык по умолчанию
        lang = DEFAULT_LANGUAGE
    else:
        lang = detect_language(language_code)
    
    # Получаем перевод
    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    text = translations.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    
    # Форматируем если есть параметры
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_supported_languages() -> list[dict]:
    """Возвращает список поддерживаемых языков."""
    return [
        {"code": "ru", "name": "🇷🇺 Русский", "native": "Русский"},
        {"code": "en", "name": "🇬🇧 English", "native": "English"},
        {"code": "uk", "name": "🇺🇦 Українська", "native": "Українська"},
    ]


def add_custom_translation(lang: str, key: str, text: str) -> bool:
    """
    Добавляет кастомный перевод (сохраняется в settings.json).
    """
    settings = load_json(SETTINGS_FILE, default_data={})
    
    if 'custom_translations' not in settings:
        settings['custom_translations'] = {}
    
    if lang not in settings['custom_translations']:
        settings['custom_translations'][lang] = {}
    
    settings['custom_translations'][lang][key] = text
    
    from bot.config import save_json
    save_json(SETTINGS_FILE, settings)
    return True


def get_user_language(user_id: int) -> str:
    """Получает сохранённый язык пользователя."""
    from bot.user_manager import get_user
    user = get_user(user_id)
    if user:
        return detect_language(user.get('language_code'))
    return DEFAULT_LANGUAGE
