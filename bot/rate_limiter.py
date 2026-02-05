"""
Rate Limiter для защиты бота от спама и DDoS.

Уровни защиты:
1. Глобальный лимит - общее количество запросов в секунду
2. Лимит на пользователя - запросы от одного user_id
3. Антифлуд - защита от быстрых последовательных сообщений
4. Чёрный список - автоматическая блокировка спамеров
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from functools import wraps

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Конфигурация rate limiter."""
    # Глобальные лимиты
    global_rate: int = 100  # Запросов в секунду со всех пользователей
    
    # Лимиты на пользователя
    user_rate: int = 5  # Запросов в секунду от одного пользователя
    user_burst: int = 10  # Максимальный burst
    
    # Антифлуд
    antiflood_rate: float = 0.5  # Минимальный интервал между сообщениями (сек)
    antiflood_messages: int = 5  # Сообщений подряд для триггера
    
    # Автобан
    auto_ban_threshold: int = 50  # Превышений для автобана
    auto_ban_duration: int = 3600  # Длительность бана (секунд)
    
    # Сообщения
    rate_limit_message: str = "⚠️ Слишком много запросов. Подождите немного."
    banned_message: str = "🚫 Вы временно заблокированы за спам."


@dataclass
class UserState:
    """Состояние пользователя для rate limiting."""
    tokens: float = 10.0  # Token bucket
    last_update: float = field(default_factory=time.time)
    message_times: list = field(default_factory=list)
    violations: int = 0
    banned_until: float = 0


class RateLimiter:
    """
    Rate Limiter с алгоритмом Token Bucket.
    
    Использование:
        limiter = RateLimiter(config)
        
        @limiter.limit
        async def handle_message(message: Message):
            ...
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.users: Dict[int, UserState] = defaultdict(UserState)
        self.global_tokens: float = float(self.config.global_rate)
        self.global_last_update: float = time.time()
        self._lock = asyncio.Lock()
        
        # Статистика
        self.stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'banned': 0,
        }
    
    def _refill_tokens(self, state: UserState) -> None:
        """Пополняет токены на основе прошедшего времени."""
        now = time.time()
        elapsed = now - state.last_update
        state.tokens = min(
            self.config.user_burst,
            state.tokens + elapsed * self.config.user_rate
        )
        state.last_update = now
    
    def _refill_global_tokens(self) -> None:
        """Пополняет глобальные токены."""
        now = time.time()
        elapsed = now - self.global_last_update
        self.global_tokens = min(
            float(self.config.global_rate * 2),  # Burst = 2x rate
            self.global_tokens + elapsed * self.config.global_rate
        )
        self.global_last_update = now
    
    def _check_antiflood(self, state: UserState) -> bool:
        """Проверяет антифлуд (слишком быстрые сообщения)."""
        now = time.time()
        
        # Очищаем старые записи
        state.message_times = [
            t for t in state.message_times 
            if now - t < 10  # Храним последние 10 секунд
        ]
        
        # Проверяем интервал между сообщениями
        if state.message_times:
            last_time = state.message_times[-1]
            if now - last_time < self.config.antiflood_rate:
                return False
        
        # Проверяем количество сообщений подряд
        if len(state.message_times) >= self.config.antiflood_messages:
            return False
        
        state.message_times.append(now)
        return True
    
    def is_banned(self, user_id: int) -> bool:
        """Проверяет, забанен ли пользователь."""
        state = self.users[user_id]
        if state.banned_until > time.time():
            return True
        return False
    
    def ban_user(self, user_id: int, duration: Optional[int] = None) -> None:
        """Банит пользователя."""
        duration = duration or self.config.auto_ban_duration
        state = self.users[user_id]
        state.banned_until = time.time() + duration
        self.stats['banned'] += 1
        logger.warning(f"User {user_id} banned for {duration} seconds")
    
    def unban_user(self, user_id: int) -> None:
        """Разбанивает пользователя."""
        if user_id in self.users:
            self.users[user_id].banned_until = 0
            self.users[user_id].violations = 0
            logger.info(f"User {user_id} unbanned")
    
    async def check_rate_limit(self, user_id: int) -> tuple[bool, str]:
        """
        Проверяет rate limit для пользователя.
        
        Returns:
            (allowed: bool, message: str)
        """
        async with self._lock:
            self.stats['total_requests'] += 1
            
            # Проверяем бан
            if self.is_banned(user_id):
                return False, self.config.banned_message
            
            state = self.users[user_id]
            
            # Пополняем токены
            self._refill_tokens(state)
            self._refill_global_tokens()
            
            # Проверяем глобальный лимит
            if self.global_tokens < 1:
                self.stats['rate_limited'] += 1
                return False, self.config.rate_limit_message
            
            # Проверяем лимит пользователя
            if state.tokens < 1:
                state.violations += 1
                self.stats['rate_limited'] += 1
                
                # Автобан при превышении порога
                if state.violations >= self.config.auto_ban_threshold:
                    self.ban_user(user_id)
                    return False, self.config.banned_message
                
                return False, self.config.rate_limit_message
            
            # Проверяем антифлуд
            if not self._check_antiflood(state):
                state.violations += 1
                self.stats['rate_limited'] += 1
                return False, self.config.rate_limit_message
            
            # Всё ок, потребляем токен
            state.tokens -= 1
            self.global_tokens -= 1
            
            return True, ""
    
    def get_stats(self) -> dict:
        """Возвращает статистику."""
        return {
            **self.stats,
            'active_users': len(self.users),
            'banned_users': sum(1 for u in self.users.values() if u.banned_until > time.time()),
        }
    
    def limit(self, func: Callable) -> Callable:
        """Декоратор для ограничения функции."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Извлекаем user_id из аргументов
            user_id = None
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    user_id = arg.from_user.id if arg.from_user else None
                    break
            
            if user_id is None:
                return await func(*args, **kwargs)
            
            allowed, message = await self.check_rate_limit(user_id)
            
            if not allowed:
                # Отправляем сообщение об ограничении
                for arg in args:
                    if isinstance(arg, Message):
                        try:
                            await arg.answer(message)
                        except Exception:
                            pass
                        return None
                    elif isinstance(arg, CallbackQuery):
                        try:
                            await arg.answer(message, show_alert=True)
                        except Exception:
                            pass
                        return None
                return None
            
            return await func(*args, **kwargs)
        
        return wrapper


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для автоматического rate limiting всех хэндлеров.
    
    Использование:
        dp = Dispatcher()
        dp.message.middleware(RateLimitMiddleware(limiter))
        dp.callback_query.middleware(RateLimitMiddleware(limiter))
    """
    
    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        
        if user_id is None:
            return await handler(event, data)
        
        # Проверяем rate limit
        allowed, message = await self.limiter.check_rate_limit(user_id)
        
        if not allowed:
            if isinstance(event, Message):
                try:
                    await event.answer(message)
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(message, show_alert=True)
                except Exception:
                    pass
            return None
        
        return await handler(event, data)


# Глобальный экземпляр (можно настроить в config)
rate_limiter = RateLimiter()
