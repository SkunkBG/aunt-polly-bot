import os
import json
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

SETTINGS_FILE = 'bot/data/settings.json'
FAQ_FILE = 'bot/data/faq.json'

def load_json(filename: str, default_data=None):
    """
    Загружает данные из JSON файла, обрабатывая ошибки.
    ✨ УЛУЧШЕНО: Создает файл с default_data если файл не существует
    """
    if default_data is None:
        default_data = {}
    
    try:
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Пытаемся прочитать файл
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                logger.warning(f"File {filename} is empty, using default data")
                # Сразу записываем default_data в пустой файл
                save_json(filename, default_data)
                return default_data
            return json.loads(content)
    except FileNotFoundError:
        logger.info(f"File {filename} not found, creating with default data")
        # ✨ Создаем файл с default_data
        save_json(filename, default_data)
        return default_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {filename}: {e}. Using default data")
        return default_data

def save_json(filename: str, data):
    """
    Сохраняет данные в JSON файл с красивым форматированием.
    ✨ УЛУЧШЕНО: Добавлена проверка успешности записи + создание директории
    """
    try:
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Записываем данные
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        logger.debug(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {e}", exc_info=True)
        return False

# --- Загрузка статических переменных ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

# Читаем строки, разделяем по запятой и создаем списки.
default_groq_models = "mixtral-8x7b-32768,gemma-7b-it"
GROQ_MODELS = [
    model.strip() for model in os.getenv("GROQ_MODELS", default_groq_models).split(',') if model.strip()
]

default_gemini_models = "gemini-1.5-flash-latest"
GEMINI_MODELS = [
    model.strip() for model in os.getenv("GEMINI_MODELS", default_gemini_models).split(',') if model.strip()
]

# --- Системный промпт по умолчанию ---
DEFAULT_AI_PROMPT = """Ты — Aunt Polly, русскоязычный ассистент поддержки VPN-сервиса.
Твои задачи:
1.  Отвечай дружелюбно, вежливо и по делу.
2.  Помогай пользователям с общими вопросами: как подключиться, на каких устройствах работает, способы оплаты, решение простых проблем с подключением (например, "попробуйте сменить сервер или протокол").
3.  НИКОГДА не проси личные данные (email, пароль).
4.  Ты НЕ МОЖЕШЬ проверять статус подписки, сбрасывать пароли или управлять аккаунтами. Если пользователь просит об этом, вежливо сообщи, что это может сделать только оператор-человек, и ему скоро ответят.
5.  Если не знаешь ответ, не придумывай. Вежливо скажи, что для решения этого вопроса требуется участие специалиста.
6.  Всегда отвечай на том же языке, на котором задан вопрос пользователя.
"""

# --- ✨ УЛУЧШЕНО: Загрузка динамических настроек с правильными default значениями ---
# Для settings.json создаем default с базовыми настройками
default_settings = {
    "welcome_message": os.getenv("WELCOME_MESSAGE", "Привет!"),
    # Путь до изображения приветствия (может быть заменено админом и попадать в бэкап)
    "welcome_image_path": os.getenv("WELCOME_IMAGE_PATH", "bot/assets/welcome.jpg"),
    "work_hour_start": int(os.getenv("WORK_HOUR_START", 9)),
    "work_hour_end": int(os.getenv("WORK_HOUR_END", 18)),
    "ai_prompt": DEFAULT_AI_PROMPT,
    "ai_enabled": False,
    "active_ai": None,
    # Время ежедневного бэкапа (HH:MM) — можно менять из админ-панели
    "backup_time": os.getenv("BACKUP_TIME", "10:00").strip(),
}

settings_data = load_json(SETTINGS_FILE, default_data=default_settings)
faq_data = load_json(FAQ_FILE, default_data=[])

# Извлекаем настройки с fallback на default значения
WELCOME_MESSAGE = settings_data.get('welcome_message', default_settings['welcome_message'])
WELCOME_IMAGE_PATH = settings_data.get('welcome_image_path', default_settings['welcome_image_path'])
WORK_HOUR_START = int(settings_data.get('work_hour_start', default_settings['work_hour_start']))
WORK_HOUR_END = int(settings_data.get('work_hour_end', default_settings['work_hour_end']))
AI_SYSTEM_PROMPT = settings_data.get('ai_prompt', DEFAULT_AI_PROMPT)

def get_faq_text():
    """Возвращает текст FAQ для отображения"""
    current_faq_data = load_json(FAQ_FILE, default_data=[])
    if not current_faq_data: 
        return "Список часто задаваемых вопросов пока пуст."
    text = "Часто задаваемые вопросы:\n\n"
    for item in current_faq_data:
        text += f"❔ *{item['question']}*\n"
        text += f"_{item['answer']}_\n\n"
    return text.replace('*', '').replace('_', '')

# --- Остальные переменные ---
OFF_HOURS_REPLY = os.getenv("OFF_HOURS_REPLY", "Ответим в рабочее время.")
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# --- Бэкапы ---
# Время ежедневного бэкапа в локальной TZ (формат HH:MM)
BACKUP_TIME = os.getenv("BACKUP_TIME", "10:00").strip()
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH")
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 8000))

# --- Remnawave API ---
REMNAWAVE_API_URL = os.getenv("REMNAWAVE_API_URL", "").strip()
REMNAWAVE_API_TOKEN = os.getenv("REMNAWAVE_API_TOKEN", "").strip()

# --- ✨ НОВОЕ: Webhook Security ---
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "").strip()

# Логируем статус инициализации (только один раз при импорте)
logger.info(f"Configuration loaded: BOT_MODE={BOT_MODE}, AI_ENABLED={settings_data.get('ai_enabled', False)}")
if WEBHOOK_SECRET_TOKEN:
    logger.info("✨ Webhook security token настроен")
else:
    logger.warning("🟠 Webhook security token не настроен — добавьте WEBHOOK_SECRET_TOKEN")
