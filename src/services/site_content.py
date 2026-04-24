"""
Управление сайтом через Supabase site_content.
"""
import json
import logging
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_content(content_key: str, content: Any) -> list[str]:
    """Проверяет структуру content для заданной секции.
    Возвращает список ошибок (пустой — если всё ок).
    """
    errors: list[str] = []

    if content_key == "site_links":
        if not isinstance(content, dict):
            return [f"Ожидается объект (dict), получен {type(content).__name__}"]
        for field in ["botUrl", "telegramChannelUrl", "telegramChatUrl", "masterTelegramUrl", "instagramUrl"]:
            if field not in content:
                errors.append(f"Поле '{field}' обязательно")
            elif not isinstance(content[field], str):
                errors.append(f"Поле '{field}' должно быть строкой")

    elif content_key == "site_shop_products":
        if not isinstance(content, dict):
            return [f"Ожидается объект (dict), получен {type(content).__name__}"]
        if "botUrl" not in content:
            errors.append("Поле 'botUrl' обязательно")
        for field in ["bracelets", "rosaries", "candles"]:
            if field not in content:
                errors.append(f"Поле '{field}' обязательно")
            elif not isinstance(content[field], list):
                errors.append(f"Поле '{field}' должно быть массивом")

    elif content_key == "site_services":
        if not isinstance(content, list):
            return [f"Ожидается массив (list), получен {type(content).__name__}"]
        for i, item in enumerate(content):
            if not isinstance(item, dict):
                errors.append(f"Элемент [{i}]: ожидается объект")
                continue
            for field in ["icon", "title", "price", "priceRub", "orderSlug", "cta"]:
                if field not in item:
                    errors.append(f"Элемент [{i}]: поле '{field}' обязательно")

    elif content_key == "site_faq":
        if not isinstance(content, list):
            return [f"Ожидается массив (list), получен {type(content).__name__}"]
        for i, cat in enumerate(content):
            if not isinstance(cat, dict):
                errors.append(f"Элемент [{i}]: ожидается объект")
                continue
            if "category" not in cat:
                errors.append(f"Элемент [{i}]: поле 'category' обязательно")
            items = cat.get("items")
            if not isinstance(items, list):
                errors.append(f"Элемент [{i}]: поле 'items' должно быть массивом")
            else:
                for j, item in enumerate(items):
                    if not isinstance(item, dict) or "q" not in item or "a" not in item:
                        errors.append(f"Элемент [{i}].items[{j}]: нужны поля 'q' и 'a'")

    elif content_key == "site_blog":
        if not isinstance(content, dict):
            return [f"Ожидается объект (dict), получен {type(content).__name__}"]
        if not isinstance(content.get("articles"), list):
            errors.append("Поле 'articles' должно быть массивом")
        cta = content.get("cta")
        if not isinstance(cta, dict):
            errors.append("Поле 'cta' должно быть объектом")
        else:
            for field in ["title", "description", "quizButtonText", "diagnosticButtonText"]:
                if field not in cta:
                    errors.append(f"cta.{field}: поле обязательно")

    elif content_key == "site_crystal_of_day":
        if not isinstance(content, dict):
            return [f"Ожидается объект (dict), получен {type(content).__name__}"]
        for field in ["label", "telegramButtonText", "telegramUrl", "mode"]:
            if field not in content:
                errors.append(f"Поле '{field}' обязательно")
        if content.get("mode") not in ("auto", "manual"):
            errors.append("Поле 'mode' должно быть 'auto' или 'manual'")

    return errors


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
    def _base_url(cls) -> str:
        return Config.SUPABASE_URL.rstrip("/")

    @classmethod
    async def get_content(cls, content_key: str):
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{cls._base_url()}/rest/v1/site_content",
                headers=cls._headers(),
                params={
                    "content_key": f"eq.{content_key}",
                    "select": "content,updated_at,updated_by,is_active,draft_content,draft_updated_at,draft_updated_by",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if rows else None

    @classmethod
    async def _save_to_history(cls, client, content_key: str, old_content: Any, saved_by: str):
        """Сохраняет старое значение content в историю версий."""
        hist_headers = cls._headers()
        hist_headers["Prefer"] = "return=minimal"
        payload = {
            "content_key": content_key,
            "content": old_content,
            "saved_by": saved_by,
        }
        try:
            resp = await client.post(
                f"{cls._base_url()}/rest/v1/site_content_history",
                headers=hist_headers,
                content=json.dumps(payload, ensure_ascii=False),
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to save history for %s: %s", content_key, exc)

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
            # Сохраняем старое значение в историю перед перезаписью
            try:
                existing = await cls.get_content(content_key)
                if existing and existing.get("content"):
                    await cls._save_to_history(client, content_key, existing["content"], updated_by)
            except Exception as exc:
                logger.warning("Could not read existing content for history: %s", exc)

            response = await client.post(
                f"{cls._base_url()}/rest/v1/site_content",
                headers=headers,
                params={"on_conflict": "content_key"},
                content=json.dumps(payload, ensure_ascii=False),
            )
            response.raise_for_status()
            return response.json()

    @classmethod
    async def save_draft(cls, content_key: str, content: Any, updated_by: str):
        """Сохраняет черновик (draft_content) без публикации."""
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        # Сначала убеждаемся, что строка существует (upsert основного контента не меняем)
        existing = await cls.get_content(content_key)
        if not existing:
            # Создаём строку с шаблоном как текущим контентом
            template = SITE_CONTENT_SECTIONS.get(content_key, {}).get("template", {})
            await cls.upsert_content(content_key, template, updated_by)

        patch_headers = cls._headers()
        patch_headers["Prefer"] = "return=minimal"

        patch_payload = {
            "draft_content": content,
            "draft_updated_by": updated_by,
            "draft_updated_at": "now()",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{cls._base_url()}/rest/v1/site_content",
                headers=patch_headers,
                params={"content_key": f"eq.{content_key}"},
                content=json.dumps(patch_payload, ensure_ascii=False),
            )
            response.raise_for_status()

    @classmethod
    async def publish_draft(cls, content_key: str, updated_by: str):
        """Публикует черновик: копирует draft_content → content, очищает черновик."""
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        row = await cls.get_content(content_key)
        if not row or not row.get("draft_content"):
            raise ValueError("Нет черновика для публикации")

        draft = row["draft_content"]
        # Публикуем через upsert (он сам сохранит в историю)
        await cls.upsert_content(content_key, draft, updated_by)

        # Очищаем черновик
        import httpx

        patch_headers = cls._headers()
        patch_headers["Prefer"] = "return=minimal"
        patch_payload = {"draft_content": None, "draft_updated_by": None, "draft_updated_at": None}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{cls._base_url()}/rest/v1/site_content",
                headers=patch_headers,
                params={"content_key": f"eq.{content_key}"},
                content=json.dumps(patch_payload, ensure_ascii=False),
            )
            response.raise_for_status()

    @classmethod
    async def get_history(cls, content_key: str, limit: int = 5) -> list[dict]:
        """Возвращает последние N версий из истории."""
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{cls._base_url()}/rest/v1/site_content_history",
                headers=cls._headers(),
                params={
                    "content_key": f"eq.{content_key}",
                    "select": "id,saved_at,saved_by",
                    "order": "saved_at.desc",
                    "limit": str(limit),
                },
            )
            response.raise_for_status()
            return response.json()

    @classmethod
    async def rollback_to(cls, history_id: str, content_key: str, updated_by: str):
        """Откатывает секцию к версии из истории."""
        if not cls.is_configured():
            raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY не настроены")

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            # Получаем нужную версию
            response = await client.get(
                f"{cls._base_url()}/rest/v1/site_content_history",
                headers=cls._headers(),
                params={
                    "id": f"eq.{history_id}",
                    "select": "content,content_key",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()

        if not rows:
            raise ValueError(f"Версия {history_id} не найдена")
        if rows[0].get("content_key") != content_key:
            raise ValueError("История принадлежит другой секции")

        await cls.upsert_content(content_key, rows[0]["content"], updated_by)