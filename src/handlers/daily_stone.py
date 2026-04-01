"""
Камень дня — ежедневная рассылка пользователям.
Запускается из фоновой задачи в background.py
"""
import logging
import random
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.utils.text_loader import ContentLoader
from src.database.db import db

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "daily_stone")
async def show_daily_stone(callback: CallbackQuery):
    """Показать камень дня вручную (кнопка в меню)."""
    stones = ContentLoader.load_all_stones()
    if not stones:
        await callback.answer("Камни не загружены", show_alert=True)
        return

    # Берём камень дня — детерминированно по дате
    from datetime import date
    day_index = date.today().toordinal() % len(stones)
    stone_id = list(stones.keys())[day_index]
    stone = stones[stone_id]

    emoji = stone.get('EMOJI', '💎')
    title = stone.get('TITLE', stone_id)
    short_desc = stone.get('SHORT_DESC', '')
    properties = stone.get('PROPERTIES', '')
    chakra = stone.get('CHAKRA', '')

    text = (
        f"🌅 *КАМЕНЬ ДНЯ*\n\n"
        f"{emoji} *{title}*\n\n"
        f"_{short_desc}_\n\n"
    )
    if properties:
        text += f"✨ *Свойства:* {properties}\n"
    if chakra:
        text += f"🌀 *Чакра:* {chakra}\n"

    text += (
        f"\n💡 *Совет дня:* Носи {title} сегодня или держи рядом — "
        f"это усилит его влияние на твою жизнь."
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 КУПИТЬ С {emoji} {title}", callback_data="showcase")],
            [InlineKeyboardButton(text="📚 ПОДРОБНЕЕ О КАМНЕ", callback_data=f"know_{stone_id}")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )
    await callback.answer()


async def send_daily_stone_broadcast(bot: Bot):
    """Рассылка камня дня всем пользователям (запускается в 9:00)."""
    stones = ContentLoader.load_all_stones()
    if not stones:
        return

    from datetime import date
    day_index = date.today().toordinal() % len(stones)
    stone_id = list(stones.keys())[day_index]
    stone = stones[stone_id]

    emoji = stone.get('EMOJI', '💎')
    title = stone.get('TITLE', stone_id)
    short_desc = stone.get('SHORT_DESC', '')

    text = (
        f"🌅 *КАМЕНЬ ДНЯ — {emoji} {title}*\n\n"
        f"_{short_desc}_\n\n"
        f"Этот камень несёт особую силу сегодня. "
        f"Носи его или держи рядом весь день."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📚 Читать о {title}", callback_data=f"know_{stone_id}")],
        [InlineKeyboardButton(text="💎 Купить браслет", callback_data="showcase")],
    ])

    with db.cursor() as c:
        c.execute("SELECT user_id FROM users ORDER BY created_at DESC LIMIT 5000")
        users = [row['user_id'] for row in c.fetchall()]

    sent = 0
    failed = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=kb)
            sent += 1
        except Exception:
            failed += 1

    logger.info(f"Камень дня отправлен: {sent} успешно, {failed} ошибок")
