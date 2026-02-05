from aiogram import Router, F, Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from bot.ai_block_manager import block_ai_for_user

logger = logging.getLogger(__name__)
router = Router()

class AdminReply(StatesGroup):
    waiting_for_reply = State()

@router.callback_query(F.data.startswith("reply_to_"))
async def start_admin_reply(callback: types.CallbackQuery, state: FSMContext):
    """
    Начинает процесс ответа админа.
    Блокирует ИИ для этого пользователя.
    """
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(user_id_to_reply=user_id)
    
    # ⚡️ Блокируем ИИ для этого пользователя
    block_ai_for_user(user_id)
    logger.info(f"Admin {callback.from_user.id} started replying to user {user_id}. AI blocked for this user.")
    
    await callback.message.answer(f"Введите ваш ответ для пользователя с ID {user_id}:")
    await state.set_state(AdminReply.waiting_for_reply)
    await callback.answer()

@router.message(AdminReply.waiting_for_reply)
async def process_admin_reply(message: types.Message, state: FSMContext, bot: Bot):
    """Отправляет ответ от админа пользователю."""
    data = await state.get_data()
    user_id = data.get("user_id_to_reply")

    if not user_id:
        await message.answer("Произошла ошибка, ID пользователя не найден.")
        await state.clear()
        return

    try:
        # Пытаемся отправить сообщение пользователю
        await bot.send_message(user_id, "Вам ответ от администратора:")
        await message.copy_to(user_id) # Копируем сообщение админа (текст, фото, файл)
        await message.answer(f"✨ Ответ отправлен пользователю {user_id}.")
        logger.info(f"Admin successfully sent reply to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send admin reply to user {user_id}: {e}")
        await message.answer(f"🛑 Не удалось отправить ответ пользователю {user_id}. Ошибка: {e}")

    await state.clear()
    # Примечание: ИИ остается заблокированным на 30 минут или пока админ не разблокирует
