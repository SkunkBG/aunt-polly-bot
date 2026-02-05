import html

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from bot.keyboards.inline import start_keyboard, admin_start_keyboard
from bot.config import ADMIN_ID, SETTINGS_FILE, load_json

router = Router()
DEFAULT_WELCOME_IMAGE_PATH = "bot/assets/welcome.jpg"

@router.message(CommandStart())
async def handle_start(message: Message):
    """
    Обработчик /start, который показывает разные меню
    для админа и обычного пользователя.
    """
    # Если это админ
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Добро пожаловать в Админ-панель!",
            reply_markup=admin_start_keyboard()
        )
        return

    # Если это обычный пользователь
    # Берём приветствие из settings.json, чтобы изменения/восстановление бэкапа применялись сразу
    settings = load_json(SETTINGS_FILE, default_data={})
    raw_text = settings.get("welcome_message", "Привет!")
    # Поддержка HTML + плейсхолдера {user_name}
    user_name = html.escape(message.from_user.full_name or message.from_user.first_name or "")
    welcome_text = (raw_text or "").replace("{user_name}", user_name)

    image_path = settings.get("welcome_image_path") or DEFAULT_WELCOME_IMAGE_PATH

    try:
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            reply_markup=start_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"Error sending photo: {e}")
        await message.answer(
            text=welcome_text,
            reply_markup=start_keyboard(),
            parse_mode="HTML",
        )
