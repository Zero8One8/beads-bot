"""
Астро-совет недели — мастер пишет пост, бот рассылает в понедельник.
Пользователи видят актуальный совет в боте.
"""
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.db import db
from src.database.models import UserModel
from src.config import Config

logger = logging.getLogger(__name__)
router = Router()


class AstroAdminStates(StatesGroup):
    waiting_text = State()
    waiting_stones = State()


# ── ПОЛЬЗОВАТЕЛЬ ────────────────────────────────────────────

@router.callback_query(F.data == "astro_advice")
async def astro_show(callback: CallbackQuery):
    """Показать актуальный астро-совет."""
    with db.cursor() as c:
        c.execute("""SELECT text, stones, created_at FROM astro_advice
                     ORDER BY id DESC LIMIT 1""")
        advice = c.fetchone()

    if not advice:
        await callback.message.edit_text(
            "🌟 *АСТРО-СОВЕТ НЕДЕЛИ*\n\n"
            "Совет этой недели ещё не опубликован.\n"
            "Возвращайся в понедельник!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")]
            ])
        )
        await callback.answer()
        return

    from src.utils.text_loader import ContentLoader
    stones_all = ContentLoader.load_all_stones()

    stones_text = ""
    if advice['stones']:
        for sid in advice['stones'].split(','):
            sid = sid.strip()
            stone = stones_all.get(sid, {})
            if stone:
                e = stone.get('EMOJI', '💎')
                t = stone.get('TITLE', sid)
                stones_text += f"\n{e} {t}"

    date_str = str(advice['created_at'])[:10] if advice['created_at'] else ''

    text = (
        f"🌟 *АСТРО-СОВЕТ НЕДЕЛИ*\n"
        f"_{date_str}_\n\n"
        f"{advice['text']}"
    )
    if stones_text:
        text += f"\n\n*Камни недели:*{stones_text}"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 ЗАКАЗАТЬ БРАСЛЕТ", callback_data="custom_order")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )
    await callback.answer()


# ── АДМИН ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_astro")
async def admin_astro_menu(callback: CallbackQuery):
    """Меню астро-советов для админа."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    await callback.message.edit_text(
        "🌟 *АСТРО-СОВЕТЫ*\n\n"
        "Напишите совет — он будет показан пользователям "
        "и разослан в ближайший понедельник.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ НАПИСАТЬ СОВЕТ", callback_data="admin_astro_write")],
            [InlineKeyboardButton(text="📤 РАЗОСЛАТЬ СЕЙЧАС", callback_data="admin_astro_send_now")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="admin_content")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_astro_write")
async def admin_astro_write(callback: CallbackQuery, state: FSMContext):
    """Написать новый астро-совет."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    await state.set_state(AstroAdminStates.waiting_text)
    await callback.message.edit_text(
        "✍️ Напишите текст астро-совета недели:\n\n"
        "_Например: «На этой неделе Меркурий входит в Овен — "
        "время решительных действий. Камни которые поддержат...»_",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AstroAdminStates.waiting_text)
async def admin_astro_text(message: Message, state: FSMContext):
    """Текст совета получен."""
    await state.update_data(text=message.text)
    await state.set_state(AstroAdminStates.waiting_stones)
    await message.answer(
        "Укажите камни недели (через запятую, stone_id):\n\n"
        "_Например: amethyst, rose_quartz, labradorite_\n\n"
        "Или /skip чтобы без камней.",
    )


@router.message(AstroAdminStates.waiting_stones)
async def admin_astro_stones(message: Message, state: FSMContext):
    """Камни указаны — сохраняем совет."""
    data = await state.get_data()
    stones = "" if message.text == "/skip" else message.text.strip()
    await state.clear()

    with db.cursor() as c:
        c.execute("""INSERT INTO astro_advice (text, stones, author_id, sent, created_at)
                     VALUES (?, ?, ?, 0, ?)""",
                  (data['text'], stones, message.from_user.id, datetime.now()))

    await message.answer(
        "✅ Астро-совет сохранён!\n\n"
        "Он уже виден пользователям в разделе «Астро-совет».\n"
        "Автоматическая рассылка — в ближайший понедельник в 10:00.\n"
        "Или нажми «Разослать сейчас» в меню астро-советов.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 РАЗОСЛАТЬ СЕЙЧАС", callback_data="admin_astro_send_now")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="admin_astro")],
        ])
    )


@router.callback_query(F.data == "admin_astro_send_now")
async def admin_astro_send_now(callback: CallbackQuery, bot: Bot):
    """Разослать последний астро-совет прямо сейчас."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    await callback.answer("⏳ Рассылка запущена...", show_alert=True)
    await send_astro_broadcast(bot)


async def send_astro_broadcast(bot: Bot):
    """Рассылка астро-совета всем пользователям."""
    with db.cursor() as c:
        c.execute("SELECT id, text, stones FROM astro_advice ORDER BY id DESC LIMIT 1")
        advice = c.fetchone()

    if not advice:
        return

    from src.utils.text_loader import ContentLoader
    stones_all = ContentLoader.load_all_stones()
    stones_text = ""
    if advice['stones']:
        for sid in advice['stones'].split(','):
            sid = sid.strip()
            stone = stones_all.get(sid, {})
            if stone:
                e = stone.get('EMOJI', '💎')
                t = stone.get('TITLE', sid)
                stones_text += f"\n{e} {t}"

    text = f"🌟 *АСТРО-СОВЕТ НЕДЕЛИ*\n\n{advice['text']}"
    if stones_text:
        text += f"\n\n*Камни недели:*{stones_text}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💍 ЗАКАЗАТЬ БРАСЛЕТ", callback_data="custom_order")]
    ])

    with db.cursor() as c:
        c.execute("SELECT user_id FROM users LIMIT 10000")
        users = [r['user_id'] for r in c.fetchall()]

    sent = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=kb)
            sent += 1
        except Exception:
            pass

    with db.cursor() as c:
        c.execute("UPDATE astro_advice SET sent = 1, sent_at = ? WHERE id = ?",
                  (datetime.now(), advice['id']))

    logger.info(f"Астро-совет разослан: {sent} пользователей")
