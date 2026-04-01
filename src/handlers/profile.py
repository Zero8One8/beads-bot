"""
Профиль пользователя — заказы, баланс, стрик, свой камень.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.database.db import db
from src.database.models import UserModel, OrderModel, ClubModel

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "profile")
async def profile_show(callback: CallbackQuery):
    """Профиль пользователя."""
    user_id = callback.from_user.id
    user = UserModel.get(user_id)

    if not user:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    name = user.get('first_name') or user.get('username') or f"ID{user_id}"

    # Баланс бонусов
    bonus = UserModel.get_bonus_balance(user_id)

    # Заказы
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM orders WHERE user_id = ? AND status = 'paid'", (user_id,))
        orders_count = c.fetchone()['cnt'] or 0

        c.execute("SELECT SUM(total_price) as total FROM orders WHERE user_id = ? AND status = 'paid'", (user_id,))
        row = c.fetchone()
        total_spent = int(row['total'] or 0)

    # Стрик
    with db.cursor() as c:
        c.execute("SELECT streak_days, total_checkins FROM user_streaks WHERE user_id = ?", (user_id,))
        streak_row = c.fetchone()
    streak = streak_row['streak_days'] if streak_row else 0
    checkins = streak_row['total_checkins'] if streak_row else 0

    # Клуб
    has_club = ClubModel.has_access(user_id)
    club_status = "✅ Активна" if has_club else "❌ Нет"

    # AI лимит
    from datetime import date
    today = date.today().isoformat()
    with db.cursor() as c:
        c.execute("SELECT count FROM ai_consult_usage WHERE user_id = ? AND usage_date = ?", (user_id, today))
        ai_row = c.fetchone()
    ai_used = ai_row['count'] if ai_row else 0
    from src.config import Config
    ai_limit = Config.AI_DAILY_LIMIT

    fire = "🔥" * min(streak, 5) if streak > 0 else "—"

    text = (
        f"👤 *МОЙ ПРОФИЛЬ*\n\n"
        f"*{name}*\n\n"
        f"📦 *Заказов:* {orders_count} (на {total_spent} ₽)\n"
        f"💰 *Бонусы:* {int(bonus)} ₽\n"
        f"🔮 *Портал силы:* {club_status}\n"
        f"🔥 *Стрик:* {fire} {streak} дней ({checkins} всего)\n"
        f"🤖 *AI советов сегодня:* {ai_used}/{ai_limit}\n\n"
    )

    buttons = [
        [InlineKeyboardButton(text="📦 МОИ ЗАКАЗЫ", callback_data="my_orders")],
        [InlineKeyboardButton(text="🔥 МОЙ СТРИК", callback_data="streak")],
        [InlineKeyboardButton(text="🤝 РЕФЕРАЛЫ", callback_data="referral")],
    ]

    if has_club:
        buttons.append([InlineKeyboardButton(text="🔮 ПОРТАЛ СИЛЫ", callback_data="club_content")])
    else:
        buttons.append([InlineKeyboardButton(text="🔮 ВСТУПИТЬ В КЛУБ", callback_data="club")])

    buttons.append([InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")])

    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()
