"""
Интеграция с Supabase для pop-up, email-подписки и чата.
Используется на фронтенде для сохранения данных.
"""

import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Supabase конфиги
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
SUPABASE_TABLE_EMAILS = "email_subscriptions"
SUPABASE_TABLE_CHAT = "chat_messages"
SUPABASE_TABLE_QUIZ_LEADS = "quiz_leads"


class SupabaseClient:
    """Упрощённый клиент для работы с Supabase REST API."""
    
    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_KEY):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "apikey": key,
        }
    
    async def insert_email(self, email: str, source: str = "pop-up") -> bool:
        """Сохранить email подписку."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/rest/v1/{SUPABASE_TABLE_EMAILS}",
                    headers=self.headers,
                    json={
                        "email": email,
                        "source": source,
                        "subscribed_at": datetime.utcnow().isoformat(),
                        "active": True,
                    },
                )
                if response.status_code in (200, 201):
                    logger.info(f"✅ Email добавлен: {email}")
                    return True
                logger.error(f"❌ Ошибка: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении email: {e}")
            return False
    
    async def insert_chat_message(self, user_id: str, message: str, email: Optional[str] = None) -> bool:
        """Сохранить сообщение из чата."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/rest/v1/{SUPABASE_TABLE_CHAT}",
                    headers=self.headers,
                    json={
                        "user_id": user_id,
                        "message": message,
                        "email": email,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
                if response.status_code in (200, 201):
                    logger.info(f"✅ Chat message saved from {user_id}")
                    return True
                logger.error(f"❌ Chat error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Chat error: {e}")
            return False
    
    async def insert_quiz_lead(self, email: str, name: Optional[str] = None, quiz_result: Optional[dict] = None) -> bool:
        """Сохранить результат квиза."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.url}/rest/v1/{SUPABASE_TABLE_QUIZ_LEADS}",
                    headers=self.headers,
                    json={
                        "email": email,
                        "name": name,
                        "quiz_result": quiz_result,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
                if response.status_code in (200, 201):
                    logger.info(f"✅ Quiz lead saved: {email}")
                    return True
                logger.error(f"❌ Quiz error: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Quiz error: {e}")
            return False


# Глобальный клиент
supabase = SupabaseClient()


# REST API endpoints для фронтенда

async def setup_supabase_routes(app):
    """Регистрация Supabase routes в FastAPI/Quart приложении."""
    
    @app.post("/api/subscribe-email")
    async def subscribe_email(data: dict):
        """POST endpoint для подписки на email."""
        email = data.get("email", "").strip()
        source = data.get("source", "pop-up")
        
        if not email or "@" not in email:
            return {"success": False, "error": "Invalid email"}
        
        success = await supabase.insert_email(email, source)
        return {"success": success}
    
    @app.post("/api/chat-message")
    async def chat_message(data: dict):
        """POST endpoint для чат-сообщений."""
        user_id = data.get("user_id", f"guest_{datetime.now().timestamp()}")
        message = data.get("message", "").strip()
        email = data.get("email", "").strip() or None
        
        if not message:
            return {"success": False, "error": "Message is empty"}
        
        success = await supabase.insert_chat_message(user_id, message, email)
        return {"success": success}
    
    @app.post("/api/quiz-result")
    async def quiz_result(data: dict):
        """POST endpoint для сохранения результата квиза."""
        email = data.get("email", "").strip()
        name = data.get("name", "").strip() or None
        quiz_result = data.get("result")
        
        if not email or "@" not in email:
            return {"success": False, "error": "Invalid email"}
        
        success = await supabase.insert_quiz_lead(email, name, quiz_result)
        return {"success": success}
