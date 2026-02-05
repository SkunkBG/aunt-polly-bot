"""
Aunt Polly Bot - Telegram бот с улучшенной защитой.

Запуск:
    python main.py

Режимы:
    - polling: для разработки
    - webhook: для продакшена (требует HTTPS)
"""
import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot import config
from bot.handlers import start, user_messages, admin_reply, faq, admin_panel, group_messages
from bot.backup_manager import run_daily_backup_loop
from bot.rate_limiter import RateLimiter, RateLimitMiddleware, RateLimitConfig

# Логгер
logger = logging.getLogger(__name__)


def setup_rate_limiter() -> RateLimiter:
    """Настройка rate limiter из конфигурации."""
    # Можно настроить через переменные окружения
    rate_config = RateLimitConfig(
        # Глобальный лимит: 100 запросов/сек
        global_rate=int(config.load_json(config.SETTINGS_FILE, {}).get('rate_limit_global', 100)),
        # Лимит на пользователя: 5 запросов/сек
        user_rate=int(config.load_json(config.SETTINGS_FILE, {}).get('rate_limit_user', 5)),
        user_burst=int(config.load_json(config.SETTINGS_FILE, {}).get('rate_limit_burst', 10)),
        # Антифлуд: минимум 0.5 сек между сообщениями
        antiflood_rate=float(config.load_json(config.SETTINGS_FILE, {}).get('antiflood_rate', 0.5)),
        # Автобан: после 50 нарушений на 1 час
        auto_ban_threshold=int(config.load_json(config.SETTINGS_FILE, {}).get('auto_ban_threshold', 50)),
        auto_ban_duration=int(config.load_json(config.SETTINGS_FILE, {}).get('auto_ban_duration', 3600)),
    )
    
    limiter = RateLimiter(rate_config)
    logger.info(f"Rate limiter configured: {rate_config.user_rate} req/sec per user, {rate_config.global_rate} req/sec global")
    return limiter


async def on_startup(bot: Bot) -> None:
    """Действия при запуске: установка вебхука, если нужно."""
    if config.BOT_MODE == "webhook":
        if not config.WEBHOOK_HOST:
            logger.critical("Webhook mode is enabled, but WEBHOOK_HOST is not set in .env")
            sys.exit(1)
        
        # Параметры для set_webhook
        webhook_params = {
            "url": f"{config.WEBHOOK_HOST}{config.WEBHOOK_PATH}",
            "drop_pending_updates": True,
            # Разрешённые типы обновлений (оптимизация)
            "allowed_updates": ["message", "callback_query"],
        }
        
        # Добавляем secret_token если он установлен
        if config.WEBHOOK_SECRET_TOKEN:
            webhook_params["secret_token"] = config.WEBHOOK_SECRET_TOKEN
            logger.info("✅ Webhook с secret token (защита включена)")
        else:
            logger.warning("⚠️ WEBHOOK_SECRET_TOKEN не задан — рекомендуется установить!")
        
        await bot.set_webhook(**webhook_params)
        logger.info(f"Webhook set to {config.WEBHOOK_HOST}{config.WEBHOOK_PATH}")

    # Ежедневный бэкап
    if config.ADMIN_ID:
        bot._daily_backup_task = asyncio.create_task(run_daily_backup_loop(bot))
        logger.info("📦 Daily backup task started")
    else:
        logger.warning("ADMIN_ID не задан — ежедневный бэкап не запущен")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке."""
    if config.BOT_MODE == "webhook":
        logger.info("Shutting down... Deleting webhook.")
        await bot.delete_webhook()

    # Останавливаем фоновую задачу бэкапа
    task = getattr(bot, "_daily_backup_task", None)
    if task:
        task.cancel()


async def main() -> None:
    logger.info("🚀 Initializing bot...")
    
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # =========================================================================
    # ЗАЩИТА: Rate Limiting Middleware
    # =========================================================================
    rate_limiter = setup_rate_limiter()
    
    # Применяем middleware к message и callback_query
    dp.message.middleware(RateLimitMiddleware(rate_limiter))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limiter))
    
    # Сохраняем ссылку для доступа из хэндлеров (например, для статистики)
    dp["rate_limiter"] = rate_limiter
    
    logger.info("🛡️ Rate limiting middleware enabled")

    # =========================================================================
    # РОУТЕРЫ
    # =========================================================================
    logger.debug("Including routers...")
    dp.include_router(admin_panel.router)
    dp.include_router(start.router)
    dp.include_router(faq.router)
    dp.include_router(admin_reply.router)
    dp.include_router(group_messages.router)  # Группы
    dp.include_router(user_messages.router)   # Личные сообщения (последний!)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # =========================================================================
    # ЗАПУСК
    # =========================================================================
    if config.BOT_MODE == "webhook":
        app = web.Application()
        
        # Health check endpoint
        async def health_check(request):
            stats = rate_limiter.get_stats()
            return web.json_response({
                "status": "ok",
                "rate_limiter": stats
            })
        
        app.router.add_get("/health", health_check)
        
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=config.WEB_SERVER_HOST, port=config.WEB_SERVER_PORT)
        
        logger.info(f"🌐 Bot starting in webhook mode on {config.WEB_SERVER_HOST}:{config.WEB_SERVER_PORT}")
        await site.start()
        await asyncio.Event().wait()
        
    elif config.BOT_MODE == "polling":
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🔄 Bot starting in polling mode...")
        await dp.start_polling(bot)
    else:
        logger.critical(f"Unknown BOT_MODE: {config.BOT_MODE}")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=config.LOG_LEVEL.upper(),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )
    logger.info("Starting Aunt Polly Bot")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
