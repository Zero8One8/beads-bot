"""
Главный файл запуска бота.
Объединяет все роутеры и запускает polling.
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import Config
from src.database.db import db
from src.database.init import init_db
from src.database.seed_quiz import run_all_seeds
from src.database.seed_content import run_all_content_seeds
from src.utils.text_loader import ContentLoader
from src.middlewares.rate_limit import RateLimitMiddleware

# Импортируем все роутеры
from src.handlers import user
from src.handlers import shop
from src.handlers import diagnostic
from src.handlers import custom_order
from src.handlers import music
from src.handlers import workouts
from src.handlers import services
from src.handlers import gifts
from src.handlers import wishlist
from src.handlers import faq
from src.handlers import quiz
from src.handlers import stories
from src.handlers import club
from src.handlers import payment
from src.handlers import admin
from src.handlers import admin_diagnostic
from src.handlers import admin_products
from src.handlers import admin_promos
from src.handlers import admin_services
from src.handlers import admin_club
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
from src.handlers import ai_consult
from src.handlers import streak
from src.handlers import wishmap
from src.handlers import compatibility
from src.handlers import profile
from src.handlers import search
from src.handlers import marathon
from src.handlers import astro_advice
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

bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

# Регистрируем middleware
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())

# Регистрируем все роутеры
dp.include_router(user.router)
dp.include_router(shop.router)
dp.include_router(diagnostic.router)
dp.include_router(custom_order.router)
dp.include_router(music.router)
dp.include_router(workouts.router)
dp.include_router(services.router)
dp.include_router(gifts.router)
dp.include_router(wishlist.router)
dp.include_router(faq.router)
dp.include_router(quiz.router)
dp.include_router(stories.router)
dp.include_router(club.router)
dp.include_router(payment.router)
dp.include_router(admin.router)
dp.include_router(admin_diagnostic.router)
dp.include_router(admin_products.router)
dp.include_router(admin_promos.router)
dp.include_router(admin_services.router)
dp.include_router(admin_club.router)
dp.include_router(admin_broadcast.router)
dp.include_router(admin_stats.router)
dp.include_router(admin_orders.router)
dp.include_router(admin_export.router)
dp.include_router(admin_scheduler.router)
dp.include_router(admin_settings.router)
dp.include_router(knowledge_router)
dp.include_router(daily_stone.router)
dp.include_router(selector.router)
dp.include_router(ai_consult.router)
dp.include_router(streak.router)
dp.include_router(wishmap.router)
dp.include_router(compatibility.router)
dp.include_router(profile.router)
dp.include_router(search.router)
dp.include_router(marathon.router)
dp.include_router(astro_advice.router)
dp.include_router(admin_content_router)
dp.include_router(admin_stones_router)

# Фоновые задачи
async def background_tasks():
    """Фоновые задачи."""
    from src.services.background import (
        check_pending_orders,
        check_birthdays,
        check_expired_subscriptions,
        send_daily_stone,
        check_cart_reminders,
        check_reactivation,
        send_monday_astro,
        send_review_requests,
        send_birthday_promos
    )
    await asyncio.gather(
        check_pending_orders(),
        check_birthdays(),
        check_expired_subscriptions(),
        send_daily_stone(bot),
        check_cart_reminders(bot),
        check_reactivation(bot),
        send_monday_astro(bot),
        send_review_requests(bot),
        send_birthday_promos(bot),
        return_exceptions=True
    )

async def on_startup():
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
    run_all_seeds()
    run_all_content_seeds()
    logger.info("✅ Начальные данные загружены")
    
    # Предзагрузка контента
    stones = ContentLoader.load_all_stones()
    logger.info(f"📚 Загружено камней: {len(stones)}")
    
    # Запуск фоновых задач
    asyncio.create_task(background_tasks())

    # Запуск веб-сервера
    web_port = int(os.getenv('PORT', 8080))
    if os.getenv('ENABLE_WEB', '1') == '1':
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
    logger.info("🛑 Остановка бота...")
    db.close_all()
    logger.info("👋 Все соединения закрыты")

async def main():
    await on_startup()
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {e}")