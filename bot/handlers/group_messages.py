"""
Обработка сообщений из группы.
"""
import logging
import html
from aiogram import Router, F, Bot
from aiogram.enums.chat_action import ChatAction
from aiogram.types import Message
from aiogram.filters import Command

from bot.config import ADMIN_ID, TIMEZONE, load_json, save_json, SETTINGS_FILE
from bot.keyboards.inline import admin_reply_keyboard
from bot.ai_integration import get_ai_response
from bot.faq_search import search_faq
from bot.remnawave_integration import remnawave_client
from bot.user_manager import track_user

logger = logging.getLogger(__name__)
router = Router()


def is_group_mode() -> bool:
    """Проверяет, включен ли режим группы."""
    settings = load_json(SETTINGS_FILE, default_data={})
    return settings.get('bot_mode') == 'group'


def get_group_id() -> int | None:
    """Возвращает ID привязанной группы."""
    settings = load_json(SETTINGS_FILE, default_data={})
    return settings.get('group_id')


def check_triggers(text: str) -> str | None:
    """Проверяет триггеры и возвращает ответ если найден."""
    if not text:
        return None
    
    settings = load_json(SETTINGS_FILE, default_data={})
    triggers = settings.get('triggers', {})
    
    text_lower = text.lower()
    for keyword, response in triggers.items():
        if keyword.lower() in text_lower:
            logger.info(f"Trigger matched: '{keyword}'")
            return response
    
    return None


@router.message(Command("link"))
async def link_group_command(message: Message):
    """Команда /link для привязки группы."""
    # Только для групп/супергрупп
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    # Только админ может привязать
    if message.from_user.id != ADMIN_ID:
        await message.reply("⚠️ Только администратор бота может привязать группу.")
        return
    
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['group_id'] = message.chat.id
    settings['group_title'] = message.chat.title or "Без названия"
    save_json(SETTINGS_FILE, settings)
    
    await message.reply(
        f"✅ Группа успешно привязана!\n\n"
        f"<b>Название:</b> {html.escape(message.chat.title or 'Без названия')}\n"
        f"<b>ID:</b> <code>{message.chat.id}</code>\n\n"
        f"Теперь включите режим группы в админ-панели бота.",
        parse_mode="HTML"
    )


@router.message(F.chat.type.in_({'group', 'supergroup'}))
async def handle_group_message(message: Message, bot: Bot):
    """Обработка сообщений из группы."""
    # Проверяем режим работы
    if not is_group_mode():
        return
    
    # Проверяем что это наша группа
    group_id = get_group_id()
    if not group_id or message.chat.id != group_id:
        return
    
    # Пропускаем сообщения от бота
    if message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    user_text = message.text or message.caption or ""
    
    # Отслеживаем пользователя
    track_user(
        user_id=user_id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    # Проверяем, обращаются ли к боту
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower() if bot_info.username else ""
    
    is_reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )
    is_mention = f"@{bot_username}" in user_text.lower() if bot_username else False
    
    # Если не обращаются к боту - только проверяем триггеры
    if not is_reply_to_bot and not is_mention:
        # Проверяем триггеры
        trigger_response = check_triggers(user_text)
        if trigger_response:
            await message.reply(trigger_response, parse_mode="HTML")
        return
    
    # Убираем упоминание из текста
    if is_mention and bot_username:
        user_text = user_text.replace(f"@{bot_username}", "").replace(f"@{bot_username.upper()}", "").strip()
    
    # Отправляем уведомление админу
    await notify_admin_about_group_message(message, bot, user_text)
    
    # Показываем что бот печатает
    await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
    
    # 1. Проверяем FAQ
    if user_text:
        settings = load_json(SETTINGS_FILE, default_data={})
        threshold = settings.get('faq_similarity_threshold', 0.4)
        
        faq_result = search_faq(user_text, similarity_threshold=threshold)
        
        if faq_result['found']:
            logger.info(f"FAQ match in group for '{user_text[:30]}...'")
            answer_text = faq_result['answer']
            media = faq_result.get('media')
            
            try:
                if media and media.get('file_id'):
                    media_type = media.get('type')
                    file_id = media.get('file_id')
                    
                    if media_type == 'photo':
                        await message.reply_photo(photo=file_id, caption=answer_text)
                    elif media_type == 'video':
                        await message.reply_video(video=file_id, caption=answer_text)
                    elif media_type == 'document':
                        await message.reply_document(document=file_id, caption=answer_text)
                    else:
                        await message.reply(answer_text)
                else:
                    await message.reply(answer_text)
                return
            except Exception as e:
                logger.error(f"Error sending FAQ with media in group: {e}")
                await message.reply(answer_text)
                return
    
    # 2. Проверяем триггеры
    trigger_response = check_triggers(user_text)
    if trigger_response:
        await message.reply(trigger_response, parse_mode="HTML")
        return
    
    # 3. Пробуем ИИ
    settings = load_json(SETTINGS_FILE, default_data={})
    ai_enabled = settings.get('ai_enabled', False)
    active_model = settings.get('active_ai')
    
    if ai_enabled and active_model and user_text:
        try:
            ai_answer = await get_ai_response(user_text, active_model)
            await message.reply(ai_answer)
            return
        except Exception as e:
            logger.error(f"Error getting AI response in group: {e}")
    
    # 4. Стандартный ответ
    await message.reply(
        "Я получил ваше сообщение. Администратор ответит вам в ближайшее время."
    )


async def notify_admin_about_group_message(message: Message, bot: Bot, user_text: str):
    """Уведомляет админа о сообщении из группы."""
    user_id = message.from_user.id
    username = message.from_user.username
    display_name = f"@{username}" if username else message.from_user.full_name
    safe_display = html.escape(display_name)
    safe_full_name = html.escape(message.from_user.full_name)
    
    user_info_text = (
        f"👥 <b>Сообщение из группы</b>\n"
        f"От: {safe_display} <code>(ID: {user_id})</code>\n"
        f"Группа: {html.escape(message.chat.title or 'Без названия')}"
    )
    
    # Remnawave интеграция
    if remnawave_client:
        try:
            user_data = await remnawave_client.get_user_by_telegram_id(user_id)
            if user_data:
                remnawave_info = remnawave_client.format_user_info(
                    user_data,
                    tg_full_name=safe_full_name,
                    tg_username=html.escape(username) if username else None,
                    tz_name=TIMEZONE,
                )
                user_info_text = f"{user_info_text}\n\n{remnawave_info}"
        except Exception as e:
            logger.error(f"Error fetching Remnawave info: {e}")
    
    # Текст сообщения
    user_message_text = html.escape(user_text) if user_text else f"<i>({message.content_type})</i>"
    
    combined_text = f"{user_info_text}\n\n<b>Сообщение:</b>\n{user_message_text}"
    
    try:
        reply_kb = admin_reply_keyboard(user_id)
        
        if message.content_type == "text":
            await bot.send_message(chat_id=ADMIN_ID, text=combined_text, reply_markup=reply_kb, parse_mode="HTML")
        elif message.photo:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=combined_text,
                reply_markup=reply_kb,
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=message.document.file_id,
                caption=combined_text,
                reply_markup=reply_kb,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=combined_text, reply_markup=reply_kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending group message to admin: {e}")
