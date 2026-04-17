"""
Фоновые задачи.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from src.database.db import db
from src.database.models import OrderModel
from src.services.notifications import AdminNotifier
from src.config import Config

logger = logging.getLogger(__name__)


async def check_pending_orders():
    """Проверка неоплаченных заказов (отмена через 24 часа)."""
    while True:
        try:
            await asyncio.sleep(3600)  # каждый час
            
            with db.cursor() as c:
                c.execute("""
                    SELECT id, user_id FROM orders
                    WHERE status = 'pending'
                    AND created_at < datetime('now', '-24 hours')
                """)
                old_orders = c.fetchall()
                
                for order in old_orders:
                    c.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order['id'],))
                    logger.info(f"Заказ #{order['id']} отменён (не оплачен 24ч)")
                    
        except Exception as e:
            logger.error(f"Ошибка в check_pending_orders: {e}")


async def check_birthdays():
    """Проверка дней рождений и отправка промокодов."""
    while True:
        try:
            await asyncio.sleep(3600)
            
            today = datetime.now().strftime('%m-%d')
            with db.cursor() as c:
                c.execute("""
                    SELECT user_id, first_name FROM users
                    WHERE birthday IS NOT NULL
                    AND strftime('%m-%d', birthday) = ?
                """, (today,))
                birthday_users = c.fetchall()
                
                for user in birthday_users:
                    c.execute("""
                        SELECT 1 FROM birthday_promos
                        WHERE user_id = ? AND date = date('now')
                    """, (user['user_id'],))
                    if c.fetchone():
                        continue
                    
                    promo_code = f"BDAY{user['user_id']}{datetime.now().strftime('%d%m')}"
                    
                    c.execute("""
                        INSERT INTO promocodes (code, discount_pct, max_uses, created_at)
                        VALUES (?, 15, 1, ?)
                    """, (promo_code, datetime.now()))
                    
                    c.execute("""
                        INSERT INTO birthday_promos (user_id, promo_code, date)
                        VALUES (?, ?, date('now'))
                    """, (user['user_id'], promo_code))
                    
                    logger.info(f"Создан birthday-промокод {promo_code} для {user['user_id']}")
                    
        except Exception as e:
            logger.error(f"Ошибка в check_birthdays: {e}")


async def send_daily_stone(bot):
    """Рассылка камня дня в 9:00 каждый день."""
    while True:
        try:
            from datetime import datetime, time
            now = datetime.now()
            # Вычисляем сколько ждать до следующего 9:00
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target:
                from datetime import timedelta
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            # Рассылка
            from src.handlers.daily_stone import send_daily_stone_broadcast
            await send_daily_stone_broadcast(bot)
            logger.info("✅ Камень дня разослан")

            # Ждём до следующего дня
            await asyncio.sleep(23 * 3600)
        except Exception as e:
            logger.error(f"Ошибка рассылки камня дня: {e}")
            await asyncio.sleep(3600)


async def check_cart_reminders(bot):
    """Напоминания о брошенной корзине — через 2 часа после добавления."""
    while True:
        try:
            await asyncio.sleep(1800)  # Проверяем каждые 30 минут

            with db.cursor() as c:
                c.execute("""
                    SELECT DISTINCT cart.user_id,
                           MIN(cart.added_at) as first_added
                    FROM cart
                    JOIN users ON cart.user_id = users.user_id
                    WHERE cart.status = 'active'
                      AND cart.added_at < datetime('now', '-2 hours')
                      AND (
                          SELECT reminded FROM cart_reminders
                          WHERE user_id = cart.user_id
                      ) IS NULL
                      OR (
                          (
                              SELECT reminded FROM cart_reminders
                              WHERE user_id = cart.user_id
                          ) = 0
                          AND cart.status = 'active'
                          AND cart.added_at < datetime('now', '-2 hours')
                      )
                    GROUP BY cart.user_id
                    LIMIT 50
                """)
                users_to_remind = c.fetchall()

            for row in users_to_remind:
                user_id = row['user_id']
                try:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🛒 ВЕРНУТЬСЯ К КОРЗИНЕ", callback_data="cart")]
                    ])
                    await bot.send_message(
                        user_id,
                        "🛒 *Ты забыл(а) кое-что в корзине!*\n\n"
                        "Камни ждут тебя. Оформи заказ пока они ещё доступны.",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                    with db.cursor() as c:
                        c.execute("""
                            INSERT INTO cart_reminders (user_id, last_reminder, reminded)
                            VALUES (?, datetime('now'), 1)
                            ON CONFLICT(user_id) DO UPDATE SET
                                last_reminder = datetime('now'),
                                reminded = 1
                        """, (user_id,))
                    logger.info(f"Напоминание о корзине отправлено: {user_id}")
                except Exception as e:
                    logger.debug(f"Не удалось отправить напоминание {user_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка в check_cart_reminders: {e}")
            await asyncio.sleep(1800)


async def check_reactivation(bot):
    """Уведомление мастеру если пользователь 3 дня не заходил."""
    while True:
        try:
            await asyncio.sleep(6 * 3600)  # Каждые 6 часов
            with db.cursor() as c:
                c.execute("""
                    SELECT DISTINCT fs.user_id, u.first_name, u.username,
                           MAX(fs.created_at) as last_seen
                    FROM funnel_stats fs
                    JOIN users u ON fs.user_id = u.user_id
                    WHERE fs.created_at < datetime('now', '-3 days')
                      AND fs.user_id NOT IN (
                          SELECT user_id FROM funnel_stats
                          WHERE created_at > datetime('now', '-3 days')
                      )
                      AND fs.user_id NOT IN (
                          SELECT DISTINCT user_id FROM funnel_stats
                          WHERE event_type = 'reactivation_sent'
                            AND created_at > datetime('now', '-7 days')
                      )
                    GROUP BY fs.user_id
                    LIMIT 20
                """)
                inactive = c.fetchall()

            if inactive:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                text = f"😴 *НЕАКТИВНЫЕ ПОЛЬЗОВАТЕЛИ ({len(inactive)}):*\n\n"
                for row in inactive[:10]:
                    name = row['first_name'] or row['username'] or str(row['user_id'])
                    uname = f"@{row['username']}" if row['username'] else "нет"
                    last = str(row['last_seen'])[:10] if row['last_seen'] else '—'
                    text += f"• {name} ({uname}) — последний раз: {last}\n"

                try:
                    await bot.send_message(Config.ADMIN_ID, text, parse_mode="Markdown")
                    for row in inactive:
                        with db.cursor() as c:
                            c.execute("""INSERT INTO funnel_stats (user_id, event_type, created_at)
                                         VALUES (?, 'reactivation_sent', ?)""",
                                      (row['user_id'], datetime.now()))
                except Exception as e:
                    logger.error(f"Ошибка отправки отчёта реактивации: {e}")

        except Exception as e:
            logger.error(f"Ошибка check_reactivation: {e}")
            await asyncio.sleep(6 * 3600)


async def send_review_requests(bot):
    """Запросы отзывов — через 7 дней после оплаты заказа."""
    while True:
        try:
            await asyncio.sleep(3 * 3600)  # Каждые 3 часа

            with db.cursor() as c:
                c.execute("""
                    SELECT o.id as order_id, o.user_id
                    FROM orders o
                    WHERE o.status = 'completed'
                      AND o.created_at < datetime('now', '-7 days')
                      AND o.id NOT IN (
                          SELECT order_id FROM review_requests WHERE review_received = 0
                      )
                    LIMIT 10
                """)
                orders = c.fetchall()

            for order in orders:
                try:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⭐ ОСТАВИТЬ ОТЗЫВ", callback_data="story_create")],
                        [InlineKeyboardButton(text="✅ Всё отлично, спасибо!", callback_data=f"review_done_{order['order_id']}")],
                    ])
                    await bot.send_message(
                        order['user_id'],
                        f"💎 *Как твой браслет?*\n\n"
                        f"Прошла неделя с получения заказа #{order['order_id']}.\n"
                        f"Поделись опытом — это помогает другим выбирать.\n\n"
                        f"_А ещё отзывы с фото дают +50 бонусов на следующий заказ!_",
                        parse_mode="Markdown",
                        reply_markup=kb
                    )
                    with db.cursor() as c:
                        c.execute("""INSERT INTO review_requests (user_id, order_id, sent_at)
                                     VALUES (?, ?, ?)""",
                                  (order['user_id'], order['order_id'], datetime.now()))
                except Exception as e:
                    logger.debug(f"Ошибка запроса отзыва для {order['user_id']}: {e}")

        except Exception as e:
            logger.error(f"Ошибка send_review_requests: {e}")
            await asyncio.sleep(3 * 3600)


async def send_birthday_promos(bot):
    """Промокоды в день рождения — раз в сутки в 10:00."""
    while True:
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            # Ждём до 10:00 следующего дня если уже после 10, или до 10:00 сегодня
            target = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            from datetime import date
            today = date.today()
            today_mmdd = f"{today.month:02d}-{today.day:02d}"

            with db.cursor() as c:
                c.execute("""
                    SELECT u.user_id, u.first_name
                    FROM users u
                    WHERE strftime('%m-%d', u.birthday) = ?
                      AND u.user_id NOT IN (
                          SELECT user_id FROM birthday_promos
                          WHERE strftime('%Y', date) = ?
                      )
                    LIMIT 20
                """, (today_mmdd, str(today.year)))
                birthday_users = c.fetchall()

            for user in birthday_users:
                try:
                    import random, string
                    promo = f"BDAY{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                    with db.cursor() as c:
                        c.execute("""INSERT OR IGNORE INTO promocodes
                                     (code, discount_pct, max_uses, created_at, active)
                                     VALUES (?, 20, 1, ?, 1)""",
                                  (promo, datetime.now()))
                        c.execute("""INSERT OR IGNORE INTO birthday_promos
                                     (user_id, promo_code, date)
                                     VALUES (?, ?, date('now'))""",
                                  (user['user_id'], promo))

                    name = user['first_name'] or "Дорогой друг"
                    await bot.send_message(
                        user['user_id'],
                        f"🎂 *С ДНЁМ РОЖДЕНИЯ, {name}!*\n\n"
                        f"Мастер поздравляет тебя и дарит скидку *20%* на любой заказ!\n\n"
                        f"Промокод: `{promo}`\n\n"
                        f"_Действует 7 дней. Введи при оформлении заказа._",
                        parse_mode="Markdown"
                    )
                    logger.info(f"День рождения: {user['user_id']}, промокод {promo}")
                except Exception as e:
                    logger.debug(f"Ошибка birthday promo {user['user_id']}: {e}")

        except Exception as e:
            logger.error(f"Ошибка send_birthday_promos: {e}")
            await asyncio.sleep(86400)
