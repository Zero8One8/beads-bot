"""
Управление сайтом через Supabase site_content.
"""
import json
import logging
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


SITE_CONTENT_SECTIONS: dict[str, dict[str, Any]] = {
    "site_links": {
        "label": "Ссылки",
        "description": "Telegram, бот, мастер, Instagram",
        "template": {
            "botUrl": "https://t.me/Themagicofstonesbot",
            "telegramChannelUrl": "https://t.me/Magic_ofstone",
            "telegramChatUrl": "https://t.me/magicstonechat",
            "masterTelegramUrl": "https://t.me/SvetozarAdidev",
            "instagramUrl": "https://instagram.com/magic.ofstone",
        },
    },
    "site_shop_products": {
        "label": "Товары сайта",
        "description": "Магазин: botUrl, bracelets, rosaries, candles",
        "template": {
            "botUrl": "https://t.me/Themagicofstonesbot",
            "bracelets": [],
            "rosaries": [],
            "candles": [],
        },
    },
    "site_services": {
        "label": "Услуги",
        "description": "Список услуг, цены, CTA, ссылки",
        "template": [
            {
                "icon": "Eye",
                "title": "Индивидуальная диагностика",
                "price": "5 000 ₽",
                "priceRub": 5000,
                "orderSlug": "diagnostika",
                "description": "Описание услуги",
                "includes": ["Пункт 1", "Пункт 2"],
                "cta": "Оплатить и записаться",
                "link": None,
                "secondaryCta": None,
                "secondaryLink": None,
                "featured": True,
            }
        ],
    },
    "site_faq": {
        "label": "FAQ",
        "description": "Категории и вопросы/ответы",
        "template": [
            {
                "category": "О камнях",
                "items": [
                    {
                        "q": "Вопрос?",
                        "a": "Ответ",
                    }
                ],
            }
        ],
    },
    "site_blog": {
        "label": "Статьи",
        "description": "Список статей и CTA-блок блога",
        "template": {
            "articles": [
                {
                    "slug": "example-article",
                    "title": "Заголовок",
                    "excerpt": "Короткое описание",
                    "readTime": "5 мин",
                    "category": "Категория",
                    "content": [
                        {"type": "p", "text": "Абзац"},
                        {"type": "h2", "text": "Подзаголовок"},
                    ],
                }
            ],
            "cta": {
                "title": "Хотите узнать, какие камни подойдут именно вам?",
                "description": "Пройдите бесплатный квиз или запишитесь на индивидуальную диагностику",
                "quizButtonText": "Пройти квиз",
                "diagnosticButtonText": "Диагностика мастера",
            },
        },
    },
    "site_crystal_of_day": {
        "label": "Блок камня дня",
        "description": "Текст кнопки, ссылка и режим auto/manual",
        "template": {
            "label": "Камень дня",
            "telegramButtonText": "Камень дня в Telegram",
            "telegramUrl": "https://t.me/Themagicofstonesbot?start=daily_stone",
            "mode": "auto",
            "manualCrystalName": None,
        },
    },
}


class SiteContentClient:
    @staticmethod
    def is_configured() -> bool:
        return bool(Config.SUPABASE_URL and Config.SUPABASE_SERVICE_ROLE_KEY)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {Config.SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": Config.SUPABASE_SERVICE_ROLE_KEY,
            "Content-Type": "application/json",
        }

    @classmethod
    async def get_content(cls, content_key: str):
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{Config.SUPABASE_URL.rstrip('/')}/rest/v1/site_content",
                headers=cls._headers(),
                params={
                    "content_key": f"eq.{content_key}",
                    "select": "content,updated_at,updated_by,is_active",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if rows else None

    @classmethod
    async def upsert_content(cls, content_key: str, content: Any, updated_by: str):
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        headers = cls._headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        payload = {
            "content_key": content_key,
            "content": content,
            "is_active": True,
            "updated_by": updated_by,
            "description": SITE_CONTENT_SECTIONS.get(content_key, {}).get("description", ""),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{Config.SUPABASE_URL.rstrip('/')}/rest/v1/site_content",
                headers=headers,
                content=json.dumps(payload, ensure_ascii=False),
            )
            response.raise_for_status()
            return response.json()