"""
Модуль для управления блокировкой ИИ-ответов.
Когда админ начинает отвечать пользователю, ИИ блокируется для этого пользователя.
"""
import time
import logging

logger = logging.getLogger(__name__)

# Хранилище заблокированных пользователей: {user_id: timestamp}
# Если админ начал отвечать, ИИ не должен отвечать этому пользователю
_blocked_users = {}

# Время блокировки в секундах (30 минут по умолчанию)
BLOCK_DURATION = 30 * 60


def block_ai_for_user(user_id: int):
    """
    Блокирует ИИ-ответы для указанного пользователя.
    Используется когда админ начинает отвечать.
    """
    _blocked_users[user_id] = time.time()
    logger.info(f"AI blocked for user {user_id}")


def unblock_ai_for_user(user_id: int):
    """
    Разблокирует ИИ-ответы для указанного пользователя.
    """
    if user_id in _blocked_users:
        del _blocked_users[user_id]
        logger.info(f"AI unblocked for user {user_id}")


def is_ai_blocked_for_user(user_id: int) -> bool:
    """
    Проверяет, заблокирован ли ИИ для данного пользователя.
    Автоматически разблокирует, если прошло больше BLOCK_DURATION времени.
    """
    if user_id not in _blocked_users:
        return False
    
    # Проверяем, не истекло ли время блокировки
    block_time = _blocked_users[user_id]
    if time.time() - block_time > BLOCK_DURATION:
        logger.info(f"AI block expired for user {user_id}, auto-unblocking")
        unblock_ai_for_user(user_id)
        return False
    
    return True


def cleanup_expired_blocks():
    """
    Очищает устаревшие блокировки.
    Можно вызывать периодически для очистки памяти.
    """
    current_time = time.time()
    expired_users = [
        user_id for user_id, block_time in _blocked_users.items()
        if current_time - block_time > BLOCK_DURATION
    ]
    
    for user_id in expired_users:
        unblock_ai_for_user(user_id)
    
    if expired_users:
        logger.debug(f"Cleaned up {len(expired_users)} expired AI blocks")
