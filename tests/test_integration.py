"""
E2E интеграционный тест: проверяет связку бот → Supabase → сайт.

Запуск:
    python tests/test_integration.py

Для прохождения теста нужны переменные окружения SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY
(берутся из .env в корне репозитория).

Тест:
1. Создаёт тестовую запись в site_content
2. Читает её обратно и проверяет значение
3. Обновляет (upsert) и проверяет изменение
4. Сохраняет черновик и проверяет draft_content
5. Публикует черновик и проверяет, что content обновился
6. Проверяет историю версий (site_content_history)
7. Откатывает к предыдущей версии через историю
8. Очищает все тестовые данные
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Поддержка запуска из любой папки
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # dotenv не обязателен

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
TEST_KEY = "_e2e_test_section"
PASSED = []
FAILED = []


def ok(name: str):
    PASSED.append(name)
    print(f"  ✅ {name}")


def fail(name: str, detail: str):
    FAILED.append(name)
    print(f"  ❌ {name}: {detail}")


def headers(extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


async def run_tests():
    if not SUPABASE_URL or not SERVICE_KEY:
        print("❌ Переменные SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY не заданы в .env")
        sys.exit(1)

    print(f"🔗 Supabase: {SUPABASE_URL}")
    print(f"🔑 Service key: {SERVICE_KEY[:20]}...")
    print()

    async with httpx.AsyncClient(timeout=30) as client:

        # ------------------------------------------------------------------
        # 1. Upsert тестовой записи
        # ------------------------------------------------------------------
        print("1. Создание тестовой записи...")
        initial_content = {"test": True, "value": "initial"}
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers({"Prefer": "resolution=merge-duplicates,return=representation"}),
            params={"on_conflict": "content_key"},
            content=json.dumps({
                "content_key": TEST_KEY,
                "content": initial_content,
                "is_active": True,
                "updated_by": "e2e_test",
            }),
        )
        if r.status_code in (200, 201):
            ok("Upsert тестовой записи")
        else:
            fail("Upsert тестовой записи", f"HTTP {r.status_code}: {r.text[:200]}")

        # ------------------------------------------------------------------
        # 2. Чтение записи
        # ------------------------------------------------------------------
        print("2. Чтение записи...")
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers(),
            params={
                "content_key": f"eq.{TEST_KEY}",
                "select": "content",
                "limit": "1",
            },
        )
        rows = r.json() if r.status_code == 200 else []
        if rows and rows[0].get("content") == initial_content:
            ok("Чтение записи (значение совпадает)")
        else:
            fail("Чтение записи", f"Получено: {rows}")

        # ------------------------------------------------------------------
        # 3. Обновление через upsert
        # ------------------------------------------------------------------
        print("3. Обновление записи...")
        updated_content = {"test": True, "value": "updated"}
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers({"Prefer": "resolution=merge-duplicates,return=representation"}),
            params={"on_conflict": "content_key"},
            content=json.dumps({
                "content_key": TEST_KEY,
                "content": updated_content,
                "is_active": True,
                "updated_by": "e2e_test_update",
            }),
        )
        if r.status_code in (200, 201):
            ok("Обновление через upsert")
        else:
            fail("Обновление через upsert", f"HTTP {r.status_code}: {r.text[:200]}")

        # ------------------------------------------------------------------
        # 4. Сохранение черновика
        # ------------------------------------------------------------------
        print("4. Сохранение черновика...")
        draft_content = {"test": True, "value": "draft"}
        r = await client.patch(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers({"Prefer": "return=minimal"}),
            params={"content_key": f"eq.{TEST_KEY}"},
            content=json.dumps({
                "draft_content": draft_content,
                "draft_updated_by": "e2e_test_draft",
            }),
        )
        if r.status_code in (200, 204):
            ok("Сохранение черновика (PATCH)")
        else:
            fail("Сохранение черновика", f"HTTP {r.status_code}: {r.text[:200]}")

        # Читаем draft_content
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers(),
            params={"content_key": f"eq.{TEST_KEY}", "select": "content,draft_content", "limit": "1"},
        )
        rows = r.json() if r.status_code == 200 else []
        if rows and rows[0].get("draft_content") == draft_content:
            ok("Чтение черновика (значение совпадает)")
        else:
            fail("Чтение черновика", f"Получено: {rows}")

        # ------------------------------------------------------------------
        # 5. Публикация черновика (эмулируем publish_draft: patch content = draft, clear draft)
        # ------------------------------------------------------------------
        print("5. Публикация черновика...")
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers({"Prefer": "resolution=merge-duplicates,return=representation"}),
            params={"on_conflict": "content_key"},
            content=json.dumps({
                "content_key": TEST_KEY,
                "content": draft_content,
                "is_active": True,
                "updated_by": "e2e_test_publish",
            }),
        )
        if r.status_code in (200, 201):
            ok("Публикация черновика (upsert)")
        else:
            fail("Публикация черновика", f"HTTP {r.status_code}: {r.text[:200]}")
        # Проверяем что content == draft_content
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers(),
            params={"content_key": f"eq.{TEST_KEY}", "select": "content", "limit": "1"},
        )
        rows = r.json() if r.status_code == 200 else []
        if rows and rows[0].get("content") == draft_content:
            ok("Контент обновлён после публикации черновика")
        else:
            fail("Контент после публикации черновика", f"Получено: {rows}")

        # ------------------------------------------------------------------
        # 6. История версий
        # ------------------------------------------------------------------
        print("6. История версий...")
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/site_content_history",
            headers=headers(),
            params={
                "content_key": f"eq.{TEST_KEY}",
                "select": "id,saved_at,saved_by,content",
                "order": "saved_at.desc",
                "limit": "10",
            },
        )
        history = r.json() if r.status_code == 200 else []
        if r.status_code == 200:
            ok(f"Чтение истории (найдено {len(history)} записей)")
        else:
            fail("Чтение истории", f"HTTP {r.status_code}: {r.text[:200]}")

        # ------------------------------------------------------------------
        # 7. Откат (если есть история)
        # ------------------------------------------------------------------
        if history:
            print("7. Откат к предыдущей версии...")
            rollback_version = history[0]
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/site_content",
                headers=headers({"Prefer": "resolution=merge-duplicates,return=representation"}),
                params={"on_conflict": "content_key"},
                content=json.dumps({
                    "content_key": TEST_KEY,
                    "content": rollback_version["content"],
                    "is_active": True,
                    "updated_by": "e2e_test_rollback",
                }),
            )
            if r.status_code in (200, 201):
                ok("Откат к версии из истории")
            else:
                fail("Откат", f"HTTP {r.status_code}: {r.text[:200]}")
        else:
            print("7. Откат — пропуск (история пуста)")

        # ------------------------------------------------------------------
        # 8. Очистка тестовых данных
        # ------------------------------------------------------------------
        print("8. Очистка тестовых данных...")
        r1 = await client.delete(
            f"{SUPABASE_URL}/rest/v1/site_content",
            headers=headers(),
            params={"content_key": f"eq.{TEST_KEY}"},
        )
        r2 = await client.delete(
            f"{SUPABASE_URL}/rest/v1/site_content_history",
            headers=headers(),
            params={"content_key": f"eq.{TEST_KEY}"},
        )
        if r1.status_code in (200, 204) and r2.status_code in (200, 204):
            ok("Очистка тестовых данных")
        else:
            fail("Очистка", f"site_content: {r1.status_code}, history: {r2.status_code}")

    # ------------------------------------------------------------------
    # Итог
    # ------------------------------------------------------------------
    print()
    print(f"{'=' * 50}")
    print(f"Результат: {len(PASSED)} пройдено, {len(FAILED)} провалено")
    if FAILED:
        print(f"Провалено: {', '.join(FAILED)}")
        sys.exit(1)
    else:
        print("🎉 Все тесты прошли!")


if __name__ == "__main__":
    asyncio.run(run_tests())
