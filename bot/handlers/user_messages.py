"""
Обработка сообщений от пользователей.
"""
import datetime
import logging
import html
import pytz
from aiogram import Router, F, Bot
from aiogram.enums.chat_action import ChatAction
from aiogram.types import Message

from bot.config import ADMIN_ID, TIMEZONE, OFF_HOURS_REPLY, load_json, SETTINGS_FILE
from bot.keyboards.inline import admin_reply_keyboard
from bot.ai_integration import get_ai_response
from bot.ai_block_manager import is_ai_blocked_for_user
from bot.faq_search import search_faq
from bot.remnawave_integration import remnawave_client
from bot.user_manager import track_user, is_user_blocked
from bot.i18n import get_text, detect_language

logger = logging.getLogger(__name__)
router = Router()


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


def is_working_hours():
    """Проверяет, является ли текущее время рабочим."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    # Режим 24/7 — всегда рабочее время
    if settings.get('work_mode') == '24/7':
        return True
    
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    start = int(settings.get("work_hour_start", 9))
    end = int(settings.get("work_hour_end", 18))
    return start <= now.hour < end and now.weekday() < 5


async def notify_new_user(bot: Bot, message: Message):
    """Отправляет уведомление админу о новом пользователе."""
    settings = load_json(SETTINGS_FILE, default_data={})
    if not settings.get('notify_new_users', True):
        return
    
    user = message.from_user
    lang_code = user.language_code or "—"
    lang_name = {
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English", 
        "uk": "🇺🇦 Українська",
        "be": "🇧🇾 Беларуская",
        "de": "🇩🇪 Deutsch",
        "fr": "🇫🇷 Français",
        "es": "🇪🇸 Español",
        "it": "🇮🇹 Italiano",
        "pt": "🇵🇹 Português",
        "pl": "🇵🇱 Polski",
        "tr": "🇹🇷 Türkçe",
        "zh": "🇨🇳 中文",
        "ja": "🇯🇵 日本語",
        "ko": "🇰🇷 한국어",
    }.get(lang_code.split('-')[0] if lang_code != "—" else "", f"🌐 {lang_code}")
    
    text = (
        f"🆕 <b>Новый пользователь!</b>\n\n"
        f"👤 <b>Имя:</b> {html.escape(user.full_name)}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
    )
    
    if user.username:
        text += f"📱 <b>Username:</b> @{user.username}\n"
    
    text += f"🌍 <b>Язык:</b> {lang_name}\n"
    text += f"📅 <b>Время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending new user notification: {e}")


@router.message(F.chat.type == "private", F.text | F.photo | F.document | F.audio | F.video)
async def handle_user_message(message: Message, bot: Bot):
    logger.debug(f"Received message from user ID {message.from_user.id}")
    
    # Пропускаем сообщения от админа
    if message.from_user.id == ADMIN_ID:
        logger.debug("Message is from admin, ignoring.")
        return
    
    user_id = message.from_user.id
    user_lang = message.from_user.language_code
    
    # Проверяем блокировку пользователя
    if is_user_blocked(user_id):
        logger.info(f"User {user_id} is blocked, ignoring message")
        return
    
    # Отслеживаем пользователя (получаем инфо о новом)
    is_new_user = track_user(
        user_id=user_id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        language_code=user_lang
    )
    
    # Уведомление о новом пользователе
    if is_new_user:
        logger.info(f"New user detected: {user_id}")
        await notify_new_user(bot, message)

    # 1. Уведомление админу
    logger.info(f"Forwarding message from user {user_id} to admin {ADMIN_ID}")

    username = message.from_user.username
    display_name = f"@{username}" if username else message.from_user.full_name
    safe_display = html.escape(display_name)
    safe_full_name = html.escape(message.from_user.full_name)
    user_info_text = f"✨ <b>Новое сообщение</b> от {safe_display} <code>(ID: {user_id})</code>"

    # Remnawave интеграция
    if remnawave_client:
        try:
            logger.info(f"Fetching user info from Remnawave for {user_id}")
            user_data = await remnawave_client.get_user_by_telegram_id(user_id)

            if user_data:
                remnawave_info = remnawave_client.format_user_info(
                    user_data,
                    tg_full_name=safe_full_name,
                    tg_username=html.escape(username) if username else None,
                    tz_name=TIMEZONE,
                )
                user_info_text = f"{user_info_text}\n\n{remnawave_info}"
            else:
                user_info_text = (
                    f"{user_info_text}\n\n🟠 Пользователь не найден в панели Remnawave"
                )
        except Exception as e:
            logger.error(f"Error fetching Remnawave info: {e}", exc_info=True)
            user_info_text = f"{user_info_text}\n\n🟠 Ошибка получения данных Remnawave"
    
    # Собираем сообщение пользователя
    user_message_text = message.text if message.text else (message.caption if message.caption else "")
    user_message_text = html.escape(user_message_text) if user_message_text else ""

    forwarded_line = f"<i>Переслано от {safe_full_name}</i>"
    msg_body = user_message_text if user_message_text else f"<i>({message.content_type} без текста)</i>"

    parts = [user_info_text, forwarded_line, msg_body]
    combined_text = "\n\n".join([p for p in parts if p])

    try:
        reply_kb = admin_reply_keyboard(user_id)

        if message.content_type == "text":
            await bot.send_message(chat_id=ADMIN_ID, text=combined_text, reply_markup=reply_kb)
        else:
            if message.photo:
                await bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=message.photo[-1].file_id,
                    caption=combined_text,
                    reply_markup=reply_kb
                )
            elif message.video:
                await bot.send_video(
                    chat_id=ADMIN_ID,
                    video=message.video.file_id,
                    caption=combined_text,
                    reply_markup=reply_kb
                )
            elif message.document:
                await bot.send_document(
                    chat_id=ADMIN_ID,
                    document=message.document.file_id,
                    caption=combined_text,
                    reply_markup=reply_kb
                )
            elif message.audio:
                await bot.send_audio(
                    chat_id=ADMIN_ID,
                    audio=message.audio.file_id,
                    caption=combined_text,
                    reply_markup=reply_kb
                )
            else:
                await bot.send_message(chat_id=ADMIN_ID, text=combined_text, reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Error sending message to admin: {e}", exc_info=True)

    # 2. Проверка блокировки ИИ (админ уже отвечает)
    if is_ai_blocked_for_user(user_id):
        logger.info(f"AI is blocked for user {user_id} - admin handling")
        return

    # 3. Проверка FAQ
    if message.text:
        logger.info(f"Searching FAQ for: '{message.text[:50]}...'")
        try:
            # Получаем порог поиска из настроек
            settings = load_json(SETTINGS_FILE, default_data={})
            threshold = settings.get('faq_similarity_threshold', 0.4)
            
            faq_result = search_faq(message.text, similarity_threshold=threshold)
            
            if faq_result['found']:
                logger.info(f"Found FAQ match with similarity {faq_result.get('similarity', 0):.2f}")
                await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
                
                answer_text = f"📖 <b>Нашёл ответ в FAQ:</b>\n\n{faq_result['answer']}"
                media = faq_result.get('media')
                
                try:
                    if media and media.get('file_id'):
                        media_type = media.get('type')
                        file_id = media.get('file_id')
                        
                        if media_type == 'photo':
                            await bot.send_photo(chat_id=message.chat.id, photo=file_id, caption=answer_text)
                        elif media_type == 'video':
                            await bot.send_video(chat_id=message.chat.id, video=file_id, caption=answer_text)
                        elif media_type == 'document':
                            await bot.send_document(chat_id=message.chat.id, document=file_id, caption=answer_text)
                        else:
                            await message.answer(answer_text)
                    else:
                        await message.answer(answer_text)
                    
                    logger.info(f"Sent FAQ answer to user {user_id}")
                    return
                except Exception as e:
                    logger.error(f"Error sending FAQ answer with media: {e}")
                    await message.answer(answer_text)
                    return
            else:
                logger.debug("No FAQ match found")
        except Exception as e:
            logger.error(f"Error in FAQ search: {e}", exc_info=True)

    # 4. Проверяем триггеры
    if message.text:
        trigger_response = check_triggers(message.text)
        if trigger_response:
            logger.info(f"Trigger matched for user {user_id}")
            await message.answer(trigger_response, parse_mode="HTML")
            return

    # 5. Логика ИИ
    settings = load_json(SETTINGS_FILE, default_data={})
    ai_enabled = settings.get('ai_enabled', False)
    active_model = settings.get('active_ai')
    logger.info(f"AI check: enabled={ai_enabled}, model='{active_model}'")

    if ai_enabled and active_model and message.text:
        logger.info(f"AI is active. Sending prompt to '{active_model}'...")
        await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)

        try:
            ai_answer = await get_ai_response(message.text, active_model)
            logger.debug(f"AI response: {ai_answer[:100]}")
            await message.answer(ai_answer)
            logger.info(f"Sent AI response to user {user_id}")
            return
        except Exception as e:
            logger.error(f"Error getting AI response: {e}", exc_info=True)
    else:
        if not message.text:
            logger.debug("No text in message, skipping AI")
        elif not ai_enabled:
            logger.info("AI is disabled")
        elif not active_model:
            logger.info("No AI model selected")

    # 6. Автоответчик вне рабочих часов
    if not is_working_hours():
        logger.info(f"Off-hours, sending auto-reply to {user_id}")
        # Используем настраиваемое сообщение
        off_hours_msg = settings.get('off_hours_message', OFF_HOURS_REPLY)
        await message.answer(off_hours_msg)
    else:
        logger.debug("Working hours, no auto-reply")
