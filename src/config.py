import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE)

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    ADMIN_ID = int(os.getenv('ADMIN_ID', '0')) if os.getenv('ADMIN_ID') else 0

    # База данных — на Volume Railway (/app/data)
    db_env = os.getenv('DB', 'data/bot.db')
    # Docker-путь вида /app/data/... на Windows маппим в локальную директорию проекта.
    if db_env.startswith('/app/'):
        db_env = db_env[len('/app/'):]
    elif db_env.startswith('/'):
        db_env = db_env.lstrip('/')

    DB_PATH = BASE_DIR / db_env
    DATA_DIR = DB_PATH.parent  # /app/data — всё постоянное хранится здесь

    # Фото и файлы пользователей — на Volume, чтобы не теряться при деплое
    STORAGE_PATH = DATA_DIR / 'storage'
    DIAGNOSTICS_PATH = STORAGE_PATH / 'diagnostics'
    STORIES_PATH = STORAGE_PATH / 'stories'
    PHOTOS_PATH = STORAGE_PATH / 'photos'

    # Контент мастера (посты, клуб) — на Volume
    # Камни (knowledge_base) — в коде, они не меняются через бот
    CONTENT_PATH = DATA_DIR / 'content'
    KNOWLEDGE_BASE_PATH = BASE_DIR / 'content' / 'knowledge_base'
    POSTS_PATH = CONTENT_PATH / 'posts'
    CLUB_CONTENT_PATH = CONTENT_PATH / 'club'

    AMOCRM_SUBDOMAIN = os.getenv('AMOCRM_SUBDOMAIN', '')
    AMOCRM_ACCESS_TOKEN = os.getenv('AMOCRM_ACCESS_TOKEN', '')

    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    AI_DAILY_LIMIT = int(os.getenv('AI_DAILY_LIMIT', '3'))

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN не установлен")
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        cls.DIAGNOSTICS_PATH.mkdir(parents=True, exist_ok=True)
        cls.STORIES_PATH.mkdir(parents=True, exist_ok=True)
        cls.PHOTOS_PATH.mkdir(parents=True, exist_ok=True)
        cls.CONTENT_PATH.mkdir(parents=True, exist_ok=True)
        cls.KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        cls.POSTS_PATH.mkdir(parents=True, exist_ok=True)
        cls.CLUB_CONTENT_PATH.mkdir(parents=True, exist_ok=True)
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return True
