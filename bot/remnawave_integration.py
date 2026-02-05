"""
Модуль для работы с Remnawave API.
Получает информацию о пользователях из панели Remnawave.

ИСПРАВЛЕНО: Февраль 2026
- Серверы берутся из реальных данных API
- Добавлен настраиваемый маппинг названий серверов
- Расширенное логирование для отладки
"""
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List, Any
import aiohttp
from bot.config import REMNAWAVE_API_URL, REMNAWAVE_API_TOKEN, load_json, SETTINGS_FILE

logger = logging.getLogger(__name__)


class RemnawaveClient:
    """Клиент для работы с Remnawave API."""
    
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получает информацию о пользователе по Telegram ID."""
        try:
            url = f"{self.api_url}/api/users"
            params = {"start": 0, "size": 1000}
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Remnawave API error: {response.status}")
                        return None
                    
                    data = await response.json()
                    response_data = data.get('response', {})
                    users = response_data.get('users', [])
                    
                    logger.info(f"Fetched {len(users)} users from Remnawave")
                    
                    # Ищем пользователя
                    for user in users:
                        user_telegram_id = user.get('telegramId') or user.get('telegram_id')
                        
                        if user_telegram_id and str(user_telegram_id) == str(telegram_id):
                            logger.info(f"Found user: {user.get('username')} for telegram_id {telegram_id}")
                            
                            # ОТЛАДКА: выводим ВСЕ поля пользователя
                            logger.debug(f"=== USER DATA FOR {telegram_id} ===")
                            logger.debug(json.dumps(user, indent=2, default=str, ensure_ascii=False))
                            logger.debug("=== END USER DATA ===")
                            
                            return user
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching user from Remnawave: {e}", exc_info=True)
            return None

    @staticmethod
    def _parse_dt(value) -> Optional[datetime]:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                ts = value / 1000 if value > 10000000000 else value
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            raw = str(value)
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _fmt_dt_local(dt: Optional[datetime], tz_name: str) -> str:
        if not dt:
            return "—"
        try:
            import pytz
            tz = pytz.timezone(tz_name) if tz_name else pytz.UTC
            local_dt = dt.astimezone(tz)
            return local_dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return dt.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _calc_remaining(dt_end: Optional[datetime]) -> str:
        if not dt_end:
            return "—"
        now = datetime.now(tz=dt_end.tzinfo or timezone.utc)
        delta = dt_end - now
        if delta.total_seconds() < 0:
            return f"Истёк ({abs(delta.days)} дн. назад)"
        if delta.days <= 1:
            return f"{delta.days} дн. {delta.seconds // 3600} ч."
        return f"{delta.days} дн."

    @staticmethod
    def _calc_period_days(dt_start: Optional[datetime], dt_end: Optional[datetime]) -> Optional[int]:
        if not dt_start or not dt_end:
            return None
        try:
            delta = dt_end - dt_start
            if delta.total_seconds() <= 0:
                return None
            return int((delta.total_seconds() + 86399) // 86400)
        except Exception:
            return None

    @staticmethod
    def _format_traffic(traffic_limit_bytes) -> str:
        if not traffic_limit_bytes or int(traffic_limit_bytes) <= 0:
            return "∞ Безлимит"
        try:
            gb = float(traffic_limit_bytes) / (1024 ** 3)
            return f"{gb:.2f} ГБ"
        except Exception:
            return "—"

    @staticmethod
    def _detect_trial(user_data: Dict) -> bool:
        for key in ("trial", "isTrial", "is_trial", "trialEndsAt"):
            if user_data.get(key) not in (None, False, 0, ""):
                return True
        tag = (user_data.get("tag") or "").lower()
        desc = (user_data.get("description") or "").lower()
        return "trial" in tag or "триал" in tag or "trial" in desc

    def _get_server_mapping(self) -> Dict[str, str]:
        """
        Получает маппинг названий серверов из settings.json.
        Админ может настроить свои названия.
        """
        try:
            settings = load_json(SETTINGS_FILE, default_data={})
            return settings.get('server_names', {})
        except Exception:
            return {}

    def _format_servers(self, user_data: Dict) -> Tuple[int, str]:
        """
        Извлекает и форматирует список серверов пользователя.
        Использует настраиваемый маппинг из settings.json.
        """
        servers: List[str] = []
        raw_servers: List[str] = []  # Для отладки
        
        # Приоритет полей для поиска серверов
        server_fields = [
            'activeUserInbounds',
            'enabledInbounds', 
            'userInbounds',
            'inbounds',
            'activeNodes',
            'nodes',
            'activeInternalSquads',
            'squads',
            'servers',
        ]
        
        # Ищем данные о серверах
        found_field = None
        for field in server_fields:
            items = user_data.get(field)
            if items:
                found_field = field
                logger.debug(f"Found server data in field '{field}': {type(items)}")
                
                if isinstance(items, list):
                    for item in items:
                        name = self._extract_server_name(item)
                        if name and name not in raw_servers:
                            raw_servers.append(name)
                elif isinstance(items, dict):
                    for key, value in items.items():
                        name = self._extract_server_name(value) or self._extract_server_name(key)
                        if name and name not in raw_servers:
                            raw_servers.append(name)
                
                if raw_servers:
                    break
        
        if not raw_servers:
            # Логируем доступные поля для отладки
            logger.warning(f"No servers found. Available fields: {list(user_data.keys())}")
            return 0, "—"
        
        logger.debug(f"Raw servers from '{found_field}': {raw_servers}")
        
        # Получаем маппинг названий
        server_mapping = self._get_server_mapping()
        logger.debug(f"Server mapping from settings: {server_mapping}")
        
        # Применяем маппинг или используем сырые названия
        for raw_name in raw_servers:
            # Пробуем найти в маппинге (без учёта регистра)
            mapped_name = None
            for key, value in server_mapping.items():
                if key.lower() == raw_name.lower():
                    mapped_name = value
                    break
            
            if mapped_name:
                servers.append(mapped_name)
            else:
                # Используем сырое название, убирая технические суффиксы
                clean_name = raw_name
                for suffix in ['-squad', '-node', '-server', '-inbound']:
                    if clean_name.lower().endswith(suffix):
                        clean_name = clean_name[:-len(suffix)]
                servers.append(clean_name)
        
        # Фильтруем служебные названия
        filtered = [s for s in servers if not any(
            x in s.lower() for x in ['default', 'test', 'internal']
        )]
        if not filtered:
            filtered = servers
        
        count = len(filtered)
        servers_str = ", ".join(filtered[:4])
        if count > 4:
            servers_str += f" +{count - 4}"
        
        return count, servers_str

    def _extract_server_name(self, item: Any) -> Optional[str]:
        """Извлекает название сервера из разных структур."""
        if not item:
            return None
        
        if isinstance(item, str):
            return item.strip() or None
        
        if isinstance(item, dict):
            # Приоритет полей
            for field in ['name', 'tag', 'serverName', 'nodeName', 'remark', 'title', 'address']:
                if field in item and item[field]:
                    val = item[field]
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            
            # Вложенные объекты
            for nested in ['node', 'server', 'inbound']:
                if nested in item and isinstance(item[nested], dict):
                    for field in ['name', 'tag', 'remark']:
                        if field in item[nested] and item[nested][field]:
                            return str(item[nested][field]).strip()
        
        return None

    def format_user_info(
        self,
        user_data: Dict,
        tg_full_name: Optional[str] = None,
        tg_username: Optional[str] = None,
        tz_name: str = "UTC",
    ) -> str:
        """Форматирует карточку пользователя."""
        if not user_data:
            return "🟠 Пользователь не найден в панели Remnawave"

        tg_full_name = tg_full_name or "—"
        tg_username = f"@{tg_username}" if tg_username else "—"

        telegram_id = user_data.get('telegramId') or user_data.get('telegram_id') or '—'
        status_raw = (user_data.get('status') or 'unknown').upper()

        is_trial = self._detect_trial(user_data)
        plan_str = "🎁 Триал" if is_trial else "💎 Платная"

        dt_expire = self._parse_dt(user_data.get('expireAt') or user_data.get('expire_at'))
        dt_created = self._parse_dt(user_data.get('createdAt') or user_data.get('created_at'))
        period_days = self._calc_period_days(dt_created, dt_expire)

        expire_str = self._fmt_dt_local(dt_expire, tz_name)
        remain_str = self._calc_remaining(dt_expire)

        traffic_limit = user_data.get('trafficLimitBytes') or user_data.get('traffic_limit_bytes')
        traffic_str = self._format_traffic(traffic_limit)

        devices = (
            user_data.get('hwidDeviceLimit') or 
            user_data.get('deviceLimit') or 
            user_data.get('maxDevices')
        )
        devices_str = str(devices) if devices is not None else "—"

        srv_count, srv_list = self._format_servers(user_data)
        servers_str = f"{srv_count} шт. ({srv_list})" if srv_count else "—"

        period_str = f"{period_days} дней" if period_days else "—"

        lines = [
            f"👤 <b>Пользователь:</b> {tg_full_name}",
            f"🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>",
            f"📱 <b>Username:</b> {tg_username}",
            f"👥 <b>Статус:</b> {plan_str}",
            f"🟢 <b>{status_raw}</b>",
            "",
            "📱 <b>Параметры подписки:</b>",
            f"📅 <b>Период:</b> {period_str}",
            f"📊 <b>Трафик:</b> {traffic_str}",
            f"📱 <b>Устройства:</b> {devices_str}",
            f"🌐 <b>Серверы:</b> {servers_str}",
            "",
            f"📆 <b>Действует до:</b> {expire_str}",
            f"⏱️ <b>Осталось:</b> {remain_str}",
        ]

        return "\n".join(lines).strip()


# Глобальный экземпляр
remnawave_client = RemnawaveClient(REMNAWAVE_API_URL, REMNAWAVE_API_TOKEN) if REMNAWAVE_API_URL and REMNAWAVE_API_TOKEN else None

if remnawave_client:
    logger.info(f"Remnawave integration initialized: {REMNAWAVE_API_URL}")
else:
    logger.warning("Remnawave integration not configured")
