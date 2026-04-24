"""
Исправленная конфигурация с безопасностью
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE)


class Config:
    """Конфигурация приложения с валидацией."""
    
    # Обязательные параметры
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    ADMIN_ID = None
    
    try:
        _admin_id = os.getenv('ADMIN_ID', '0')
        ADMIN_ID = int(_admin_id) if _admin_id and _admin_id != '0' else 0
    except (ValueError, TypeError):
        ADMIN_ID = 0

    # База данных
    db_env = os.getenv('DB', 'data/bot.db')
    if db_env.startswith('/app/'):
        db_env = db_env[len('/app/'):]
    elif db_env.startswith('/'):
        db_env = db_env.lstrip('/')

    DB_PATH = BASE_DIR / db_env
    DATA_DIR = DB_PATH.parent

    # Пути для хранения файлов
    STORAGE_PATH = DATA_DIR / 'storage'
    DIAGNOSTICS_PATH = STORAGE_PATH / 'diagnostics'
    STORIES_PATH = STORAGE_PATH / 'stories'
    PHOTOS_PATH = STORAGE_PATH / 'photos'

    # Контент
    CONTENT_PATH = DATA_DIR / 'content'
    KNOWLEDGE_BASE_PATH = BASE_DIR / 'content' / 'knowledge_base'
    POSTS_PATH = CONTENT_PATH / 'posts'
    CLUB_CONTENT_PATH = CONTENT_PATH / 'club'

    # Webhook (если задан — бот работает через webhook, иначе polling)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '').rstrip('/')
    WEBHOOK_PATH = '/webhook/telegram'
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')

    # Интеграции (опциональные)
    AMOCRM_SUBDOMAIN = os.getenv('AMOCRM_SUBDOMAIN', '')
    AMOCRM_ACCESS_TOKEN = os.getenv('AMOCRM_ACCESS_TOKEN', '')
    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    MASTER_USERNAME = os.getenv('MASTER_USERNAME', 'SvetozarAdidev')
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    try:
        AI_DAILY_LIMIT = int(os.getenv('AI_DAILY_LIMIT', '3'))
    except (ValueError, TypeError):
        AI_DAILY_LIMIT = 3

    @classmethod
    def validate(cls) -> bool:
        """Проверить конфигурацию."""
        if not cls.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN не установлен в переменных окружения")
        
        # Создаём необходимые директории
        dirs = [
            cls.DATA_DIR,
            cls.STORAGE_PATH,
            cls.DIAGNOSTICS_PATH,
            cls.STORIES_PATH,
            cls.PHOTOS_PATH,
            cls.CONTENT_PATH,
            cls.KNOWLEDGE_BASE_PATH,
            cls.POSTS_PATH,
            cls.CLUB_CONTENT_PATH,
            cls.DB_PATH.parent
        ]
        
        for dir_path in dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Не удалось создать директорию {dir_path}: {e}")
        
        return True

    @classmethod
    def get_summary(cls) -> str:
        """Получить сводку конфигурации."""
        return f"""
Config Summary:
  BOT_TOKEN: {'✅ Set' if cls.BOT_TOKEN else '❌ Missing'}
  ADMIN_ID: {cls.ADMIN_ID}
  DB_PATH: {cls.DB_PATH}
  DATA_DIR: {cls.DATA_DIR}
  KNOWLEDGE_BASE: {cls.KNOWLEDGE_BASE_PATH}
"""
