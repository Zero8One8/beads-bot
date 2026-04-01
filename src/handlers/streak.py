"""
Стрик практик — пользователь отмечает что надел браслет сегодня.
Считает дни подряд, даёт бонусы за 7/30 дней.
Напоминания о чистке камней каждые 14 дней.
"""
import logging
from datetime import datetime, date, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from src.database.db import db

logger = logging.getLogger(__name__)
router = Router()


def _get_streak(user_id: int) -> dict:
    """Получить данные стрика пользователя."""
    with db.cursor() as c:
        c.execute("""
            SELECT streak_days, last_checkin, total_checkins, last_cleaning_reminder
            FROM user_streaks WHERE user_id = ?
        """, (user_id,))
        row = c.fetchone()
    if row:
        return dict(row)
    return {'streak_days': 0, 'last_checkin': None, 'total_checkins': 0, 'last_cleaning_reminder': None}


def _update_streak(user_id: int) -> dict:
    """Обновить стрик при чек-ине. Возвращает новые данные."""
    today = date.today()
    streak_data = _get_streak(user_id)

    last = streak_data.get('last_checkin')
    if last:
        last_date = date.fromisoformat(str(last)[:10])
        if last_date == today:
            return {'status': 'already', **streak_data}
        elif last_date == today - timedelta(days=1):
            new_streak = streak_data['streak_days'] + 1
        else:
            new_streak = 1  # Стрик прерван
    else:
        new_streak = 1

    new_total = streak_data['total_checkins'] + 1

    with db.cursor() as c:
        c.execute("""
            INSERT INTO user_streaks (user_id, streak_days, last_checkin, total_checkins)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                streak_days = excluded.streak_days,
                last_checkin = excluded.last_checkin,
                total_checkins = excluded.total_checkins
        """, (user_id, new_streak, today.isoformat(), new_total))

    # Бонусы за 7 и 30 дней
    bonus = 0
    milestone = None
    if new_streak == 7:
        bonus = 50
        milestone = "7 дней"
    elif new_streak == 30:
        bonus = 200
        milestone = "30 дней"
    elif new_streak % 30 == 0:
        bonus = 200
        milestone = f"{new_streak} дней"

    if bonus > 0:
        with db.cursor() as c:
            c.execute("""
                INSERT INTO referral_balance (user_id, balance, total_earned)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    balance = balance + excluded.balance,
                    total_earned = total_earned + excluded.total_earned
            """, (user_id, bonus, bonus))

    return {
        'status': 'checked',
        'streak_days': new_streak,
        'total_checkins': new_total,
        'bonus': bonus,
        'milestone': milestone
    }


@router.callback_query(F.data == "streak")
async def streak_menu(callback: CallbackQuery):
    """Меню стрика."""
    user_id = callback.from_user.id
    data = _get_streak(user_id)
    streak = data['streak_days']
    total = data['total_checkins']
    last = data.get('last_checkin')

    today = date.today()
    checked_today = last and date.fromisoformat(str(last)[:10]) == today

    # Визуализация стрика
    fire = "🔥" * min(streak, 7)
    if not fire:
        fire = "○"

    next_milestone = 7 if streak < 7 else 30 if streak < 30 else ((streak // 30 + 1) * 30)
    days_to_next = next_milestone - streak

    text = (
        f"🔥 *СТРИК ПРАКТИК*\n\n"
        f"*{fire}*\n\n"
        f"📅 Дней подряд: *{streak}*\n"
        f"📊 Всего отметок: *{total}*\n"
        f"🎯 До следующего бонуса: *{days_to_next} дней*\n\n"
    )

    if streak >= 7:
        text += "🏆 *Бонусы:*\n7 дней — 50 бонусов ✅\n"
    if streak >= 30:
        text += "30 дней — 200 бонусов ✅\n"

    text += (
        f"\n_Отмечай каждый день когда надел браслет или работал с камнями._\n"
        f"_7 дней подряд = 50 бонусов. 30 дней = 200 бонусов._"
    )

    buttons = []
    if checked_today:
        buttons.append([InlineKeyboardButton(text="✅ Уже отмечено сегодня", callback_data="noop")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ ОТМЕТИТЬ СЕГОДНЯ", callback_data="streak_checkin")])

    buttons.append([InlineKeyboardButton(text="🪩 НАПОМНИТЬ О ЧИСТКЕ", callback_data="cleaning_remind")])
    buttons.append([InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")])

    await callback.answer()
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )



@router.callback_query(F.data == "streak_checkin")
async def streak_checkin(callback: CallbackQuery):
    """Чек-ин дня."""
    user_id = callback.from_user.id
    result = _update_streak(user_id)

    if result['status'] == 'already':
        await callback.answer("Ты уже отметился сегодня!", show_alert=True)
        return

    streak = result['streak_days']
    fire = "🔥" * min(streak, 7)

    text = f"✅ *ОТМЕЧЕНО!*\n\n{fire}\n\n*{streak} {'день' if streak == 1 else 'дня' if 2 <= streak <= 4 else 'дней'} подряд!*\n\n"

    if result.get('milestone'):
        text += (
            f"🏆 *РУБЕЖ {result['milestone'].upper()}!*\n"
            f"Начислено *{result['bonus']} бонусов* на счёт! 🎉\n\n"
        )

    if streak == 3:
        text += "_Три дня подряд — это уже привычка начинает формироваться!_"
    elif streak == 7:
        text += "_Неделя! Камни уже стали частью твоей жизни._"
    elif streak == 14:
        text += "_Две недели! Самое время почистить камни — они много работали._"
    elif streak == 30:
        text += "_Месяц! Ты — настоящий практик. Камни это чувствуют._"
    else:
        text += "_Так держать! Постоянство — это и есть магия._"

    await callback.answer()
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 МОЙ СТРИК", callback_data="streak")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )



@router.callback_query(F.data == "cleaning_remind")
async def cleaning_remind(callback: CallbackQuery):
    """Инструкция по чистке камней."""
    text = (
        "🪩 *ЧИСТКА КАМНЕЙ — ПАМЯТКА*\n\n"
        "Камни нужно чистить раз в 1-2 недели, особенно если носишь постоянно.\n\n"
        "✨ *Способы чистки:*\n\n"
        "💧 *Проточная вода* — подходит большинству камней. "
        "Держи под холодной водой 1-2 минуты, визуализируй как негатив уходит.\n"
        "_Нельзя:_ лепидолиту, малахиту, пириту, кианиту.\n\n"
        "🌙 *Лунный свет* — положи на подоконник в полнолуние. "
        "Подходит всем без исключения.\n\n"
        "🌿 *Земля* — закопай в землю на ночь. Мощная перезагрузка.\n\n"
        "🔔 *Звук* — поющая чаша, колокольчик, звонкий металл рядом.\n\n"
        "☀️ *Солнце* — 30 минут на утреннем солнце. "
        "_Нельзя:_ аметисту, флюориту, розовому кварцу — выцветают.\n\n"
        "После чистки — зарядка намерением: "
        "возьми в руки, закрой глаза, скажи для чего он тебе нужен сейчас."
    )
    await callback.answer()
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 МОЙ СТРИК", callback_data="streak")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )

