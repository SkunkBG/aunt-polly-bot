from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from bot.config import FAQ_FILE, load_json
from bot.keyboards.inline import faq_questions_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "faq")
async def handle_faq(callback: CallbackQuery, bot: Bot):
    """
    Обработчик нажатия на кнопку FAQ.
    Показывает меню с вопросами.
    """
    faq_data = load_json(FAQ_FILE, default_data=[])
    
    if not faq_data:
        await callback.message.answer("Список часто задаваемых вопросов пока пуст.")
        await callback.answer()
        return
    
    # Показываем меню с вопросами
    await callback.message.answer(
        "📖 <b>Часто задаваемые вопросы</b>\n\nВыберите интересующий вас вопрос:",
        reply_markup=faq_questions_keyboard(faq_data)
    )
    await callback.answer()
    logger.info(f"Showed FAQ menu with {len(faq_data)} questions to user {callback.from_user.id}")


@router.callback_query(F.data.startswith("show_faq_"))
async def show_faq_answer(callback: CallbackQuery, bot: Bot):
    """
    Обработчик показа конкретного ответа из FAQ.
    Поддерживает отображение текста и медиа (фото, видео, файлы).
    """
    # Извлекаем индекс вопроса из callback_data
    try:
        faq_index = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("🛑 Ошибка: неверный формат данных")
        return
    
    faq_data = load_json(FAQ_FILE, default_data=[])
    
    if faq_index >= len(faq_data):
        await callback.answer("🛑 Вопрос не найден")
        return
    
    item = faq_data[faq_index]
    question = item.get('question', 'Вопрос не указан')
    answer = item.get('answer', 'Ответ не указан')
    media = item.get('media')
    
    # Формируем текст
    text = f"❔ <b>Вопрос:</b> {question}\n\n💡 <b>Ответ:</b> {answer}"
    
    try:
        # Если есть медиа, отправляем с медиа
        if media and media.get('file_id'):
            media_type = media.get('type')
            file_id = media.get('file_id')
            
            if media_type == 'photo':
                await bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=file_id,
                    caption=text
                )
            elif media_type == 'video':
                await bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=file_id,
                    caption=text
                )
            elif media_type == 'document':
                await bot.send_document(
                    chat_id=callback.message.chat.id,
                    document=file_id,
                    caption=text
                )
            else:
                # Неизвестный тип медиа, отправляем только текст
                await callback.message.answer(text)
        else:
            # Нет медиа, отправляем только текст
            await callback.message.answer(text)
            
    except Exception as e:
        logger.error(f"Error sending FAQ item {faq_index}: {e}")
        # В случае ошибки отправляем хотя бы текст
        await callback.message.answer(text)
    
    await callback.answer()
    logger.info(f"Sent FAQ answer #{faq_index} to user {callback.from_user.id}")
