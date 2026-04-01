"""
AI-консультация через Google Gemini API.
Бесплатно: 1500 запросов/день на весь бот.
Лимит: 3 запроса в день на одного пользователя (настраивается через AI_DAILY_LIMIT).
"""
import logging
import aiohttp
from datetime import date
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.db import db
from src.config import Config
from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()

SYSTEM_PROMPT = """Ты — опытный мастер литотерапии и энергетических практик.
Твоя задача — выслушать человека и дать глубокий, тёплый, личный совет.

Структура ответа (строго в таком порядке):

1. Краткое отражение ситуации (1-2 предложения — покажи что ты услышал)
2. 2-3 рекомендованных камня с объяснением ПОЧЕМУ именно они (конкретно для этой ситуации)
3. Практический совет — как носить, как работать с камнями
4. Мягкое предложение перейти к диагностике для более глубокой работы

Тон: тёплый, мудрый, без пафоса. Как разговор с опытным наставником.
Длина: не более 350 слов. Только на русском языке.
Не используй заголовки с #. Эмодзи — умеренно, уместно."""


class AIConsultStates(StatesGroup):
    waiting_question = State()


# ──────────────────────────────────────────────────────────────
# ЛИМИТ ЗАПРОСОВ
# ──────────────────────────────────────────────────────────────

def _get_daily_usage(user_id: int) -> int:
    """Сколько запросов использовано сегодня."""
    today = date.today().isoformat()
    with db.cursor() as c:
        c.execute(
            "SELECT count FROM ai_consult_usage WHERE user_id = ? AND usage_date = ?",
            (user_id, today)
        )
        row = c.fetchone()
    return row['count'] if row else 0


def _increment_usage(user_id: int):
    """Увеличить счётчик использований на 1."""
    today = date.today().isoformat()
    with db.cursor() as c:
        c.execute("""
            INSERT INTO ai_consult_usage (user_id, usage_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1
        """, (user_id, today))


# ──────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ai_consult")
async def ai_consult_start(callback: CallbackQuery, state: FSMContext):
    """Начало AI-консультации — проверяем лимит."""
    user_id = callback.from_user.id
    limit = Config.AI_DAILY_LIMIT
    used = _get_daily_usage(user_id)

    if used >= limit:
        await callback.message.edit_text(
            "🔮 *СОВЕТ МАСТЕРА*\n\n"
            f"На сегодня ты использовал все {limit} бесплатных консультации.\n\n"
            "Завтра счётчик обнулится и можно будет спросить снова.\n\n"
            "_Хочешь более глубокой работы прямо сейчас?_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🩺 ДИАГНОСТИКА", callback_data="diagnostic")],
                [InlineKeyboardButton(text="📞 НАПИСАТЬ МАСТЕРУ", callback_data="contact_master")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
        await callback.answer()
        return

    remaining = limit - used
    await state.set_state(AIConsultStates.waiting_question)

    await callback.message.edit_text(
        "🔮 *СОВЕТ МАСТЕРА*\n\n"
        "Опиши своё состояние, ситуацию или запрос — одним сообщением.\n\n"
        "Пиши как есть, без выбора из списка:\n"
        "_«Я в постоянном стрессе, не могу успокоиться, ночью не сплю»_\n"
        "_«Хочу привлечь деньги, застряла в одной точке уже год»_\n"
        "_«Ищу защиту от человека который мне вредит»_\n\n"
        f"💬 Осталось консультаций сегодня: *{remaining} из {limit}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← ОТМЕНА", callback_data="menu")]
        ])
    )
    await callback.answer()


@router.message(AIConsultStates.waiting_question)
async def ai_consult_process(message: Message, state: FSMContext):
    """Обработка запроса через Gemini API."""
    await state.clear()
    user_id = message.from_user.id
    user_text = message.text.strip() if message.text else ""

    if len(user_text) < 10:
        await message.answer(
            "Напиши чуть подробнее — чем больше расскажешь, тем точнее совет 🙏",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")]
            ])
        )
        return

    # Повторная проверка лимита (защита от гонки)
    limit = Config.AI_DAILY_LIMIT
    if _get_daily_usage(user_id) >= limit:
        await message.answer(
            f"На сегодня лимит исчерпан ({limit} консультации). Возвращайся завтра!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")]
            ])
        )
        return

    # Увеличиваем счётчик ДО запроса (защита от дублей)
    _increment_usage(user_id)

    thinking_msg = await message.answer(
        "🔮 _Мастер изучает твой запрос..._\n_Обычно занимает 5–10 секунд_",
        parse_mode="Markdown"
    )

    # Собираем список камней для контекста
    stones = ContentLoader.load_all_stones()
    stones_list = ", ".join(
        d.get('TITLE', sid) for sid, d in list(stones.items())[:25]
    ) if stones else "розовый кварц, аметист, цитрин, лабрадорит, чёрный турмалин"

    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Запрос клиента: {user_text}\n\n"
        f"Камни в наличии у мастера: {stones_list}\n\n"
        f"Дай персональную консультацию."
    )

    response_text = await _call_gemini(full_prompt)

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    used_now = _get_daily_usage(user_id)
    remaining = max(0, limit - used_now)

    if response_text and not response_text.startswith("⚠️"):
        footer = f"\n\n_💬 Консультаций на сегодня осталось: {remaining}_" if remaining > 0 else \
                 f"\n\n_💬 Это была последняя консультация на сегодня. Завтра снова доступно {limit}._"

        await message.answer(
            f"🔮 *СОВЕТ МАСТЕРА*\n\n{response_text}{footer}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🩺 ДИАГНОСТИКА — глубже", callback_data="diagnostic")],
                [InlineKeyboardButton(text="💍 КАСТОМНЫЙ ЗАКАЗ", callback_data="custom_order")],
                [InlineKeyboardButton(text="📚 БАЗА ЗНАНИЙ", callback_data="knowledge")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
    elif response_text and response_text.startswith("⚠️"):
        await message.answer(response_text)
    else:
        # Если API недоступен — возвращаем запрос обратно
        _decrement_usage(user_id)
        await message.answer(
            "🙏 Сейчас не могу ответить — сервис временно недоступен.\n"
            "Попробуй через пару минут или напиши мастеру напрямую.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 ПОПРОБОВАТЬ СНОВА", callback_data="ai_consult")],
                [InlineKeyboardButton(text="📞 НАПИСАТЬ МАСТЕРУ", callback_data="contact_master")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )


def _decrement_usage(user_id: int):
    """Уменьшить счётчик если API вернул ошибку."""
    today = date.today().isoformat()
    with db.cursor() as c:
        c.execute("""
            UPDATE ai_consult_usage SET count = MAX(0, count - 1)
            WHERE user_id = ? AND usage_date = ?
        """, (user_id, today))


# ──────────────────────────────────────────────────────────────
# GEMINI API
# ──────────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> str:
    """Вызов Google Gemini API (бесплатный тариф: 1500 req/day)."""
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY не задан")
        return (
            "⚠️ Совет мастера временно недоступен.\n\n"
            "Для активации добавьте GEMINI_API_KEY в переменные Railway.\n"
            "Ключ бесплатно: aistudio.google.com"
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
            "topP": 0.9,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=25)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            return parts[0].get('text', '').strip()
                    logger.warning(f"Gemini: пустой ответ — {data}")
                    return ""
                else:
                    body = await resp.text()
                    logger.error(f"Gemini API error {resp.status}: {body[:200]}")
                    return ""
    except aiohttp.ClientTimeout:
        logger.error("Gemini API: timeout")
        return ""
    except Exception as e:
        logger.error(f"Gemini API exception: {e}")
        return ""
