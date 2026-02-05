"""
Модуль управления пользователями.
Хранит статистику, историю сообщений, блокировки.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

USERS_FILE = "bot/data/users.json"


def _load_users() -> dict:
    """Загружает данные пользователей."""
    try:
        path = Path(USERS_FILE)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading users: {e}")
    return {"users": {}, "blocked": [], "broadcasts": []}


def _save_users(data: dict):
    """Сохраняет данные пользователей."""
    try:
        path = Path(USERS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving users: {e}")


def track_user(user_id: int, full_name: str, username: Optional[str] = None, language_code: Optional[str] = None) -> bool:
    """
    Регистрирует пользователя или обновляет его данные.
    Вызывается при каждом сообщении.
    
    Returns:
        True если это новый пользователь, False если существующий
    """
    data = _load_users()
    uid_str = str(user_id)
    is_new = uid_str not in data["users"]

    if is_new:
        data["users"][uid_str] = {
            "user_id": user_id,
            "name": full_name,
            "username": username,
            "language_code": language_code,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "message_count": 0,
            "blocked": False,
        }

    user = data["users"][uid_str]
    user["name"] = full_name
    user["username"] = username
    if language_code:
        user["language_code"] = language_code
    user["last_seen"] = datetime.now(timezone.utc).isoformat()
    user["message_count"] = user.get("message_count", 0) + 1

    _save_users(data)
    return is_new


def get_user(user_id: int) -> Optional[dict]:
    """Получает данные пользователя."""
    data = _load_users()
    return data["users"].get(str(user_id))


def get_all_users() -> list:
    """Возвращает список всех пользователей."""
    data = _load_users()
    users = list(data["users"].values())
    # Сортируем по последней активности
    users.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return users


def get_users_stats() -> dict:
    """Возвращает статистику пользователей."""
    data = _load_users()
    users = data["users"].values()
    total = len(users)
    blocked = sum(1 for u in users if u.get("blocked"))
    total_messages = sum(u.get("message_count", 0) for u in users)

    return {
        "total": total,
        "blocked": blocked,
        "total_messages": total_messages,
    }


def block_user(user_id: int) -> bool:
    """Блокирует пользователя."""
    data = _load_users()
    uid_str = str(user_id)

    if uid_str in data["users"]:
        data["users"][uid_str]["blocked"] = True
        _save_users(data)
        logger.info(f"User {user_id} blocked")
        return True

    # Если пользователя нет, создаём запись
    data["users"][uid_str] = {
        "user_id": user_id,
        "name": "Unknown",
        "blocked": True,
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "message_count": 0,
    }
    _save_users(data)
    logger.info(f"User {user_id} blocked (new record)")
    return True


def unblock_user(user_id: int) -> bool:
    """Разблокирует пользователя."""
    data = _load_users()
    uid_str = str(user_id)

    if uid_str in data["users"]:
        data["users"][uid_str]["blocked"] = False
        _save_users(data)
        logger.info(f"User {user_id} unblocked")
        return True
    return False


def is_user_blocked(user_id: int) -> bool:
    """Проверяет, заблокирован ли пользователь."""
    data = _load_users()
    user = data["users"].get(str(user_id))
    if user:
        return user.get("blocked", False)
    return False


def get_active_user_ids() -> list[int]:
    """Возвращает список ID незаблокированных пользователей."""
    data = _load_users()
    return [
        int(uid) for uid, u in data["users"].items()
        if not u.get("blocked", False)
    ]


def add_broadcast_record(message_text: str, sent_count: int, failed_count: int):
    """Записывает историю рассылки."""
    data = _load_users()
    if "broadcasts" not in data:
        data["broadcasts"] = []

    data["broadcasts"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_preview": message_text[:100],
        "sent": sent_count,
        "failed": failed_count,
    })

    # Храним только последние 20 рассылок
    data["broadcasts"] = data["broadcasts"][-20:]
    _save_users(data)


def get_broadcast_history(limit: int = 10) -> list:
    """Возвращает историю рассылок."""
    data = _load_users()
    broadcasts = data.get("broadcasts", [])
    return list(reversed(broadcasts[-limit:]))
