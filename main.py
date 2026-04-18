"""
Главный файл запуска бота.
Объединяет все роутеры и запускает polling.
"""
import asyncio
import logging
import os
import signal
import socket
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramConflictError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from src.config import Config
from src.database.db import db
from src.database.init import init_db
from src.database.seed_content import run_all_content_seeds
from src.utils.text_loader import ContentLoader
from src.middlewares.rate_limit import RateLimitMiddleware

# Импортируем все роутеры
from src.handlers import user
from src.handlers import shop
from src.handlers import diagnostic
from src.handlers import workouts
from src.handlers import services
from src.handlers import gifts
from src.handlers import wishlist
from src.handlers import faq
from src.handlers import stories
from src.handlers import payment
from src.handlers import admin
from src.handlers import admin_diagnostic
from src.handlers import admin_products
from src.handlers import admin_promos
from src.handlers import admin_services
from src.handlers import admin_broadcast
from src.handlers import admin_stats
from src.handlers import admin_orders
from src.handlers import admin_export
from src.handlers import admin_scheduler
from src.handlers import admin_settings
from src.handlers.admin_content import router as admin_content_router
from src.handlers.knowledge import router as knowledge_router
from src.handlers import daily_stone
from src.handlers import selector
from src.handlers import compatibility
from src.handlers import profile
from src.handlers import search
from src.handlers.admin_stones import router as admin_stones_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def env_bool(name: str, default: bool) -> bool:
    """Читает bool из env с безопасным значением по умолчанию."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())
polling_conflict_detected = False
background_task: asyncio.Task | None = None
polling_lock_task: asyncio.Task | None = None
POLLING_LOCK_NAME = "telegram_polling"
POLLING_LOCK_OWNER = f"{socket.gethostname()}:{os.getpid()}"

# Регистрируем middleware
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())


@dp.errors()
async def handle_dispatcher_errors(event: ErrorEvent):
    """Останавливает polling при конфликте, чтобы не спамить бесконечными retry."""
    global polling_conflict_detected
    if isinstance(event.exception, TelegramConflictError):
        polling_conflict_detected = True
        logger.error(
            "❌ Конфликт Telegram getUpdates: обнаружен другой polling-инстанс. "
            "Останавливаю polling и перевожу процесс в пассивный режим."
        )
        await dp.stop_polling()


def try_acquire_polling_lock() -> bool:
    """Пытается захватить lock poller в общей БД, чтобы не запускать второй getUpdates."""
    with db.cursor() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_locks (
                lock_name TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            INSERT INTO runtime_locks (lock_name, owner, heartbeat_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(lock_name) DO NOTHING
            """,
            (POLLING_LOCK_NAME, POLLING_LOCK_OWNER),
        )
        c.execute(
            "SELECT owner FROM runtime_locks WHERE lock_name = ?",
            (POLLING_LOCK_NAME,),
        )
        row = c.fetchone()
        return bool(row and row["owner"] == POLLING_LOCK_OWNER)


async def polling_lock_heartbeat():
    """Обновляет heartbeat lock для активного poller-инстанса."""
    while True:
        try:
            with db.cursor() as c:
                c.execute(
                    """
                    UPDATE runtime_locks
                    SET heartbeat_at = datetime('now')
                    WHERE lock_name = ? AND owner = ?
                    """,
                    (POLLING_LOCK_NAME, POLLING_LOCK_OWNER),
                )
        except Exception as e:
            logger.warning("Не удалось обновить heartbeat poller lock: %s", e)
        await asyncio.sleep(30)


def release_polling_lock():
    """Освобождает lock poller текущего инстанса."""
    try:
        with db.cursor() as c:
            c.execute(
                "DELETE FROM runtime_locks WHERE lock_name = ? AND owner = ?",
                (POLLING_LOCK_NAME, POLLING_LOCK_OWNER),
            )
    except Exception as e:
        logger.warning("Не удалось освободить poller lock: %s", e)

# Регистрируем все роутеры
dp.include_router(user.router)
dp.include_router(shop.router)
dp.include_router(diagnostic.router)
dp.include_router(workouts.router)
dp.include_router(services.router)
dp.include_router(gifts.router)
dp.include_router(wishlist.router)
dp.include_router(faq.router)
dp.include_router(stories.router)
dp.include_router(payment.router)
dp.include_router(admin.router)
dp.include_router(admin_diagnostic.router)
dp.include_router(admin_products.router)
dp.include_router(admin_promos.router)
dp.include_router(admin_services.router)
dp.include_router(admin_broadcast.router)
dp.include_router(admin_stats.router)
dp.include_router(admin_orders.router)
dp.include_router(admin_export.router)
dp.include_router(admin_scheduler.router)
dp.include_router(admin_settings.router)
dp.include_router(knowledge_router)
dp.include_router(daily_stone.router)
dp.include_router(selector.router)
dp.include_router(compatibility.router)
dp.include_router(profile.router)
dp.include_router(search.router)
dp.include_router(admin_content_router)
dp.include_router(admin_stones_router)

# Фоновые задачи
async def background_tasks():
    """Фоновые задачи."""
    from src.services.background import (
        check_pending_orders,
        check_birthdays,
        send_daily_stone,
        check_cart_reminders,
        check_reactivation,
        send_review_requests,
        send_birthday_promos
    )
    await asyncio.gather(
        check_pending_orders(),
        check_birthdays(),
        send_daily_stone(bot),
        check_cart_reminders(bot),
        check_reactivation(bot),
        send_review_requests(bot),
        send_birthday_promos(bot),
        return_exceptions=True
    )

async def on_startup(enable_web: bool):
    global background_task
    logger.info("="*50)
    logger.info("🚀 ЗАПУСК БОТА MAGIC STONES V6.0")
    logger.info("="*50)

    # Директории/проверки конфигурации должны выполняться перед подключением к БД и лог-файлами.
    Config.validate()
    log_path = Config.STORAGE_PATH / 'bot.log'
    root_logger = logging.getLogger()
    already_has_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(log_path)
        for h in root_logger.handlers
    )
    if not already_has_file:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)
    
    # Инициализация БД
    init_db()
    logger.info("✅ База данных инициализирована")
    
    # Заполняем данные по умолчанию
    run_all_content_seeds()
    logger.info("✅ Начальные данные загружены")
    
    # Предзагрузка контента
    stones = ContentLoader.load_all_stones()
    logger.info(f"📚 Загружено камней: {len(stones)}")
    
    # Запуск фоновых задач
    background_task = asyncio.create_task(background_tasks())

    # Запуск веб-сервера
    web_port = int(os.getenv('PORT', 8080))
    if enable_web:
        from web.app import create_web_app
        from aiohttp import web as aio_web
        web_app = create_web_app()
        runner = aio_web.AppRunner(web_app)
        await runner.setup()
        site = aio_web.TCPSite(runner, '0.0.0.0', web_port)
        await site.start()
        logger.info(f"✅ Веб-сервер запущен на порту {web_port}")
    
    logger.info("✅ Бот готов к работе")

async def on_shutdown():
    global background_task, polling_lock_task
    logger.info("🛑 Остановка бота...")

    if polling_lock_task and not polling_lock_task.done():
        polling_lock_task.cancel()
        try:
            await polling_lock_task
        except asyncio.CancelledError:
            pass
        polling_lock_task = None

    if background_task and not background_task.done():
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        background_task = None

    release_polling_lock()
    db.close()
    logger.info("👋 Все соединения закрыты")

async def main():
    global polling_lock_task
    role = os.getenv('ROLE', '').strip().lower()

    if role == 'web':
        default_enable_web = True
        default_enable_polling = False
    elif role == 'bot':
        default_enable_web = False
        default_enable_polling = True
    else:
        default_enable_web = True
        default_enable_polling = True

    enable_web = env_bool('ENABLE_WEB', default_enable_web)
    enable_polling = env_bool('ENABLE_POLLING', default_enable_polling)

    if role == 'web' and enable_polling:
        logger.warning("ROLE=web: принудительно отключаю polling (ENABLE_POLLING игнорируется).")
        enable_polling = False

    # Webhook-режим — если задан WEBHOOK_URL, используем его вместо polling.
    # Telegram сам присылает обновления на URL, конфликт инстансов невозможен.
    webhook_url = Config.WEBHOOK_URL
    use_webhook = bool(webhook_url) and enable_polling

    logger.info(
        "⚙️ Режим запуска: ROLE=%s, ENABLE_WEB=%s, ENABLE_POLLING=%s, WEBHOOK=%s",
        role or 'auto',
        enable_web,
        enable_polling,
        webhook_url or 'нет (используется polling)',
    )

    await on_startup(enable_web)
    try:
        if not enable_polling:
            logger.warning("⏸️ Polling/webhook отключен. Инстанс работает без Telegram getUpdates.")
            while True:
                await asyncio.sleep(3600)

        if use_webhook:
            # ── WEBHOOK MODE ──────────────────────────────────────────────
            # Конфликт двух инстансов невозможен: Telegram шлёт обновления
            # на URL, а не оба инстанса тянут их сами.
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web as aio_web

            full_webhook_url = webhook_url + Config.WEBHOOK_PATH

            # Выставляем webhook в Telegram
            await bot.set_webhook(
                url=full_webhook_url,
                secret_token=Config.WEBHOOK_SECRET or None,
                drop_pending_updates=True,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "pre_checkout_query",
                    "successful_payment",
                ],
            )
            logger.info(f"✅ Webhook установлен: {full_webhook_url}")

            # Если веб-сервер уже запущен в on_startup — добавляем к нему handler.
            # Если нет — поднимаем отдельный.
            if not enable_web:
                web_port = int(os.getenv('PORT', 8080))
                app = aio_web.Application()
                SimpleRequestHandler(
                    dispatcher=dp,
                    bot=bot,
                    secret_token=Config.WEBHOOK_SECRET or None,
                ).register(app, path=Config.WEBHOOK_PATH)
                setup_application(app, dp, bot=bot)
                runner = aio_web.AppRunner(app)
                await runner.setup()
                site = aio_web.TCPSite(runner, '0.0.0.0', web_port)
                await site.start()
                logger.info(f"✅ Webhook-сервер запущен на порту {web_port}")
                # Ждём SIGTERM
                stop_event = asyncio.Event()
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    try:
                        loop.add_signal_handler(sig, stop_event.set)
                    except (NotImplementedError, OSError):
                        pass
                await stop_event.wait()
                await runner.cleanup()
            else:
                # Веб-сервер уже запущен — регистрируем handler на его app
                # через startup: получаем app из глобального runner
                from web.app import create_web_app
                from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
                from aiohttp import web as aio_web

                app = create_web_app()
                SimpleRequestHandler(
                    dispatcher=dp,
                    bot=bot,
                    secret_token=Config.WEBHOOK_SECRET or None,
                ).register(app, path=Config.WEBHOOK_PATH)

                web_port = int(os.getenv('PORT', 8080))
                runner = aio_web.AppRunner(app)
                await runner.setup()
                site = aio_web.TCPSite(runner, '0.0.0.0', web_port)
                await site.start()
                logger.info(f"✅ Webhook+Web сервер запущен на порту {web_port}")

                stop_event = asyncio.Event()
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    try:
                        loop.add_signal_handler(sig, stop_event.set)
                    except (NotImplementedError, OSError):
                        pass
                await stop_event.wait()
                await runner.cleanup()
        else:
            # ── POLLING MODE (fallback) ───────────────────────────────────
            if not try_acquire_polling_lock():
                logger.warning("⏸️ Polling lock уже занят. Этот инстанс не запускает getUpdates.")
                while True:
                    await asyncio.sleep(3600)

            polling_lock_task = asyncio.create_task(polling_lock_heartbeat())

            loop = asyncio.get_running_loop()
            stop_event = asyncio.Event()

            def _on_stop_signal():
                logger.info("⛔ Получен сигнал завершения — останавливаю polling немедленно.")
                stop_event.set()

            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, _on_stop_signal)
                except (NotImplementedError, OSError):
                    pass

            await bot.delete_webhook(drop_pending_updates=True)

            polling_task = asyncio.create_task(
                dp.start_polling(bot, handle_signals=False)
            )
            stop_task = asyncio.create_task(stop_event.wait())

            done, pending = await asyncio.wait(
                [polling_task, stop_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            if stop_event.is_set():
                logger.info("⛔ Polling остановлен по сигналу. Завершаю процесс.")
            elif polling_conflict_detected:
                logger.warning("⏸️ После конфликта polling остановлен, инстанс завершает работу.")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {e}")