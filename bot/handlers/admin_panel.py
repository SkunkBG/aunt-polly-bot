"""
Улучшенная админ-панель с расширенным функционалом.
"""
import logging
import html
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Router, F, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from zoneinfo import ZoneInfo

from bot.fsm.admin_states import AdminStates
from bot.keyboards.inline import (
    admin_start_keyboard,
    back_to_admin_panel,
    back_to_faq_management,
    # Приветствие
    welcome_menu_keyboard,
    # Автоответчик  
    autoresponder_menu_keyboard,
    # FAQ
    faq_management_keyboard,
    dynamic_delete_faq_keyboard,
    dynamic_edit_faq_keyboard,
    faq_edit_options_keyboard,
    skip_media_keyboard,
    skip_edit_media_keyboard,
    # ИИ
    ai_management_keyboard,
    ai_model_selection_keyboard,
    ai_test_keyboard,
    # Бэкапы
    backup_menu_keyboard,
    backup_restore_keyboard,
    # Пользователи
    users_menu_keyboard,
    users_list_keyboard,
    user_info_keyboard,
    # Рассылка
    broadcast_menu_keyboard,
    broadcast_confirm_keyboard,
    broadcast_done_keyboard,
    # Статистика
    dashboard_keyboard,
    # Справка
    help_menu_keyboard,
    help_back_keyboard,
)
from bot import config as bot_config
from bot.config import SETTINGS_FILE, FAQ_FILE, load_json, save_json, DEFAULT_AI_PROMPT
from bot.backup_manager import create_backup_file, list_backups, restore_backup_file, send_backup_to_admin
from bot.user_manager import (
    get_all_users, get_users_stats, get_user, 
    block_user, unblock_user, is_user_blocked,
    get_active_user_ids, add_broadcast_record, get_broadcast_history
)
from bot.ai_integration import get_ai_response

logger = logging.getLogger(__name__)
router = Router()


# ============================================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================================

@router.callback_query(F.data == "admin_back_to_main")
async def back_to_main_admin_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    logger.debug(f"Admin {callback.from_user.id} returned to main admin menu.")
    await state.clear()
    await callback.message.edit_text(
        "🏠 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_start_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# СТАТИСТИКА / ДАШБОРД
# ============================================================================

@router.callback_query(F.data.in_({"admin_dashboard", "admin_dashboard_refresh"}))
async def show_dashboard(callback: types.CallbackQuery, state: FSMContext):
    """Показывает дашборд со статистикой."""
    await state.clear()
    
    # Статистика пользователей
    user_stats = get_users_stats()
    
    # Статистика FAQ
    faq_list = load_json(FAQ_FILE, default_data=[])
    faq_count = len(faq_list)
    
    # Настройки ИИ
    settings = load_json(SETTINGS_FILE, default_data={})
    ai_status = "🟢 Включен" if settings.get('ai_enabled') else "🔴 Выключен"
    ai_model = settings.get('active_ai', 'не выбран').capitalize()
    
    # Время
    tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
    now = datetime.now(tz)
    
    text = (
        f"📊 <b>Статистика бота</b>\n"
        f"<i>{now.strftime('%d.%m.%Y %H:%M')}</i>\n\n"
        f"👥 <b>Пользователи</b>\n"
        f"├ Всего: {user_stats['total']}\n"
        f"├ Заблокировано: {user_stats['blocked']}\n"
        f"└ Сообщений: {user_stats['total_messages']}\n\n"
        f"🗂️ <b>FAQ</b>\n"
        f"└ Вопросов: {faq_count}\n\n"
        f"🧠 <b>ИИ</b>\n"
        f"├ Статус: {ai_status}\n"
        f"└ Модель: {ai_model}\n\n"
        f"⏰ <b>Рабочие часы</b>\n"
        f"└ {settings.get('work_hour_start', 9)}:00 - {settings.get('work_hour_end', 18)}:00"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=dashboard_keyboard(), parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "admin_export_users")
async def export_users_csv(callback: types.CallbackQuery, bot: Bot):
    """Экспорт пользователей в CSV."""
    users = get_all_users()
    
    if not users:
        return await callback.answer("Нет пользователей для экспорта", show_alert=True)
    
    # Создаём CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Имя', 'Username', 'Первое сообщение', 'Последнее сообщение', 'Сообщений', 'Заблокирован'])
    
    for user in users:
        writer.writerow([
            user.get('user_id', ''),
            user.get('name', ''),
            user.get('username', ''),
            user.get('first_seen', '')[:19] if user.get('first_seen') else '',
            user.get('last_seen', '')[:19] if user.get('last_seen') else '',
            user.get('message_count', 0),
            'Да' if user.get('blocked') else 'Нет'
        ])
    
    # Отправляем файл
    csv_bytes = output.getvalue().encode('utf-8-sig')
    tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
    filename = f"users_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}.csv"
    
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=BufferedInputFile(csv_bytes, filename=filename),
        caption=f"📤 Экспорт пользователей\nВсего: {len(users)}"
    )
    await callback.answer("CSV отправлен!")


# ============================================================================
# ПРИВЕТСТВИЕ
# ============================================================================

@router.callback_query(F.data.in_({"admin_welcome_menu", "admin_change_welcome"}))
async def welcome_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    current_msg = settings.get('welcome_message', 'Привет!')[:100]
    
    text = (
        "✨ <b>Приветствие</b>\n\n"
        f"Текущий текст: <i>{html.escape(current_msg)}...</i>\n\n"
        "• Поддерживается <b>HTML</b>\n"
        "• Плейсхолдер: <code>{user_name}</code>"
    )
    await callback.message.edit_text(text, reply_markup=welcome_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_welcome_change_text")
async def change_welcome_message(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} initiated welcome message change.")
    await state.set_state(AdminStates.waiting_for_welcome_message)
    await callback.message.edit_text(
        "📝 <b>Редактирование приветствия</b>\n\n"
        "Введите новый текст приветствия.\n\n"
        "<b>Поддерживаемые HTML-теги:</b>\n"
        "• <code>&lt;b&gt;жирный&lt;/b&gt;</code> → <b>жирный</b>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code> → <i>курсив</i>\n"
        "• <code>&lt;u&gt;подчёркнутый&lt;/u&gt;</code> → <u>подчёркнутый</u>\n"
        "• <code>&lt;code&gt;код&lt;/code&gt;</code> → <code>код</code>\n"
        "• <code>&lt;a href=\"URL\"&gt;ссылка&lt;/a&gt;</code>\n\n"
        "<b>Плейсхолдер:</b>\n"
        "• <code>{user_name}</code> — имя пользователя\n\n"
        "<b>Пример:</b>\n"
        "<code>Привет, &lt;b&gt;{user_name}&lt;/b&gt;! 👋\nДобро пожаловать в наш сервис!</code>",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_welcome_message)
async def process_new_welcome_message(message: types.Message, state: FSMContext, bot: Bot):
    logger.info(f"Admin {message.from_user.id} is setting a new welcome message.")
    settings = load_json(SETTINGS_FILE)
    settings['welcome_message'] = message.text
    save_json(SETTINGS_FILE, settings)
    await state.clear()
    try:
        await bot.delete_message(message.chat.id, message.message_id - 1)
    except TelegramBadRequest:
        pass
    await message.answer("✅ Приветствие обновлено!", reply_markup=admin_start_keyboard())


@router.callback_query(F.data == "admin_welcome_change_image")
async def change_welcome_image(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_welcome_image)
    await callback.message.edit_text(
        "🖼️ Отправьте новое изображение для приветствия (JPG/PNG).\n\n"
        "Можно отправить как фото или как файл.",
        reply_markup=back_to_admin_panel(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_welcome_image, F.photo | F.document)
async def process_welcome_image(message: types.Message, state: FSMContext, bot: Bot):
    try:
        ext = "jpg"
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            doc = message.document
            fname = (doc.file_name or "").lower()
            if not (fname.endswith(".jpg") or fname.endswith(".jpeg") or fname.endswith(".png")):
                await message.answer("⚠️ Поддерживаются только JPG и PNG.")
                return
            ext = "png" if fname.endswith(".png") else "jpg"
            file_id = doc.file_id

        if not file_id:
            await message.answer("⚠️ Не удалось прочитать изображение.")
            return

        target_dir = Path("bot/data")
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"welcome_image.{ext}"

        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=target_path)

        settings = load_json(SETTINGS_FILE, default_data={})
        settings["welcome_image_path"] = str(target_path)
        save_json(SETTINGS_FILE, settings)

        await state.clear()
        await message.answer("✅ Изображение приветствия обновлено!", reply_markup=admin_start_keyboard())
    except Exception as e:
        logger.error("Failed to set welcome image: %s", e, exc_info=True)
        await state.clear()
        await message.answer("⚠️ Не удалось обновить изображение.", reply_markup=admin_start_keyboard())


@router.callback_query(F.data == "admin_welcome_preview")
async def preview_welcome(callback: types.CallbackQuery, bot: Bot):
    """Предпросмотр приветствия."""
    settings = load_json(SETTINGS_FILE, default_data={})
    raw_text = settings.get("welcome_message", "Привет!")
    user_name = html.escape(callback.from_user.full_name or "Тестовый Пользователь")
    welcome_text = (raw_text or "").replace("{user_name}", user_name)
    
    image_path = settings.get("welcome_image_path") or "bot/assets/welcome.jpg"
    
    try:
        from aiogram.types import FSInputFile
        photo = FSInputFile(image_path)
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=photo,
            caption=f"👁️ <b>Предпросмотр приветствия:</b>\n\n{welcome_text}",
            parse_mode="HTML",
        )
    except Exception as e:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=f"👁️ <b>Предпросмотр приветствия:</b>\n\n{welcome_text}\n\n<i>(изображение не найдено)</i>",
            parse_mode="HTML",
        )
    await callback.answer()


# ============================================================================
# АВТООТВЕТЧИК
# ============================================================================

@router.callback_query(F.data == "admin_autoresponder_menu")
async def autoresponder_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню автоответчика."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    
    work_mode = settings.get('work_mode', 'custom')
    off_hours_msg = settings.get('off_hours_message', bot_config.OFF_HOURS_REPLY)[:100]
    work_start = settings.get('work_hour_start', 9)
    work_end = settings.get('work_hour_end', 18)
    
    if work_mode == '24/7':
        mode_info = "🌐 <b>Режим 24/7</b> — автоответчик отключен, бот всегда онлайн"
    else:
        mode_info = f"🕘 <b>Режим по часам</b> — рабочие часы: {work_start:02d}:00 - {work_end:02d}:00"
    
    text = (
        "⏰ <b>Автоответчик</b>\n\n"
        f"{mode_info}\n\n"
        f"<b>Сообщение вне рабочих часов:</b>\n<i>{html.escape(off_hours_msg)}...</i>"
    )
    await callback.message.edit_text(
        text, 
        reply_markup=autoresponder_menu_keyboard(settings), 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_work_mode_info")
async def work_mode_info(callback: types.CallbackQuery):
    """Информация о текущем режиме работы."""
    settings = load_json(SETTINGS_FILE, default_data={})
    work_mode = settings.get('work_mode', 'custom')
    
    if work_mode == '24/7':
        await callback.answer(
            "🌐 Режим 24/7\n\nБот всегда онлайн, автоответчик не используется.",
            show_alert=True
        )
    else:
        start = settings.get('work_hour_start', 9)
        end = settings.get('work_hour_end', 18)
        await callback.answer(
            f"🕘 Режим по часам\n\nРабочие часы: {start:02d}:00 - {end:02d}:00\nВне этого времени отправляется автоответ.",
            show_alert=True
        )


@router.callback_query(F.data == "admin_set_mode_247")
async def set_mode_247(callback: types.CallbackQuery):
    """Установка режима 24/7."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    if settings.get('work_mode') == '24/7':
        return await callback.answer("Режим 24/7 уже активен")
    
    settings['work_mode'] = '24/7'
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer("✅ Включен режим 24/7")
    
    text = (
        "⏰ <b>Автоответчик</b>\n\n"
        "🌐 <b>Режим 24/7</b> — автоответчик отключен, бот всегда онлайн\n\n"
        "<i>Сообщение вне рабочих часов не используется</i>"
    )
    try:
        await callback.message.edit_text(
            text, 
            reply_markup=autoresponder_menu_keyboard(settings), 
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "admin_set_mode_custom")
async def set_mode_custom(callback: types.CallbackQuery):
    """Установка режима по часам."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    if settings.get('work_mode', 'custom') == 'custom':
        return await callback.answer("Режим по часам уже активен")
    
    settings['work_mode'] = 'custom'
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer("✅ Включен режим по часам")
    
    work_start = settings.get('work_hour_start', 9)
    work_end = settings.get('work_hour_end', 18)
    off_hours_msg = settings.get('off_hours_message', bot_config.OFF_HOURS_REPLY)[:100]
    
    text = (
        "⏰ <b>Автоответчик</b>\n\n"
        f"🕘 <b>Режим по часам</b> — рабочие часы: {work_start:02d}:00 - {work_end:02d}:00\n\n"
        f"<b>Сообщение вне рабочих часов:</b>\n<i>{html.escape(off_hours_msg)}...</i>"
    )
    try:
        await callback.message.edit_text(
            text, 
            reply_markup=autoresponder_menu_keyboard(settings), 
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "admin_change_hours")
async def change_work_hours(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} initiated work hours change.")
    await state.set_state(AdminStates.waiting_for_work_hours)
    
    settings = load_json(SETTINGS_FILE, default_data={})
    current = f"{settings.get('work_hour_start', 9)}-{settings.get('work_hour_end', 18)}"
    
    await callback.message.edit_text(
        f"🕘 <b>Часы работы</b>\n\n"
        f"Текущие: <code>{current}</code>\n\n"
        f"Введите новые часы в формате <code>ЧЧ-ЧЧ</code>\n"
        f"Например: <code>9-18</code> или <code>10-22</code>",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_work_hours)
async def process_new_work_hours(message: types.Message, state: FSMContext, bot: Bot):
    try:
        start, end = map(int, message.text.replace(" ", "").split('-'))
        if not (0 <= start <= 23 and 0 <= end <= 23 and start < end):
            raise ValueError("Incorrect hour range.")
        
        settings = load_json(SETTINGS_FILE)
        settings['work_hour_start'] = start
        settings['work_hour_end'] = end
        save_json(SETTINGS_FILE, settings)
        await state.clear()
        
        try:
            await bot.delete_message(message.chat.id, message.message_id - 1)
        except TelegramBadRequest:
            pass
        await message.answer(
            f"✅ Часы работы обновлены: {start}:00 - {end}:00", 
            reply_markup=admin_start_keyboard()
        )
    except (ValueError, IndexError):
        await message.answer(
            "⚠️ Неверный формат. Введите в формате <code>ЧЧ-ЧЧ</code>",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_change_off_hours_msg")
async def change_off_hours_message(callback: types.CallbackQuery, state: FSMContext):
    """Изменение сообщения автоответчика."""
    settings = load_json(SETTINGS_FILE, default_data={})
    current = settings.get('off_hours_message', bot_config.OFF_HOURS_REPLY)
    
    await state.set_state(AdminStates.waiting_for_off_hours_message)
    await callback.message.edit_text(
        f"💬 <b>Сообщение вне рабочих часов</b>\n\n"
        f"Текущее:\n<i>{html.escape(current)}</i>\n\n"
        f"Введите новое сообщение:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_off_hours_message)
async def process_off_hours_message(message: types.Message, state: FSMContext, bot: Bot):
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['off_hours_message'] = message.text
    save_json(SETTINGS_FILE, settings)
    await state.clear()
    
    try:
        await bot.delete_message(message.chat.id, message.message_id - 1)
    except TelegramBadRequest:
        pass
    await message.answer("✅ Сообщение автоответчика обновлено!", reply_markup=admin_start_keyboard())


@router.callback_query(F.data == "admin_autoresponder_preview")
async def preview_autoresponder(callback: types.CallbackQuery, bot: Bot):
    """Предпросмотр автоответчика."""
    settings = load_json(SETTINGS_FILE, default_data={})
    msg = settings.get('off_hours_message', bot_config.OFF_HOURS_REPLY)
    start = settings.get('work_hour_start', 9)
    end = settings.get('work_hour_end', 18)
    
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            f"👁️ <b>Предпросмотр автоответчика</b>\n\n"
            f"Рабочие часы: {start}:00 - {end}:00\n"
            f"Вне рабочих часов пользователь получит:\n\n"
            f"<i>{html.escape(msg)}</i>"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# FAQ
# ============================================================================

@router.callback_query(F.data == "admin_manage_faq")
async def manage_faq(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} entered FAQ management.")
    await state.clear()
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    settings = load_json(SETTINGS_FILE, default_data={})
    threshold = settings.get('faq_similarity_threshold', 0.4)
    
    text = (
        f"🗂️ <b>Управление FAQ</b>\n\n"
        f"Всего вопросов: {len(faq_list)}\n"
        f"Порог поиска: {threshold:.0%}"
    )
    await callback.message.edit_text(text, reply_markup=faq_management_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_view_all_faq")
async def view_all_faq(callback: types.CallbackQuery, bot: Bot):
    """Просмотр всех FAQ."""
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if not faq_list:
        return await callback.answer("FAQ пуст", show_alert=True)
    
    # Формируем текст
    text = "📋 <b>Все вопросы FAQ:</b>\n\n"
    for i, item in enumerate(faq_list, 1):
        q = html.escape(item.get('question', '')[:50])
        a = html.escape(item.get('answer', '')[:100])
        media = "📎" if item.get('media') else ""
        text += f"<b>{i}. {q}...</b> {media}\n<i>{a}...</i>\n\n"
    
    # Если текст слишком длинный, отправляем отдельным сообщением
    if len(text) > 4000:
        text = text[:4000] + "...\n\n<i>(список обрезан)</i>"
    
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=text,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_faq")
async def add_faq_start(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} initiated 'add FAQ'.")
    await state.set_state(AdminStates.waiting_for_faq_question)
    await callback.message.edit_text(
        "➕ <b>Добавление FAQ</b>\n\nВведите вопрос:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_question)
async def add_faq_question(message: types.Message, state: FSMContext):
    logger.debug(f"Admin {message.from_user.id} entered FAQ question.")
    await state.update_data(question=message.text)
    await state.set_state(AdminStates.waiting_for_faq_answer)
    await message.answer("Теперь введите ответ на этот вопрос:")


@router.message(AdminStates.waiting_for_faq_answer, F.text)
async def add_faq_answer(message: types.Message, state: FSMContext):
    logger.debug(f"Admin {message.from_user.id} entered FAQ answer.")
    await state.update_data(answer=message.text)
    await state.set_state(AdminStates.waiting_for_faq_media)
    await message.answer(
        "🖼️ Хотите добавить медиа к этому FAQ?\n"
        "(фото, видео или файл)\n\n"
        "Отправьте медиа или нажмите «Пропустить»",
        reply_markup=skip_media_keyboard()
    )


@router.callback_query(F.data == "skip_faq_media", AdminStates.waiting_for_faq_media)
async def skip_faq_media(callback: types.CallbackQuery, state: FSMContext):
    """Пропуск добавления медиа к FAQ."""
    data = await state.get_data()
    faq_list = load_json(FAQ_FILE, default_data=[])
    faq_list.append({
        "question": data.get('question'),
        "answer": data.get('answer'),
        "media": None
    })
    save_json(FAQ_FILE, faq_list)
    await state.clear()
    logger.info("New FAQ item added without media.")
    await callback.message.edit_text("✅ FAQ добавлен!", reply_markup=faq_management_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_media, F.photo | F.video | F.document)
async def add_faq_media(message: types.Message, state: FSMContext):
    """Добавление медиа к FAQ."""
    data = await state.get_data()
    
    media_info = None
    if message.photo:
        media_info = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        media_info = {"type": "video", "file_id": message.video.file_id}
    elif message.document:
        media_info = {"type": "document", "file_id": message.document.file_id}
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    faq_list.append({
        "question": data.get('question'),
        "answer": data.get('answer'),
        "media": media_info
    })
    save_json(FAQ_FILE, faq_list)
    await state.clear()
    logger.info("New FAQ item added with media.")
    await message.answer("✅ FAQ с медиа добавлен!", reply_markup=faq_management_keyboard())


@router.callback_query(F.data == "admin_delete_faq")
async def delete_faq_list(callback: types.CallbackQuery):
    faq_list = load_json(FAQ_FILE, default_data=[])
    if not faq_list:
        return await callback.answer("FAQ пуст", show_alert=True)
    await callback.message.edit_text(
        "🗑️ <b>Удаление FAQ</b>\n\nВыберите вопрос для удаления:",
        reply_markup=dynamic_delete_faq_keyboard(faq_list),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_faq_"))
async def confirm_delete_faq(callback: types.CallbackQuery):
    index = int(callback.data.split('_')[-1])
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if 0 <= index < len(faq_list):
        removed = faq_list.pop(index)
        save_json(FAQ_FILE, faq_list)
        logger.info(f"FAQ item deleted: {removed['question'][:30]}...")
        await callback.answer(f"Удалено: {removed['question'][:20]}...", show_alert=True)
        
        if faq_list:
            await callback.message.edit_text(
                "🗑️ <b>Удаление FAQ</b>\n\nВыберите вопрос для удаления:",
                reply_markup=dynamic_delete_faq_keyboard(faq_list),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text("FAQ теперь пуст.", reply_markup=faq_management_keyboard())
    else:
        await callback.answer("Этот FAQ уже удалён", show_alert=True)


# --- Редактирование FAQ ---

@router.callback_query(F.data == "admin_edit_faq_list")
async def edit_faq_list(callback: types.CallbackQuery):
    """Список FAQ для редактирования."""
    faq_list = load_json(FAQ_FILE, default_data=[])
    if not faq_list:
        return await callback.answer("FAQ пуст", show_alert=True)
    await callback.message.edit_text(
        "✏️ <b>Редактирование FAQ</b>\n\nВыберите вопрос:",
        reply_markup=dynamic_edit_faq_keyboard(faq_list),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_faq_") & ~F.data.startswith("admin_edit_faq_q_") & ~F.data.startswith("admin_edit_faq_a_") & ~F.data.startswith("admin_edit_faq_m_"))
async def show_faq_edit_options(callback: types.CallbackQuery):
    """Показать опции редактирования FAQ."""
    index = int(callback.data.split('_')[-1])
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if index >= len(faq_list):
        return await callback.answer("FAQ не найден", show_alert=True)
    
    item = faq_list[index]
    q = html.escape(item.get('question', '')[:100])
    a = html.escape(item.get('answer', '')[:200])
    media = "📎 Есть медиа" if item.get('media') else "Без медиа"
    
    text = (
        f"✏️ <b>Редактирование FAQ #{index + 1}</b>\n\n"
        f"<b>Вопрос:</b>\n{q}\n\n"
        f"<b>Ответ:</b>\n{a}\n\n"
        f"<i>{media}</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=faq_edit_options_keyboard(index), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_faq_q_"))
async def edit_faq_question_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования вопроса FAQ."""
    index = int(callback.data.split('_')[-1])
    await state.update_data(edit_faq_index=index)
    await state.set_state(AdminStates.waiting_for_faq_edit_question)
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    current = faq_list[index].get('question', '')
    
    await callback.message.edit_text(
        f"📝 <b>Редактирование вопроса</b>\n\n"
        f"Текущий:\n<i>{html.escape(current)}</i>\n\n"
        f"Введите новый вопрос:",
        reply_markup=back_to_faq_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_edit_question)
async def process_faq_edit_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get('edit_faq_index')
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    if index is not None and index < len(faq_list):
        faq_list[index]['question'] = message.text
        save_json(FAQ_FILE, faq_list)
    
    await state.clear()
    await message.answer("✅ Вопрос обновлён!", reply_markup=faq_management_keyboard())


@router.callback_query(F.data.startswith("admin_edit_faq_a_"))
async def edit_faq_answer_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования ответа FAQ."""
    index = int(callback.data.split('_')[-1])
    await state.update_data(edit_faq_index=index)
    await state.set_state(AdminStates.waiting_for_faq_edit_answer)
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    current = faq_list[index].get('answer', '')[:500]
    
    await callback.message.edit_text(
        f"💬 <b>Редактирование ответа</b>\n\n"
        f"Текущий:\n<i>{html.escape(current)}...</i>\n\n"
        f"Введите новый ответ:",
        reply_markup=back_to_faq_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_edit_answer)
async def process_faq_edit_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get('edit_faq_index')
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    if index is not None and index < len(faq_list):
        faq_list[index]['answer'] = message.text
        save_json(FAQ_FILE, faq_list)
    
    await state.clear()
    await message.answer("✅ Ответ обновлён!", reply_markup=faq_management_keyboard())


@router.callback_query(F.data.startswith("admin_edit_faq_m_"))
async def edit_faq_media_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования медиа FAQ."""
    index = int(callback.data.split('_')[-1])
    await state.update_data(edit_faq_index=index)
    await state.set_state(AdminStates.waiting_for_faq_edit_media)
    
    await callback.message.edit_text(
        "🖼️ <b>Редактирование медиа</b>\n\n"
        "Отправьте новое медиа (фото/видео/файл)\n"
        "или нажмите «Оставить текущее»",
        reply_markup=skip_edit_media_keyboard(index),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_edit_media, F.photo | F.video | F.document)
async def process_faq_edit_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get('edit_faq_index')
    
    media_info = None
    if message.photo:
        media_info = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        media_info = {"type": "video", "file_id": message.video.file_id}
    elif message.document:
        media_info = {"type": "document", "file_id": message.document.file_id}
    
    faq_list = load_json(FAQ_FILE, default_data=[])
    if index is not None and index < len(faq_list):
        faq_list[index]['media'] = media_info
        save_json(FAQ_FILE, faq_list)
    
    await state.clear()
    await message.answer("✅ Медиа обновлено!", reply_markup=faq_management_keyboard())


@router.callback_query(F.data.startswith("admin_skip_edit_media_"))
async def skip_edit_media(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Медиа оставлено без изменений.", reply_markup=faq_management_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove_faq_media_"))
async def remove_faq_media(callback: types.CallbackQuery):
    """Удаление медиа из FAQ."""
    index = int(callback.data.split('_')[-1])
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if index < len(faq_list):
        faq_list[index]['media'] = None
        save_json(FAQ_FILE, faq_list)
        await callback.answer("Медиа удалено", show_alert=True)
        await callback.message.edit_text("✅ Медиа удалено из FAQ.", reply_markup=faq_management_keyboard())
    else:
        await callback.answer("FAQ не найден", show_alert=True)


# --- Порог поиска FAQ ---

@router.callback_query(F.data == "admin_faq_threshold")
async def faq_threshold_menu(callback: types.CallbackQuery, state: FSMContext):
    """Настройка порога поиска FAQ."""
    settings = load_json(SETTINGS_FILE, default_data={})
    current = settings.get('faq_similarity_threshold', 0.4)
    
    await state.set_state(AdminStates.waiting_for_faq_threshold)
    await callback.message.edit_text(
        f"🔍 <b>Порог поиска FAQ</b>\n\n"
        f"Текущий: <code>{current:.0%}</code>\n\n"
        f"Чем выше порог — тем точнее должно быть совпадение.\n"
        f"Рекомендуемое значение: 30-50%\n\n"
        f"Введите новое значение (число от 10 до 90):",
        reply_markup=back_to_faq_management(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_faq_threshold)
async def process_faq_threshold(message: types.Message, state: FSMContext):
    try:
        value = int(message.text.replace('%', '').strip())
        if not (10 <= value <= 90):
            raise ValueError
        
        threshold = value / 100
        settings = load_json(SETTINGS_FILE, default_data={})
        settings['faq_similarity_threshold'] = threshold
        save_json(SETTINGS_FILE, settings)
        
        await state.clear()
        await message.answer(f"✅ Порог поиска установлен: {value}%", reply_markup=faq_management_keyboard())
    except (ValueError, TypeError):
        await message.answer("⚠️ Введите число от 10 до 90", reply_markup=back_to_faq_management())


# ============================================================================
# ИИ
# ============================================================================

@router.callback_query(F.data == "admin_manage_ai")
async def manage_ai(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} entered AI management.")
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    
    ai_enabled = settings.get('ai_enabled', False)
    active_ai = settings.get('active_ai', 'не выбран')
    
    status = "🟢 Включен" if ai_enabled else "🔴 Выключен"
    
    text = (
        f"🧠 <b>Управление ИИ</b>\n\n"
        f"Статус: {status}\n"
        f"Сервис: {active_ai.capitalize() if active_ai else 'Не выбран'}"
    )
    
    await callback.message.edit_text(text, reply_markup=ai_management_keyboard(settings), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_toggle_ai")
async def toggle_ai(callback: types.CallbackQuery):
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['ai_enabled'] = not settings.get('ai_enabled', False)
    save_json(SETTINGS_FILE, settings)
    
    status = 'включен ✅' if settings['ai_enabled'] else 'выключен ❌'
    logger.info(f"Admin {callback.from_user.id} toggled AI: {status}")
    await callback.answer(f"ИИ {status}")
    
    try:
        text = (
            f"🧠 <b>Управление ИИ</b>\n\n"
            f"Статус: {'🟢 Включен' if settings['ai_enabled'] else '🔴 Выключен'}\n"
            f"Сервис: {(settings.get('active_ai') or 'не выбран').capitalize()}"
        )
        await callback.message.edit_text(text, reply_markup=ai_management_keyboard(settings), parse_mode="HTML")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("admin_select_"))
async def select_ai_service(callback: types.CallbackQuery):
    """Выбор сервиса ИИ (Gemini/Groq)."""
    service = callback.data.split('_')[-1]
    
    if service not in ('gemini', 'groq'):
        return await callback.answer("Неизвестный сервис", show_alert=True)
    
    settings = load_json(SETTINGS_FILE, default_data={})
    if settings.get('active_ai') == service:
        return await callback.answer(f"{service.capitalize()} уже выбран")
    
    settings['active_ai'] = service
    save_json(SETTINGS_FILE, settings)
    logger.info(f"Admin {callback.from_user.id} selected AI service: {service}")
    
    await callback.answer(f"Выбран {service.capitalize()}")
    try:
        text = (
            f"🧠 <b>Управление ИИ</b>\n\n"
            f"Статус: {'🟢 Включен' if settings.get('ai_enabled') else '🔴 Выключен'}\n"
            f"Сервис: {service.capitalize()}"
        )
        await callback.message.edit_text(text, reply_markup=ai_management_keyboard(settings), parse_mode="HTML")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "admin_select_ai_model")
async def select_ai_model_menu(callback: types.CallbackQuery):
    """Меню выбора конкретной модели."""
    settings = load_json(SETTINGS_FILE, default_data={})
    active_service = settings.get('active_ai')
    
    if not active_service:
        return await callback.answer("Сначала выберите сервис (Gemini/Groq)", show_alert=True)
    
    if active_service == 'gemini':
        models = bot_config.GEMINI_MODELS
        current = settings.get('gemini_model')
    else:
        models = bot_config.GROQ_MODELS
        current = settings.get('groq_model')
    
    if not models:
        return await callback.answer(f"Модели {active_service} не настроены в .env", show_alert=True)
    
    await callback.message.edit_text(
        f"🔬 <b>Выбор модели {active_service.capitalize()}</b>\n\n"
        f"Текущая: {current or 'по умолчанию'}\n"
        f"Доступные модели:",
        reply_markup=ai_model_selection_keyboard(active_service, models, current),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_model_"))
async def set_ai_model(callback: types.CallbackQuery):
    """Установка конкретной модели."""
    parts = callback.data.split('_')
    service = parts[3]  # gemini or groq
    model = '_'.join(parts[4:])  # model name (might contain underscores)
    
    settings = load_json(SETTINGS_FILE, default_data={})
    settings[f'{service}_model'] = model
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer(f"Модель установлена: {model}")
    
    # Обновляем меню
    if service == 'gemini':
        models = bot_config.GEMINI_MODELS
    else:
        models = bot_config.GROQ_MODELS
    
    await callback.message.edit_text(
        f"🔬 <b>Выбор модели {service.capitalize()}</b>\n\n"
        f"Текущая: {model}\n"
        f"Доступные модели:",
        reply_markup=ai_model_selection_keyboard(service, models, model),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_change_prompt")
async def change_ai_prompt_start(callback: types.CallbackQuery, state: FSMContext):
    logger.debug(f"Admin {callback.from_user.id} initiated AI prompt change.")
    settings = load_json(SETTINGS_FILE, default_data={})
    current_prompt = settings.get('ai_prompt', DEFAULT_AI_PROMPT)[:500]
    
    await state.set_state(AdminStates.waiting_for_ai_prompt)
    await callback.message.edit_text(
        f"🪄 <b>Системный промпт ИИ</b>\n\n"
        f"Текущий:\n<code>{html.escape(current_prompt)}...</code>\n\n"
        f"Отправьте новый текст промпта:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_ai_prompt)
async def process_new_ai_prompt(message: types.Message, state: FSMContext, bot: Bot):
    logger.info(f"Admin {message.from_user.id} setting new AI prompt.")
    settings = load_json(SETTINGS_FILE)
    settings['ai_prompt'] = message.text
    save_json(SETTINGS_FILE, settings)
    await state.clear()
    
    try:
        await bot.delete_message(message.chat.id, message.message_id - 1)
    except TelegramBadRequest:
        pass
    await message.answer("✅ Промпт для ИИ обновлён!", reply_markup=admin_start_keyboard())


@router.callback_query(F.data == "admin_test_ai")
async def test_ai_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало тестирования ИИ."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    if not settings.get('ai_enabled'):
        return await callback.answer("ИИ выключен. Включите для теста.", show_alert=True)
    
    if not settings.get('active_ai'):
        return await callback.answer("Не выбран сервис ИИ", show_alert=True)
    
    await state.set_state(AdminStates.waiting_for_ai_test_message)
    await callback.message.edit_text(
        "🧪 <b>Тестирование ИИ</b>\n\n"
        "Введите тестовое сообщение, и я покажу ответ ИИ:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_ai_test_message)
async def process_ai_test(message: types.Message, state: FSMContext, bot: Bot):
    """Тестирование ИИ."""
    from aiogram.enums.chat_action import ChatAction
    
    settings = load_json(SETTINGS_FILE, default_data={})
    active_model = settings.get('active_ai')
    
    await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
    
    try:
        response = await get_ai_response(message.text, active_model)
        
        test_result = (
            f"🧪 <b>Тест ИИ</b>\n\n"
            f"<b>Вопрос:</b>\n{html.escape(message.text[:200])}\n\n"
            f"<b>Ответ ({active_model}):</b>\n{html.escape(response[:1500])}"
        )
        
        if len(response) > 1500:
            test_result += "...\n<i>(ответ обрезан)</i>"
        
        await state.clear()
        await message.answer(test_result, reply_markup=ai_test_keyboard(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"AI test failed: {e}")
        await state.clear()
        await message.answer(
            f"⚠️ Ошибка тестирования:\n<code>{html.escape(str(e)[:200])}</code>",
            reply_markup=ai_test_keyboard(),
            parse_mode="HTML"
        )


# ============================================================================
# БЭКАПЫ
# ============================================================================

@router.callback_query(F.data == "admin_manage_backups")
async def backups_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    bt = (settings.get("backup_time") or getattr(bot_config, "BACKUP_TIME", "10:00")).strip()
    
    backups = list_backups(limit=3)
    backups_info = f"Сохранено бэкапов: {len(backups)}" if backups else "Бэкапов пока нет"
    
    await callback.message.edit_text(
        f"🗄️ <b>Бэкапы</b>\n\n"
        f"• Хранится: <b>3 последних</b> бэкапа\n"
        f"• Ежедневный бэкап: <b>{bt}</b>\n"
        f"• {backups_info}\n\n"
        f"Выберите действие:",
        reply_markup=backup_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_backup_send_last")
async def admin_send_last_backup(callback: types.CallbackQuery, bot: Bot):
    try:
        backups = list_backups(limit=1)
        backup_path = backups[0].path if backups else create_backup_file()

        tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
        local_time = datetime.now(tz).strftime("%d.%m.%Y %H:%M")
        
        await send_backup_to_admin(
            bot, backup_path,
            caption=f"🗄️ Последний бэкап • {local_time}"
        )
        await callback.message.edit_text("📤 Бэкап отправлен!", reply_markup=backup_menu_keyboard())
    except Exception as e:
        logger.error("Send backup failed: %s", e, exc_info=True)
        await callback.message.edit_text("⚠️ Не удалось отправить бэкап", reply_markup=backup_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_backup_set_time")
async def admin_backup_set_time_start(callback: types.CallbackQuery, state: FSMContext):
    settings = load_json(SETTINGS_FILE, default_data={})
    current = (settings.get("backup_time") or "10:00").strip()
    
    await state.set_state(AdminStates.waiting_for_backup_time)
    await callback.message.edit_text(
        f"⏰ <b>Время ежедневного бэкапа</b>\n\n"
        f"Текущее: <b>{current}</b>\n\n"
        f"Введите новое время в формате <code>HH:MM</code>:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_backup_time)
async def admin_backup_set_time_process(message: types.Message, state: FSMContext):
    value = (message.text or "").strip()
    try:
        hh, mm = value.split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError

        settings = load_json(SETTINGS_FILE, default_data={})
        settings["backup_time"] = f"{h:02d}:{m:02d}"
        save_json(SETTINGS_FILE, settings)
        await state.clear()
        await message.answer(
            f"✅ Время бэкапа: {h:02d}:{m:02d}",
            reply_markup=backup_menu_keyboard(),
        )
    except Exception:
        await message.answer(
            "⚠️ Неверный формат. Введите <code>HH:MM</code>",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin_backup_create")
async def admin_create_backup(callback: types.CallbackQuery, bot: Bot):
    try:
        backup_path = create_backup_file()
        tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
        local_time = datetime.now(tz).strftime("%d.%m.%Y %H:%M")
        
        await send_backup_to_admin(
            bot, backup_path,
            caption=f"🗄️ Ручной бэкап • {local_time}"
        )
        await callback.message.edit_text("✅ Бэкап создан и отправлен!", reply_markup=backup_menu_keyboard())
    except Exception as e:
        logger.error("Backup create failed: %s", e, exc_info=True)
        await callback.message.edit_text("⚠️ Ошибка создания бэкапа", reply_markup=backup_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_backup_restore_menu")
async def admin_restore_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    backups = list_backups(limit=5)
    
    if backups:
        tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
        titles = [b.created_at.astimezone(tz).strftime("%d.%m.%Y %H:%M") for b in backups]
        text = "♻️ <b>Восстановление</b>\n\nВыберите бэкап:"
    else:
        titles = []
        text = "♻️ <b>Восстановление</b>\n\nБэкапов нет. Загрузите файл."
    
    await callback.message.edit_text(text, reply_markup=backup_restore_keyboard(titles), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_restore_backup_"))
async def admin_restore_from_local(callback: types.CallbackQuery):
    try:
        idx = int(callback.data.split("_")[-1])
    except Exception:
        return await callback.answer("Ошибка", show_alert=True)

    backups = list_backups(limit=5)
    if idx < 0 or idx >= len(backups):
        return await callback.answer("Бэкап не найден", show_alert=True)

    try:
        report = restore_backup_file(backups[idx].path)
        await callback.message.edit_text(
            f"✅ {report}\n\n<i>Перезапустите бота для применения всех изменений.</i>",
            reply_markup=backup_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Restore failed: %s", e, exc_info=True)
        await callback.message.edit_text("⚠️ Ошибка восстановления", reply_markup=backup_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_backup_restore_upload")
async def admin_restore_upload_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_backup_upload)
    await callback.message.edit_text(
        "⬆️ <b>Загрузка бэкапа</b>\n\nОтправьте ZIP-файл бэкапа:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_backup_upload, F.document)
async def admin_restore_upload_process(message: types.Message, state: FSMContext, bot: Bot):
    try:
        doc = message.document
        if not doc or not (doc.file_name or "").lower().endswith(".zip"):
            await message.answer("⚠️ Отправьте ZIP-файл")
            return

        uploads_dir = Path("bot/backups/_uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = uploads_dir / f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"

        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=tmp_path)

        report = restore_backup_file(tmp_path)
        await state.clear()
        await message.answer(
            f"✅ {report}\n\n<i>Перезапустите бота для применения.</i>",
            reply_markup=admin_start_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Upload restore failed: %s", e, exc_info=True)
        await state.clear()
        await message.answer("⚠️ Ошибка восстановления из файла", reply_markup=admin_start_keyboard())


# ============================================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================================

@router.callback_query(F.data == "admin_users_menu")
async def users_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню управления пользователями."""
    await state.clear()
    stats = get_users_stats()
    
    text = (
        f"👥 <b>Пользователи</b>\n\n"
        f"Всего: {stats['total']}\n"
        f"Заблокировано: {stats['blocked']}\n"
        f"Сообщений: {stats['total_messages']}"
    )
    
    await callback.message.edit_text(text, reply_markup=users_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users_list")
async def users_list(callback: types.CallbackQuery):
    """Список пользователей."""
    users = get_all_users()
    
    if not users:
        return await callback.answer("Пользователей пока нет", show_alert=True)
    
    await callback.message.edit_text(
        f"📋 <b>Список пользователей</b> ({len(users)})\n\n"
        f"🚫 = заблокирован",
        reply_markup=users_list_keyboard(users, page=0),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users_page_"))
async def users_list_page(callback: types.CallbackQuery):
    """Пагинация списка пользователей."""
    page = int(callback.data.split('_')[-1])
    users = get_all_users()
    
    await callback.message.edit_text(
        f"📋 <b>Список пользователей</b> ({len(users)})\n\n"
        f"🚫 = заблокирован",
        reply_markup=users_list_keyboard(users, page=page),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_info_"))
async def user_info(callback: types.CallbackQuery):
    """Информация о пользователе."""
    user_id = int(callback.data.split('_')[-1])
    user = get_user(user_id)
    
    if not user:
        return await callback.answer("Пользователь не найден", show_alert=True)
    
    name = html.escape(user.get('name', 'Unknown'))
    username = user.get('username', '')
    first_seen = user.get('first_seen', '')[:10]
    last_seen = user.get('last_seen', '')[:10]
    msg_count = user.get('message_count', 0)
    blocked = user.get('blocked', False)
    
    status = "🚫 Заблокирован" if blocked else "✅ Активен"
    
    text = (
        f"👤 <b>Пользователь</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Имя: {name}\n"
        f"Username: @{username if username else '—'}\n"
        f"Первое сообщение: {first_seen}\n"
        f"Последняя активность: {last_seen}\n"
        f"Сообщений: {msg_count}\n"
        f"Статус: {status}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=user_info_keyboard(user_id, blocked),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_toggle_block_"))
async def toggle_user_block(callback: types.CallbackQuery):
    """Блокировка/разблокировка пользователя."""
    user_id = int(callback.data.split('_')[-1])
    
    if is_user_blocked(user_id):
        unblock_user(user_id)
        await callback.answer("✅ Пользователь разблокирован")
    else:
        block_user(user_id)
        await callback.answer("🚫 Пользователь заблокирован")
    
    # Обновляем информацию
    user = get_user(user_id)
    if user:
        name = html.escape(user.get('name', 'Unknown'))
        blocked = user.get('blocked', False)
        status = "🚫 Заблокирован" if blocked else "✅ Активен"
        
        text = (
            f"👤 <b>Пользователь</b>\n\n"
            f"ID: <code>{user_id}</code>\n"
            f"Имя: {name}\n"
            f"Username: @{user.get('username') or '—'}\n"
            f"Статус: {status}"
        )
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=user_info_keyboard(user_id, blocked),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data == "admin_users_block")
async def users_block_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало блокировки пользователя по ID."""
    await state.set_state(AdminStates.waiting_for_user_id_to_block)
    await callback.message.edit_text(
        "🚫 <b>Блокировка пользователя</b>\n\n"
        "Введите ID пользователя для блокировки:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id_to_block)
async def process_user_block(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        block_user(user_id)
        await state.clear()
        await message.answer(f"🚫 Пользователь {user_id} заблокирован", reply_markup=users_menu_keyboard())
    except ValueError:
        await message.answer("⚠️ Введите числовой ID пользователя", reply_markup=back_to_admin_panel())


@router.callback_query(F.data == "admin_users_unblock")
async def users_unblock_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало разблокировки пользователя."""
    await state.set_state(AdminStates.waiting_for_user_id_to_unblock)
    await callback.message.edit_text(
        "✅ <b>Разблокировка пользователя</b>\n\n"
        "Введите ID пользователя для разблокировки:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id_to_unblock)
async def process_user_unblock(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if unblock_user(user_id):
            await state.clear()
            await message.answer(f"✅ Пользователь {user_id} разблокирован", reply_markup=users_menu_keyboard())
        else:
            await message.answer("⚠️ Пользователь не найден", reply_markup=users_menu_keyboard())
            await state.clear()
    except ValueError:
        await message.answer("⚠️ Введите числовой ID", reply_markup=back_to_admin_panel())


@router.callback_query(F.data == "admin_users_search")
async def users_search_start(callback: types.CallbackQuery, state: FSMContext):
    """Поиск пользователя."""
    await state.set_state(AdminStates.waiting_for_user_search)
    await callback.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите ID, имя или username:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    users = get_all_users()
    
    # Ищем по ID, имени или username
    results = []
    for user in users:
        uid = str(user.get('user_id', ''))
        name = (user.get('name') or '').lower()
        username = (user.get('username') or '').lower()
        
        if query in uid or query in name or query in username:
            results.append(user)
    
    await state.clear()
    
    if not results:
        await message.answer("🔍 Ничего не найдено", reply_markup=users_menu_keyboard())
    elif len(results) == 1:
        # Показываем сразу информацию
        user = results[0]
        user_id = user.get('user_id')
        name = html.escape(user.get('name', 'Unknown'))
        blocked = user.get('blocked', False)
        status = "🚫 Заблокирован" if blocked else "✅ Активен"
        
        text = (
            f"👤 <b>Найден пользователь</b>\n\n"
            f"ID: <code>{user_id}</code>\n"
            f"Имя: {name}\n"
            f"Username: @{user.get('username') or '—'}\n"
            f"Сообщений: {user.get('message_count', 0)}\n"
            f"Статус: {status}"
        )
        await message.answer(text, reply_markup=user_info_keyboard(user_id, blocked), parse_mode="HTML")
    else:
        # Показываем список
        await message.answer(
            f"🔍 <b>Найдено: {len(results)}</b>",
            reply_markup=users_list_keyboard(results, page=0),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_users_stats")
async def users_stats(callback: types.CallbackQuery):
    """Статистика пользователей."""
    stats = get_users_stats()
    users = get_all_users()
    
    # Считаем активных за последние 7 дней
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_week = 0
    for user in users:
        try:
            last_seen = datetime.fromisoformat(user.get('last_seen', '').replace('Z', '+00:00'))
            if last_seen > week_ago:
                active_week += 1
        except Exception:
            pass
    
    text = (
        f"📊 <b>Статистика пользователей</b>\n\n"
        f"👥 Всего: {stats['total']}\n"
        f"🚫 Заблокировано: {stats['blocked']}\n"
        f"📅 Активных за неделю: {active_week}\n"
        f"💬 Всего сообщений: {stats['total_messages']}"
    )
    
    await callback.message.edit_text(text, reply_markup=users_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


# ============================================================================
# РАССЫЛКА
# ============================================================================

@router.callback_query(F.data == "admin_broadcast_menu")
async def broadcast_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню рассылки."""
    await state.clear()
    
    active_users = len(get_active_user_ids())
    history = get_broadcast_history(limit=3)
    
    history_text = ""
    if history:
        history_text = "\n\n<b>Последние рассылки:</b>\n"
        for h in history[:3]:
            ts = h.get('timestamp', '')[:10]
            sent = h.get('sent', 0)
            preview = h.get('message_preview', '')[:30]
            history_text += f"• {ts}: {sent} получателей\n  <i>{html.escape(preview)}...</i>\n"
    
    text = (
        f"📢 <b>Рассылка</b>\n\n"
        f"Активных пользователей: {active_users}"
        f"{history_text}"
    )
    
    await callback.message.edit_text(text, reply_markup=broadcast_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_new")
async def broadcast_new(callback: types.CallbackQuery, state: FSMContext):
    """Начало новой рассылки."""
    active_count = len(get_active_user_ids())
    
    if active_count == 0:
        return await callback.answer("Нет активных пользователей для рассылки", show_alert=True)
    
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.message.edit_text(
        f"📨 <b>Новая рассылка</b>\n\n"
        f"Получателей: {active_count}\n\n"
        f"Введите текст сообщения для рассылки:\n"
        f"<i>(поддерживается HTML-форматирование)</i>",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    """Обработка текста рассылки."""
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)
    
    active_count = len(get_active_user_ids())
    preview = html.escape(message.text[:200])
    
    await message.answer(
        f"📨 <b>Подтверждение рассылки</b>\n\n"
        f"<b>Текст:</b>\n{preview}{'...' if len(message.text) > 200 else ''}\n\n"
        f"<b>Получателей:</b> {active_count}\n\n"
        f"Отправить?",
        reply_markup=broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_broadcast_confirm", AdminStates.waiting_for_broadcast_confirm)
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка рассылки."""
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    
    if not text:
        await state.clear()
        return await callback.answer("Текст рассылки пуст", show_alert=True)
    
    await callback.message.edit_text("⏳ <b>Рассылка...</b>", parse_mode="HTML")
    
    user_ids = get_active_user_ids()
    sent = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML"
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast to {user_id} failed: {e}")
            failed += 1
        
        # Небольшая задержка чтобы не превысить лимиты
        import asyncio
        await asyncio.sleep(0.05)
    
    # Сохраняем историю
    add_broadcast_record(text, sent, failed)
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📬 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=broadcast_done_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_cancel")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена", reply_markup=broadcast_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_history")
async def broadcast_history(callback: types.CallbackQuery):
    """История рассылок."""
    history = get_broadcast_history(limit=10)
    
    if not history:
        return await callback.answer("История рассылок пуста", show_alert=True)
    
    text = "📜 <b>История рассылок</b>\n\n"
    for h in history:
        ts = h.get('timestamp', '')[:16].replace('T', ' ')
        sent = h.get('sent', 0)
        failed = h.get('failed', 0)
        preview = html.escape(h.get('message_preview', '')[:50])
        text += f"<b>{ts}</b>\n✓{sent} ✗{failed}\n<i>{preview}...</i>\n\n"
    
    await callback.message.edit_text(text, reply_markup=broadcast_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


# ============================================================================
# СПРАВКА
# ============================================================================

@router.callback_query(F.data == "admin_help_menu")
async def help_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню справки."""
    await state.clear()
    text = (
        "❓ <b>Справка по админ-панели</b>\n\n"
        "Выберите раздел, чтобы узнать подробности:"
    )
    await callback.message.edit_text(text, reply_markup=help_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_dashboard")
async def help_dashboard(callback: types.CallbackQuery):
    """Справка по статистике."""
    text = (
        "📊 <b>Статистика</b>\n\n"
        "Раздел показывает общую информацию о работе бота:\n\n"
        "• <b>Пользователи</b> — сколько людей писало боту\n"
        "• <b>Заблокировано</b> — количество заблокированных\n"
        "• <b>Сообщений</b> — общее количество сообщений\n"
        "• <b>FAQ</b> — количество вопросов в базе\n"
        "• <b>Статус ИИ</b> — включен ли ИИ и какая модель\n\n"
        "📤 <b>Экспорт в CSV</b> — скачивание списка пользователей в виде таблицы"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_welcome")
async def help_welcome(callback: types.CallbackQuery):
    """Справка по приветствию."""
    text = (
        "✨ <b>Приветствие</b>\n\n"
        "Настройка сообщения, которое получают новые пользователи при команде /start\n\n"
        "• <b>Текст</b> — поддерживает HTML-разметку\n"
        "• <b>Изображение</b> — картинка, отправляемая вместе с текстом\n"
        "• <b>Плейсхолдер</b> <code>{user_name}</code> — автоматически заменяется на имя пользователя\n\n"
        "<b>Пример текста:</b>\n"
        "<code>Привет, &lt;b&gt;{user_name}&lt;/b&gt;! 👋</code>\n\n"
        "Результат: Привет, <b>Иван</b>! 👋"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_autoresponder")
async def help_autoresponder(callback: types.CallbackQuery):
    """Справка по автоответчику."""
    text = (
        "⏰ <b>Автоответчик</b>\n\n"
        "Управление режимом работы бота:\n\n"
        "<b>Режим 24/7</b>\n"
        "Бот всегда онлайн, автоответчик не используется. "
        "Все сообщения обрабатываются без ограничений по времени.\n\n"
        "<b>Режим по часам</b>\n"
        "Устанавливаются рабочие часы (например, 09:00-18:00). "
        "Вне этих часов пользователям отправляется автоматический ответ.\n\n"
        "• <b>Часы работы</b> — формат ЧЧ-ЧЧ (например, 9-18)\n"
        "• <b>Сообщение</b> — текст, который получит пользователь вне рабочих часов"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_faq")
async def help_faq(callback: types.CallbackQuery):
    """Справка по FAQ."""
    text = (
        "🗂️ <b>FAQ</b>\n\n"
        "База часто задаваемых вопросов. Бот автоматически ищет подходящий ответ.\n\n"
        "• <b>Просмотр</b> — список всех вопросов и ответов\n"
        "• <b>Добавить</b> — создание нового FAQ (вопрос + ответ + медиа)\n"
        "• <b>Изменить</b> — редактирование существующих FAQ\n"
        "• <b>Удалить</b> — удаление FAQ из базы\n\n"
        "<b>Порог поиска</b>\n"
        "Определяет, насколько точно вопрос пользователя должен совпадать с FAQ.\n"
        "• <b>Низкий порог (10-30%)</b> — бот отвечает на похожие вопросы\n"
        "• <b>Высокий порог (50-90%)</b> — нужно точное совпадение\n"
        "• <b>Рекомендуется: 30-50%</b>"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_ai")
async def help_ai(callback: types.CallbackQuery):
    """Справка по ИИ."""
    text = (
        "🧠 <b>ИИ</b>\n\n"
        "Интеграция с искусственным интеллектом для автоматических ответов.\n\n"
        "<b>Сервисы:</b>\n"
        "• <b>Gemini</b> — Google AI (рекомендуется)\n"
        "• <b>Groq</b> — быстрый и бесплатный\n\n"
        "<b>Настройки:</b>\n"
        "• <b>Вкл/Выкл</b> — включение или отключение ИИ\n"
        "• <b>Выбор сервиса</b> — Gemini или Groq\n"
        "• <b>Выбор модели</b> — конкретная модель из списка\n"
        "• <b>Системный промпт</b> — инструкции для ИИ\n"
        "• <b>Тест</b> — проверка работы ИИ\n\n"
        "<b>Приоритет ответов:</b>\n"
        "1. FAQ (если найдено совпадение)\n"
        "2. ИИ (если включен)\n"
        "3. Автоответчик (вне рабочих часов)"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_users")
async def help_users(callback: types.CallbackQuery):
    """Справка по пользователям."""
    text = (
        "👥 <b>Пользователи</b>\n\n"
        "Управление пользователями бота:\n\n"
        "• <b>Список</b> — все пользователи с пагинацией\n"
        "• <b>Поиск</b> — по ID, имени или username\n"
        "• <b>Блокировка</b> — заблокированные пользователи не могут писать боту\n"
        "• <b>Статистика</b> — активность за неделю\n\n"
        "<b>Информация о пользователе:</b>\n"
        "• ID — уникальный идентификатор Telegram\n"
        "• Имя и username\n"
        "• Дата первого и последнего сообщения\n"
        "• Количество сообщений\n"
        "• Статус блокировки"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_broadcast")
async def help_broadcast(callback: types.CallbackQuery):
    """Справка по рассылке."""
    text = (
        "📢 <b>Рассылка</b>\n\n"
        "Массовая отправка сообщений всем пользователям.\n\n"
        "<b>Как использовать:</b>\n"
        "1. Нажмите «Новая рассылка»\n"
        "2. Введите текст сообщения\n"
        "3. Проверьте предпросмотр\n"
        "4. Подтвердите отправку\n\n"
        "<b>Важно:</b>\n"
        "• Рассылка отправляется только незаблокированным пользователям\n"
        "• Поддерживается HTML-разметка\n"
        "• Отправка происходит с задержкой, чтобы не превысить лимиты Telegram\n"
        "• История сохраняет последние 20 рассылок"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_backups")
async def help_backups(callback: types.CallbackQuery):
    """Справка по бэкапам."""
    text = (
        "🗄️ <b>Бэкапы</b>\n\n"
        "Резервное копирование настроек и данных.\n\n"
        "<b>Что сохраняется:</b>\n"
        "• Настройки бота (settings.json)\n"
        "• База FAQ (faq.json)\n"
        "• Изображение приветствия\n\n"
        "<b>Функции:</b>\n"
        "• <b>Создать</b> — моментальный бэкап\n"
        "• <b>Отправить</b> — получить последний бэкап в чат\n"
        "• <b>Время</b> — настройка ежедневного автобэкапа\n"
        "• <b>Восстановить</b> — из локального или загруженного файла\n\n"
        "<b>Хранение:</b>\n"
        "Автоматически сохраняются 3 последних бэкапа, старые удаляются."
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_help_html")
async def help_html(callback: types.CallbackQuery):
    """Справка по HTML-разметке."""
    text = (
        "📝 <b>HTML-разметка</b>\n\n"
        "В приветствии и рассылках можно использовать HTML-теги:\n\n"
        "<b>Форматирование текста:</b>\n"
        "• <code>&lt;b&gt;жирный&lt;/b&gt;</code> → <b>жирный</b>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code> → <i>курсив</i>\n"
        "• <code>&lt;u&gt;подчёркнутый&lt;/u&gt;</code> → <u>подчёркнутый</u>\n"
        "• <code>&lt;s&gt;зачёркнутый&lt;/s&gt;</code> → <s>зачёркнутый</s>\n"
        "• <code>&lt;code&gt;моноширинный&lt;/code&gt;</code> → <code>моноширинный</code>\n\n"
        "<b>Ссылки:</b>\n"
        "<code>&lt;a href=\"https://example.com\"&gt;текст&lt;/a&gt;</code>\n"
        "Результат: <a href=\"https://example.com\">текст</a>\n\n"
        "<b>Упоминание пользователя:</b>\n"
        "<code>&lt;a href=\"tg://user?id=123456\"&gt;имя&lt;/a&gt;</code>\n\n"
        "<b>Перенос строки:</b>\n"
        "Просто нажмите Enter или используйте обычный перенос"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# ============================================================================
# REMNAWAVE - НАСТРОЙКА НАЗВАНИЙ СЕРВЕРОВ
# ============================================================================

@router.callback_query(F.data == "admin_remnawave_menu")
async def remnawave_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню настройки Remnawave."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    server_names = settings.get('server_names', {})
    
    if server_names:
        mapping_text = "\n".join([f"• <code>{k}</code> → {v}" for k, v in server_names.items()])
    else:
        mapping_text = "<i>Не настроено (используются сырые названия)</i>"
    
    text = (
        "🌐 <b>Remnawave - Названия серверов</b>\n\n"
        f"<b>Текущий маппинг:</b>\n{mapping_text}\n\n"
        "Здесь можно настроить красивые названия для серверов.\n"
        "Это нужно, если в API приходят технические имена вроде 'norway-squad'."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Настроить названия", callback_data="admin_remnawave_edit")],
        [InlineKeyboardButton(text="🗑️ Сбросить маппинг", callback_data="admin_remnawave_reset")],
        [InlineKeyboardButton(text="📋 Пример маппинга", callback_data="admin_remnawave_example")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_remnawave_edit")
async def remnawave_edit(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование маппинга серверов."""
    await state.set_state(AdminStates.waiting_for_server_mapping)
    
    text = (
        "✏️ <b>Настройка названий серверов</b>\n\n"
        "Введите маппинг в формате:\n"
        "<code>техническое_имя = Красивое название</code>\n\n"
        "Каждый сервер с новой строки. Пример:\n"
        "<code>norway-squad = 🇳🇴 Норвегия\n"
        "sweden-squad = 🇸🇪 Швеция\n"
        "usa-squad = 🇺🇸 США</code>\n\n"
        "💡 Чтобы узнать технические названия, включите LOG_LEVEL=DEBUG в .env "
        "и посмотрите логи при получении сообщения от пользователя."
    )
    
    await callback.message.edit_text(text, reply_markup=back_to_admin_panel(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_for_server_mapping)
async def process_server_mapping(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка нового маппинга серверов."""
    try:
        mapping = {}
        lines = message.text.strip().split('\n')
        
        for line in lines:
            if '=' not in line:
                continue
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    mapping[key] = value
        
        if not mapping:
            await message.answer(
                "⚠️ Не удалось распознать маппинг.\n"
                "Используйте формат: <code>имя = Название</code>",
                reply_markup=back_to_admin_panel(),
                parse_mode="HTML"
            )
            return
        
        settings = load_json(SETTINGS_FILE, default_data={})
        settings['server_names'] = mapping
        save_json(SETTINGS_FILE, settings)
        
        await state.clear()
        
        mapping_text = "\n".join([f"• <code>{k}</code> → {v}" for k, v in mapping.items()])
        await message.answer(
            f"✅ Маппинг серверов сохранён!\n\n{mapping_text}",
            reply_markup=admin_start_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error saving server mapping: {e}")
        await message.answer(
            "❌ Ошибка сохранения",
            reply_markup=back_to_admin_panel()
        )


@router.callback_query(F.data == "admin_remnawave_reset")
async def remnawave_reset(callback: types.CallbackQuery):
    """Сброс маппинга серверов."""
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['server_names'] = {}
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer("✅ Маппинг сброшен", show_alert=True)
    
    # Возвращаемся в меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Настроить названия", callback_data="admin_remnawave_edit")],
        [InlineKeyboardButton(text="📋 Пример маппинга", callback_data="admin_remnawave_example")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(
        "🌐 <b>Remnawave - Названия серверов</b>\n\n"
        "<b>Текущий маппинг:</b>\n<i>Не настроено (используются сырые названия)</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_remnawave_example")
async def remnawave_example(callback: types.CallbackQuery):
    """Пример маппинга серверов."""
    example_mapping = {
        "bridgeru-squad": "🇷🇺 LTE Россия",
        "norway-squad": "🇳🇴 Норвегия",
        "sweden-squad": "🇸🇪 Швеция", 
        "usa-squad": "🇺🇸 США",
        "germany-squad": "🇩🇪 Германия",
        "netherlands-squad": "🇳🇱 Нидерланды",
    }
    
    # Сохраняем пример
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['server_names'] = example_mapping
    save_json(SETTINGS_FILE, settings)
    
    mapping_text = "\n".join([f"• <code>{k}</code> → {v}" for k, v in example_mapping.items()])
    
    await callback.message.edit_text(
        f"✅ Загружен пример маппинга:\n\n{mapping_text}\n\n"
        "Измените названия под ваши серверы.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="admin_remnawave_edit")],
            [InlineKeyboardButton(text="‹ Назад", callback_data="admin_remnawave_menu")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer("Пример загружен!")


# ============================================================================
# РЕЖИМ РАБОТЫ (БОТ / ГРУППА)
# ============================================================================

@router.callback_query(F.data == "admin_work_mode_menu")
async def work_mode_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню выбора режима работы."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    
    current_mode = settings.get('bot_mode', 'private')  # 'private' или 'group'
    group_id = settings.get('group_id', '')
    
    if current_mode == 'group':
        mode_text = "👥 <b>Группа</b>"
        mode_desc = "Бот работает в группе, сообщения пересылаются админу"
        if group_id:
            mode_desc += f"\nID группы: <code>{group_id}</code>"
    else:
        mode_text = "🤖 <b>Личные сообщения</b>"
        mode_desc = "Бот работает в личке, пользователи пишут напрямую боту"
    
    text = (
        f"⚙️ <b>Режим работы бота</b>\n\n"
        f"Текущий режим: {mode_text}\n"
        f"{mode_desc}\n\n"
        f"<b>Описание режимов:</b>\n"
        f"🤖 <b>Личка</b> — пользователи пишут боту напрямую\n"
        f"👥 <b>Группа</b> — бот работает в группе/супергруппе"
    )
    
    # Определяем какую кнопку показать активной
    private_mark = " ✓" if current_mode == 'private' else ""
    group_mark = " ✓" if current_mode == 'group' else ""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🤖 Личка{private_mark}", callback_data="admin_set_mode_private"),
            InlineKeyboardButton(text=f"👥 Группа{group_mark}", callback_data="admin_set_mode_group"),
        ],
        [InlineKeyboardButton(text="🔗 Привязать группу", callback_data="admin_link_group")],
        [InlineKeyboardButton(text="📋 Инструкция", callback_data="admin_mode_help")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_set_mode_private")
async def set_mode_private(callback: types.CallbackQuery):
    """Установка режима личных сообщений."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    if settings.get('bot_mode') == 'private':
        return await callback.answer("Режим личных сообщений уже активен")
    
    settings['bot_mode'] = 'private'
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer("✅ Включен режим личных сообщений")
    
    # Обновляем меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Личка ✓", callback_data="admin_set_mode_private"),
            InlineKeyboardButton(text="👥 Группа", callback_data="admin_set_mode_group"),
        ],
        [InlineKeyboardButton(text="🔗 Привязать группу", callback_data="admin_link_group")],
        [InlineKeyboardButton(text="📋 Инструкция", callback_data="admin_mode_help")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    try:
        await callback.message.edit_text(
            "⚙️ <b>Режим работы бота</b>\n\n"
            "Текущий режим: 🤖 <b>Личные сообщения</b>\n"
            "Бот работает в личке, пользователи пишут напрямую боту",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "admin_set_mode_group")
async def set_mode_group(callback: types.CallbackQuery):
    """Установка режима группы."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    group_id = settings.get('group_id')
    if not group_id:
        return await callback.answer(
            "⚠️ Сначала привяжите группу!\nДобавьте бота в группу и нажмите 'Привязать группу'",
            show_alert=True
        )
    
    if settings.get('bot_mode') == 'group':
        return await callback.answer("Режим группы уже активен")
    
    settings['bot_mode'] = 'group'
    save_json(SETTINGS_FILE, settings)
    
    await callback.answer("✅ Включен режим группы")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Личка", callback_data="admin_set_mode_private"),
            InlineKeyboardButton(text="👥 Группа ✓", callback_data="admin_set_mode_group"),
        ],
        [InlineKeyboardButton(text="🔗 Привязать группу", callback_data="admin_link_group")],
        [InlineKeyboardButton(text="📋 Инструкция", callback_data="admin_mode_help")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    try:
        await callback.message.edit_text(
            f"⚙️ <b>Режим работы бота</b>\n\n"
            f"Текущий режим: 👥 <b>Группа</b>\n"
            f"ID группы: <code>{group_id}</code>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "admin_link_group")
async def link_group(callback: types.CallbackQuery, state: FSMContext):
    """Привязка группы."""
    await state.set_state(AdminStates.waiting_for_group_id)
    
    text = (
        "🔗 <b>Привязка группы</b>\n\n"
        "<b>Способ 1 (рекомендуется):</b>\n"
        "1. Добавьте бота в группу как администратора\n"
        "2. Напишите в группе команду <code>/link</code>\n"
        "3. Бот автоматически привяжет группу\n\n"
        "<b>Способ 2 (вручную):</b>\n"
        "Отправьте ID группы (начинается с -100...)\n\n"
        "💡 Узнать ID группы можно добавив бота @getmyid_bot в группу"
    )
    
    await callback.message.edit_text(text, reply_markup=back_to_admin_panel(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_for_group_id)
async def process_group_id(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка ID группы."""
    try:
        group_id = int(message.text.strip())
        
        # Проверяем что это группа (отрицательный ID)
        if group_id >= 0:
            await message.answer(
                "⚠️ ID группы должен быть отрицательным числом (начинается с -)",
                reply_markup=back_to_admin_panel()
            )
            return
        
        # Проверяем доступ к группе
        try:
            chat = await bot.get_chat(group_id)
            chat_title = chat.title or "Без названия"
        except Exception:
            await message.answer(
                "❌ Не удалось получить информацию о группе.\n"
                "Убедитесь что бот добавлен в группу как администратор.",
                reply_markup=back_to_admin_panel()
            )
            return
        
        settings = load_json(SETTINGS_FILE, default_data={})
        settings['group_id'] = group_id
        settings['group_title'] = chat_title
        save_json(SETTINGS_FILE, settings)
        
        await state.clear()
        await message.answer(
            f"✅ Группа привязана!\n\n"
            f"<b>Название:</b> {html.escape(chat_title)}\n"
            f"<b>ID:</b> <code>{group_id}</code>",
            reply_markup=admin_start_keyboard(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "⚠️ Введите числовой ID группы",
            reply_markup=back_to_admin_panel()
        )


@router.callback_query(F.data == "admin_mode_help")
async def mode_help(callback: types.CallbackQuery):
    """Инструкция по режимам."""
    text = (
        "📋 <b>Инструкция по режимам работы</b>\n\n"
        "<b>🤖 Режим личных сообщений:</b>\n"
        "• Пользователи пишут боту напрямую\n"
        "• Сообщения пересылаются админу\n"
        "• Бот отвечает в личке пользователя\n"
        "• Подходит для поддержки 1-на-1\n\n"
        "<b>👥 Режим группы:</b>\n"
        "• Бот работает в группе/супергруппе\n"
        "• Реагирует на упоминания и команды\n"
        "• Отвечает на вопросы из FAQ\n"
        "• Может использовать ИИ для ответов\n"
        "• Подходит для публичной поддержки\n\n"
        "<b>Настройка группы:</b>\n"
        "1. Добавьте бота в группу\n"
        "2. Дайте права администратора\n"
        "3. Напишите /link в группе\n"
        "4. Включите режим группы"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="‹ Назад", callback_data="admin_work_mode_menu")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# БЫСТРЫЕ ОТВЕТЫ
# ============================================================================

@router.callback_query(F.data == "admin_quick_replies")
async def quick_replies_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню быстрых ответов."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    quick_replies = settings.get('quick_replies', {})
    
    if quick_replies:
        replies_text = "\n".join([f"• <b>{name}</b>: {text[:50]}..." for name, text in list(quick_replies.items())[:10]])
    else:
        replies_text = "<i>Нет сохранённых ответов</i>"
    
    text = (
        "⚡ <b>Быстрые ответы</b>\n\n"
        f"Сохранено: {len(quick_replies)} шт.\n\n"
        f"{replies_text}\n\n"
        "Быстрые ответы можно использовать при ответе пользователю."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ответ", callback_data="admin_quick_reply_add")],
        [InlineKeyboardButton(text="📋 Список ответов", callback_data="admin_quick_reply_list")],
        [InlineKeyboardButton(text="🗑️ Удалить ответ", callback_data="admin_quick_reply_delete")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_quick_reply_add")
async def quick_reply_add(callback: types.CallbackQuery, state: FSMContext):
    """Добавление быстрого ответа - шаг 1."""
    await state.set_state(AdminStates.waiting_for_quick_reply_name)
    
    text = (
        "➕ <b>Добавление быстрого ответа</b>\n\n"
        "Шаг 1/2: Введите короткое название (команду).\n\n"
        "Например: <code>приветствие</code>, <code>цена</code>, <code>контакты</code>"
    )
    
    await callback.message.edit_text(text, reply_markup=back_to_admin_panel(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_for_quick_reply_name)
async def process_quick_reply_name(message: types.Message, state: FSMContext):
    """Обработка названия быстрого ответа."""
    name = message.text.strip().lower()
    
    if len(name) > 30:
        await message.answer("⚠️ Название слишком длинное (макс. 30 символов)")
        return
    
    if not name.replace("_", "").isalnum():
        await message.answer("⚠️ Используйте только буквы, цифры и _")
        return
    
    await state.update_data(quick_reply_name=name)
    await state.set_state(AdminStates.waiting_for_quick_reply_text)
    
    await message.answer(
        f"Шаг 2/2: Введите текст ответа для <b>{name}</b>\n\n"
        "Поддерживается HTML-разметка.",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_quick_reply_text)
async def process_quick_reply_text(message: types.Message, state: FSMContext):
    """Обработка текста быстрого ответа."""
    data = await state.get_data()
    name = data.get('quick_reply_name')
    text = message.text.strip()
    
    settings = load_json(SETTINGS_FILE, default_data={})
    if 'quick_replies' not in settings:
        settings['quick_replies'] = {}
    
    settings['quick_replies'][name] = text
    save_json(SETTINGS_FILE, settings)
    
    await state.clear()
    await message.answer(
        f"✅ Быстрый ответ <b>{name}</b> сохранён!\n\n"
        f"Используйте: <code>/qr {name}</code> при ответе пользователю",
        reply_markup=admin_start_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_quick_reply_list")
async def quick_reply_list(callback: types.CallbackQuery):
    """Список всех быстрых ответов."""
    settings = load_json(SETTINGS_FILE, default_data={})
    quick_replies = settings.get('quick_replies', {})
    
    if not quick_replies:
        return await callback.answer("Нет сохранённых ответов", show_alert=True)
    
    text = "📋 <b>Все быстрые ответы:</b>\n\n"
    for name, reply_text in quick_replies.items():
        text += f"<b>/{name}</b>\n{html.escape(reply_text[:100])}{'...' if len(reply_text) > 100 else ''}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="‹ Назад", callback_data="admin_quick_replies")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_quick_reply_delete")
async def quick_reply_delete_menu(callback: types.CallbackQuery):
    """Меню удаления быстрых ответов."""
    settings = load_json(SETTINGS_FILE, default_data={})
    quick_replies = settings.get('quick_replies', {})
    
    if not quick_replies:
        return await callback.answer("Нет ответов для удаления", show_alert=True)
    
    buttons = []
    for name in list(quick_replies.keys())[:15]:
        buttons.append([InlineKeyboardButton(
            text=f"🗑️ {name}",
            callback_data=f"admin_qr_del_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_quick_replies")])
    
    await callback.message.edit_text(
        "🗑️ Выберите ответ для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_qr_del_"))
async def quick_reply_delete(callback: types.CallbackQuery):
    """Удаление быстрого ответа."""
    name = callback.data.replace("admin_qr_del_", "")
    
    settings = load_json(SETTINGS_FILE, default_data={})
    if 'quick_replies' in settings and name in settings['quick_replies']:
        del settings['quick_replies'][name]
        save_json(SETTINGS_FILE, settings)
        await callback.answer(f"✅ Ответ '{name}' удалён")
    else:
        await callback.answer("Ответ не найден")
    
    # Возвращаемся в меню
    await quick_replies_menu(callback, FSMContext)


# ============================================================================
# ТРИГГЕРЫ (АВТООТВЕТЫ ПО КЛЮЧЕВЫМ СЛОВАМ)
# ============================================================================

@router.callback_query(F.data == "admin_triggers_menu")
async def triggers_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню триггеров."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    triggers = settings.get('triggers', {})
    
    if triggers:
        triggers_text = "\n".join([
            f"• <code>{kw}</code> → {resp[:30]}..." 
            for kw, resp in list(triggers.items())[:10]
        ])
    else:
        triggers_text = "<i>Нет настроенных триггеров</i>"
    
    text = (
        "🎯 <b>Триггеры</b>\n\n"
        "Автоматические ответы по ключевым словам.\n"
        "Если сообщение содержит ключевое слово — бот отвечает автоматически.\n\n"
        f"<b>Активные триггеры ({len(triggers)}):</b>\n{triggers_text}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить триггер", callback_data="admin_trigger_add")],
        [InlineKeyboardButton(text="📋 Список триггеров", callback_data="admin_trigger_list")],
        [InlineKeyboardButton(text="🗑️ Удалить триггер", callback_data="admin_trigger_delete")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_trigger_add")
async def trigger_add(callback: types.CallbackQuery, state: FSMContext):
    """Добавление триггера - шаг 1."""
    await state.set_state(AdminStates.waiting_for_trigger_keyword)
    
    text = (
        "➕ <b>Добавление триггера</b>\n\n"
        "Шаг 1/2: Введите ключевое слово или фразу.\n\n"
        "Примеры:\n"
        "• <code>цена</code> — сработает на 'какая цена', 'цена услуги'\n"
        "• <code>как оплатить</code> — точное совпадение фразы"
    )
    
    await callback.message.edit_text(text, reply_markup=back_to_admin_panel(), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_for_trigger_keyword)
async def process_trigger_keyword(message: types.Message, state: FSMContext):
    """Обработка ключевого слова триггера."""
    keyword = message.text.strip().lower()
    
    if len(keyword) < 2:
        await message.answer("⚠️ Слишком короткое слово (минимум 2 символа)")
        return
    
    if len(keyword) > 50:
        await message.answer("⚠️ Слишком длинное слово (максимум 50 символов)")
        return
    
    await state.update_data(trigger_keyword=keyword)
    await state.set_state(AdminStates.waiting_for_trigger_response)
    
    await message.answer(
        f"Шаг 2/2: Введите ответ для триггера <b>{keyword}</b>\n\n"
        "Поддерживается HTML-разметка.",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_trigger_response)
async def process_trigger_response(message: types.Message, state: FSMContext):
    """Обработка ответа триггера."""
    data = await state.get_data()
    keyword = data.get('trigger_keyword')
    response = message.text.strip()
    
    settings = load_json(SETTINGS_FILE, default_data={})
    if 'triggers' not in settings:
        settings['triggers'] = {}
    
    settings['triggers'][keyword] = response
    save_json(SETTINGS_FILE, settings)
    
    await state.clear()
    await message.answer(
        f"✅ Триггер сохранён!\n\n"
        f"<b>Ключевое слово:</b> <code>{keyword}</code>\n"
        f"<b>Ответ:</b> {response[:100]}{'...' if len(response) > 100 else ''}",
        reply_markup=admin_start_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_trigger_list")
async def trigger_list(callback: types.CallbackQuery):
    """Список всех триггеров."""
    settings = load_json(SETTINGS_FILE, default_data={})
    triggers = settings.get('triggers', {})
    
    if not triggers:
        return await callback.answer("Нет настроенных триггеров", show_alert=True)
    
    text = "📋 <b>Все триггеры:</b>\n\n"
    for keyword, response in triggers.items():
        text += f"<b>🎯 {keyword}</b>\n{html.escape(response[:150])}{'...' if len(response) > 150 else ''}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="‹ Назад", callback_data="admin_triggers_menu")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_trigger_delete")
async def trigger_delete_menu(callback: types.CallbackQuery):
    """Меню удаления триггеров."""
    settings = load_json(SETTINGS_FILE, default_data={})
    triggers = settings.get('triggers', {})
    
    if not triggers:
        return await callback.answer("Нет триггеров для удаления", show_alert=True)
    
    buttons = []
    for keyword in list(triggers.keys())[:15]:
        # Обрезаем длинные ключевые слова для кнопки
        btn_text = keyword[:20] + "..." if len(keyword) > 20 else keyword
        buttons.append([InlineKeyboardButton(
            text=f"🗑️ {btn_text}",
            callback_data=f"admin_trig_del_{keyword[:30]}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_triggers_menu")])
    
    await callback.message.edit_text(
        "🗑️ Выберите триггер для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_trig_del_"))
async def trigger_delete(callback: types.CallbackQuery):
    """Удаление триггера."""
    keyword = callback.data.replace("admin_trig_del_", "")
    
    settings = load_json(SETTINGS_FILE, default_data={})
    if 'triggers' in settings and keyword in settings['triggers']:
        del settings['triggers'][keyword]
        save_json(SETTINGS_FILE, settings)
        await callback.answer(f"✅ Триггер '{keyword}' удалён")
    else:
        await callback.answer("Триггер не найден")
    
    # Возвращаемся в меню
    await triggers_menu(callback, FSMContext)


# ============================================================================
# ЭКСПОРТ FAQ
# ============================================================================

@router.callback_query(F.data == "admin_export_faq")
async def export_faq(callback: types.CallbackQuery, bot: Bot):
    """Экспорт FAQ в JSON."""
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if not faq_list:
        return await callback.answer("FAQ пуст, нечего экспортировать", show_alert=True)
    
    # Создаём JSON
    import json
    faq_json = json.dumps(faq_list, ensure_ascii=False, indent=2)
    faq_bytes = faq_json.encode('utf-8')
    
    tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
    filename = f"faq_backup_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}.json"
    
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=BufferedInputFile(faq_bytes, filename=filename),
        caption=f"📤 Экспорт FAQ\nВсего вопросов: {len(faq_list)}"
    )
    await callback.answer("FAQ экспортирован!")


@router.callback_query(F.data == "admin_export_faq_csv")
async def export_faq_csv(callback: types.CallbackQuery, bot: Bot):
    """Экспорт FAQ в CSV."""
    faq_list = load_json(FAQ_FILE, default_data=[])
    
    if not faq_list:
        return await callback.answer("FAQ пуст, нечего экспортировать", show_alert=True)
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Вопрос', 'Ответ', 'Медиа тип', 'Медиа ID'])
    
    for item in faq_list:
        media = item.get('media', {})
        writer.writerow([
            item.get('question', ''),
            item.get('answer', ''),
            media.get('type', ''),
            media.get('file_id', ''),
        ])
    
    csv_bytes = output.getvalue().encode('utf-8-sig')
    
    tz = ZoneInfo(bot_config.TIMEZONE) if bot_config.TIMEZONE else timezone.utc
    filename = f"faq_backup_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}.csv"
    
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=BufferedInputFile(csv_bytes, filename=filename),
        caption=f"📤 Экспорт FAQ (CSV)\nВсего вопросов: {len(faq_list)}"
    )
    await callback.answer("FAQ экспортирован в CSV!")


# ============================================================================
# МУЛЬТИЯЗЫЧНОСТЬ
# ============================================================================

@router.callback_query(F.data == "admin_multilang_menu")
async def multilang_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню мультиязычности."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    
    multilang_enabled = settings.get('multilang_enabled', False)
    default_lang = settings.get('default_language', 'ru')
    
    status = "🟢 Включена" if multilang_enabled else "🔴 Выключена"
    
    lang_names = {
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English",
        "uk": "🇺🇦 Українська",
    }
    
    text = (
        "🌍 <b>Мультиязычность</b>\n\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Язык по умолчанию:</b> {lang_names.get(default_lang, default_lang)}\n\n"
        "<b>Как работает:</b>\n"
        "• Бот определяет язык по настройкам Telegram пользователя\n"
        "• Системные сообщения показываются на языке пользователя\n"
        "• Поддерживаются: 🇷🇺 🇬🇧 🇺🇦"
    )
    
    toggle_text = "🔴 Выключить" if multilang_enabled else "🟢 Включить"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data="admin_multilang_toggle")],
        [InlineKeyboardButton(text="🌐 Язык по умолчанию", callback_data="admin_multilang_default")],
        [InlineKeyboardButton(text="📊 Статистика языков", callback_data="admin_multilang_stats")],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_multilang_toggle")
async def multilang_toggle(callback: types.CallbackQuery):
    """Включение/выключение мультиязычности."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    current = settings.get('multilang_enabled', False)
    settings['multilang_enabled'] = not current
    save_json(SETTINGS_FILE, settings)
    
    status = "включена" if not current else "выключена"
    await callback.answer(f"✅ Мультиязычность {status}")
    
    # Обновляем меню
    await multilang_menu(callback, FSMContext)


@router.callback_query(F.data == "admin_multilang_default")
async def multilang_default(callback: types.CallbackQuery):
    """Выбор языка по умолчанию."""
    settings = load_json(SETTINGS_FILE, default_data={})
    current = settings.get('default_language', 'ru')
    
    languages = [
        ("ru", "🇷🇺 Русский"),
        ("en", "🇬🇧 English"),
        ("uk", "🇺🇦 Українська"),
    ]
    
    buttons = []
    for code, name in languages:
        mark = " ✓" if code == current else ""
        buttons.append([InlineKeyboardButton(
            text=f"{name}{mark}",
            callback_data=f"admin_set_default_lang_{code}"
        )])
    buttons.append([InlineKeyboardButton(text="‹ Назад", callback_data="admin_multilang_menu")])
    
    await callback.message.edit_text(
        "🌐 <b>Выберите язык по умолчанию:</b>\n\n"
        "Этот язык будет использоваться, если язык пользователя не определён.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_default_lang_"))
async def set_default_lang(callback: types.CallbackQuery):
    """Установка языка по умолчанию."""
    lang = callback.data.replace("admin_set_default_lang_", "")
    
    settings = load_json(SETTINGS_FILE, default_data={})
    settings['default_language'] = lang
    save_json(SETTINGS_FILE, settings)
    
    lang_names = {"ru": "Русский", "en": "English", "uk": "Українська"}
    await callback.answer(f"✅ Язык по умолчанию: {lang_names.get(lang, lang)}")
    
    await multilang_menu(callback, FSMContext)


@router.callback_query(F.data == "admin_multilang_stats")
async def multilang_stats(callback: types.CallbackQuery):
    """Статистика языков пользователей."""
    from bot.user_manager import get_all_users
    
    users = get_all_users()
    
    # Считаем языки
    lang_counts = {}
    for user in users:
        lang = user.get('language_code', 'unknown')
        if lang:
            lang = lang.split('-')[0]  # en-US -> en
        else:
            lang = 'unknown'
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    # Сортируем по количеству
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    
    lang_flags = {
        "ru": "🇷🇺", "en": "🇬🇧", "uk": "🇺🇦", "be": "🇧🇾",
        "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
        "pt": "🇵🇹", "pl": "🇵🇱", "tr": "🇹🇷", "zh": "🇨🇳",
        "ja": "🇯🇵", "ko": "🇰🇷", "unknown": "❓"
    }
    
    text = "📊 <b>Статистика языков</b>\n\n"
    for lang, count in sorted_langs[:15]:
        flag = lang_flags.get(lang, "🌐")
        percent = (count / len(users) * 100) if users else 0
        text += f"{flag} <code>{lang}</code>: {count} ({percent:.1f}%)\n"
    
    text += f"\n<b>Всего пользователей:</b> {len(users)}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="‹ Назад", callback_data="admin_multilang_menu")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# НАСТРОЙКИ УВЕДОМЛЕНИЙ
# ============================================================================

@router.callback_query(F.data == "admin_notifications_menu")
async def notifications_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню настройки уведомлений."""
    await state.clear()
    settings = load_json(SETTINGS_FILE, default_data={})
    
    notify_new = settings.get('notify_new_users', True)
    
    new_status = "🟢 Вкл" if notify_new else "🔴 Выкл"
    
    text = (
        "🔔 <b>Настройки уведомлений</b>\n\n"
        f"<b>Новые пользователи:</b> {new_status}\n"
        "Уведомление когда кто-то впервые пишет боту\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🆕 Новые пользователи: {new_status}",
            callback_data="admin_toggle_notify_new"
        )],
        [InlineKeyboardButton(text="‹ Назад", callback_data="admin_back_to_main")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_toggle_notify_new")
async def toggle_notify_new(callback: types.CallbackQuery):
    """Переключение уведомлений о новых пользователях."""
    settings = load_json(SETTINGS_FILE, default_data={})
    
    current = settings.get('notify_new_users', True)
    settings['notify_new_users'] = not current
    save_json(SETTINGS_FILE, settings)
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"✅ Уведомления о новых пользователях {status}")
    
    await notifications_menu(callback, FSMContext)
