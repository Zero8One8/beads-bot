"""
Кастомный заказ — 5 вопросов через кнопки, без текстового ввода.
После ответов — сразу сохраняется заявка и уведомляет мастера.
Никаких /skip, никакого текстового ввода.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from src.database.db import db
from src.database.models import UserModel
from src.config import Config

logger = logging.getLogger(__name__)
router = Router()


class CustomOrderStates(StatesGroup):
    q_purpose   = State()
    q_situation = State()
    q_stones    = State()
    q_size      = State()
    q_budget    = State()


@router.callback_query(F.data == "custom_order")
async def custom_order_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "💍 *КАСТОМНЫЙ ЗАКАЗ — БРАСЛЕТ ДЛЯ ТЕБЯ*\n\n"
        "Каждый браслет создаётся под конкретного человека.\n"
        "Мастер лично подберёт камни под твою ситуацию и цели.\n\n"
        "5 вопросов — и заявка уйдёт мастеру.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ НАЧАТЬ", callback_data="co_q1")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")],
        ])
    )


@router.callback_query(F.data == "co_q1")
async def co_q1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomOrderStates.q_purpose)
    await callback.answer()
    await callback.message.edit_text(
        "💍 *Вопрос 1 из 5*\n\n🎯 *Для чего нужен браслет?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Деньги и успех",           callback_data="co_p_money")],
            [InlineKeyboardButton(text="💞 Любовь и отношения",       callback_data="co_p_love")],
            [InlineKeyboardButton(text="🛡 Защита от негатива",       callback_data="co_p_protect")],
            [InlineKeyboardButton(text="🔥 Энергия и уверенность",    callback_data="co_p_energy")],
            [InlineKeyboardButton(text="🌿 Спокойствие и баланс",     callback_data="co_p_calm")],
            [InlineKeyboardButton(text="✨ Духовное развитие",        callback_data="co_p_spirit")],
        ])
    )


@router.callback_query(CustomOrderStates.q_purpose, F.data.startswith("co_p_"))
async def co_q2(callback: CallbackQuery, state: FSMContext):
    MAP = {
        'co_p_money':   '💰 Деньги и успех',
        'co_p_love':    '💞 Любовь и отношения',
        'co_p_protect': '🛡 Защита',
        'co_p_energy':  '🔥 Энергия и уверенность',
        'co_p_calm':    '🌿 Спокойствие',
        'co_p_spirit':  '✨ Духовное развитие',
    }
    await state.update_data(purpose=MAP.get(callback.data, callback.data))
    await state.set_state(CustomOrderStates.q_situation)
    await callback.answer()
    await callback.message.edit_text(
        "💍 *Вопрос 2 из 5*\n\n🌿 *Что сейчас происходит в твоей жизни?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌪 Стресс и тревога",          callback_data="co_s_stress")],
            [InlineKeyboardButton(text="📉 Застой, нет движения",      callback_data="co_s_stagnation")],
            [InlineKeyboardButton(text="💔 Боль, потеря, расставание", callback_data="co_s_pain")],
            [InlineKeyboardButton(text="🚀 На подъёме, хочу усилить",  callback_data="co_s_growth")],
            [InlineKeyboardButton(text="🌫 Поиск себя и пути",        callback_data="co_s_search")],
            [InlineKeyboardButton(text="⚔️ Много препятствий",        callback_data="co_s_fight")],
        ])
    )


@router.callback_query(CustomOrderStates.q_situation, F.data.startswith("co_s_"))
async def co_q3(callback: CallbackQuery, state: FSMContext):
    MAP = {
        'co_s_stress':      '🌪 Стресс и тревога',
        'co_s_stagnation':  '📉 Застой',
        'co_s_pain':        '💔 Боль и потери',
        'co_s_growth':      '🚀 Рост и подъём',
        'co_s_search':      '🌫 Поиск себя',
        'co_s_fight':       '⚔️ Борьба с препятствиями',
    }
    await state.update_data(situation=MAP.get(callback.data, callback.data))
    await state.set_state(CustomOrderStates.q_stones)
    await callback.answer()
    await callback.message.edit_text(
        "💍 *Вопрос 3 из 5*\n\n💎 *Какой цвет камней привлекает больше?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌹 Розовый — нежность",       callback_data="co_st_pink")],
            [InlineKeyboardButton(text="💜 Фиолетовый — мистика",     callback_data="co_st_purple")],
            [InlineKeyboardButton(text="🖤 Тёмный — сила, защита",    callback_data="co_st_dark")],
            [InlineKeyboardButton(text="💛 Золотистый — энергия",     callback_data="co_st_gold")],
            [InlineKeyboardButton(text="💙 Синий — покой, глубина",   callback_data="co_st_blue")],
            [InlineKeyboardButton(text="🤝 Доверяю мастеру",         callback_data="co_st_trust")],
        ])
    )


@router.callback_query(CustomOrderStates.q_stones, F.data.startswith("co_st_"))
async def co_q4(callback: CallbackQuery, state: FSMContext):
    MAP = {
        'co_st_pink':   '🌹 Розовые (кварц, родонит)',
        'co_st_purple': '💜 Фиолетовые (аметист, лепидолит)',
        'co_st_dark':   '🖤 Тёмные (турмалин, обсидиан)',
        'co_st_gold':   '💛 Золотистые (цитрин, тигровый глаз)',
        'co_st_blue':   '💙 Синие (лазурит, содалит)',
        'co_st_trust':  '🤝 Доверяю мастеру',
    }
    await state.update_data(stones_preference=MAP.get(callback.data, callback.data))
    await state.set_state(CustomOrderStates.q_size)
    await callback.answer()
    await callback.message.edit_text(
        "💍 *Вопрос 4 из 5*\n\n📏 *Обхват запястья?*\n\n"
        "_Если не знаешь — выбери примерно_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="14–15 см — очень тонкое", callback_data="co_sz_14"),
             InlineKeyboardButton(text="15–16 см — тонкое",       callback_data="co_sz_15")],
            [InlineKeyboardButton(text="16–17 см — среднее",      callback_data="co_sz_16"),
             InlineKeyboardButton(text="17–18 см — среднее",      callback_data="co_sz_17")],
            [InlineKeyboardButton(text="18–19 см — широкое",      callback_data="co_sz_18"),
             InlineKeyboardButton(text="19+ см — широкое",        callback_data="co_sz_19")],
        ])
    )


@router.callback_query(CustomOrderStates.q_size, F.data.startswith("co_sz_"))
async def co_q5(callback: CallbackQuery, state: FSMContext):
    MAP = {
        'co_sz_14': '14–15 см',
        'co_sz_15': '15–16 см',
        'co_sz_16': '16–17 см',
        'co_sz_17': '17–18 см',
        'co_sz_18': '18–19 см',
        'co_sz_19': '19+ см',
    }
    await state.update_data(size=MAP.get(callback.data, '16–17 см'))
    await state.set_state(CustomOrderStates.q_budget)
    await callback.answer()
    await callback.message.edit_text(
        "💍 *Вопрос 5 из 5*\n\n💰 *Бюджет на браслет?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="до 2 000 ₽",        callback_data="co_b_2k")],
            [InlineKeyboardButton(text="2 000 – 5 000 ₽",   callback_data="co_b_5k")],
            [InlineKeyboardButton(text="5 000 – 10 000 ₽",  callback_data="co_b_10k")],
            [InlineKeyboardButton(text="от 10 000 ₽",       callback_data="co_b_max")],
        ])
    )


@router.callback_query(CustomOrderStates.q_budget, F.data.startswith("co_b_"))
async def co_finish(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Последний шаг — сохраняем и уведомляем мастера."""
    MAP = {
        'co_b_2k':  'до 2 000 ₽',
        'co_b_5k':  '2 000–5 000 ₽',
        'co_b_10k': '5 000–10 000 ₽',
        'co_b_max': 'от 10 000 ₽',
    }
    await state.update_data(budget=MAP.get(callback.data, callback.data))
    await callback.answer()

    data = await state.get_data()
    user_id = callback.from_user.id
    await state.clear()

    # Сохраняем заявку
    with db.cursor() as c:
        c.execute("""
            INSERT INTO custom_orders
                (user_id, purpose, stones, size, notes, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (
            user_id,
            data.get('purpose', ''),
            f"{data.get('stones_preference', '')} | Бюджет: {data.get('budget', '')}",
            data.get('size', ''),
            data.get('situation', ''),
            datetime.now()
        ))
        order_id = c.lastrowid

    # Уведомление мастеру
    user = UserModel.get(user_id)
    name  = (user.get('first_name') or user.get('username') or str(user_id)) if user else str(user_id)
    uname = f"@{user['username']}" if user and user.get('username') else "нет username"

    admin_text = (
        f"💍 *НОВЫЙ КАСТОМНЫЙ ЗАКАЗ #{order_id}*\n\n"
        f"👤 {name} ({uname}) | ID: `{user_id}`\n\n"
        f"🎯 *Цель:* {data.get('purpose', '—')}\n"
        f"🌿 *Ситуация:* {data.get('situation', '—')}\n"
        f"💎 *Камни:* {data.get('stones_preference', '—')}\n"
        f"📏 *Размер:* {data.get('size', '—')}\n"
        f"💰 *Бюджет:* {data.get('budget', '—')}"
    )
    try:
        await bot.send_message(
            Config.ADMIN_ID, admin_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ ВЗЯТЬ В РАБОТУ",
                    callback_data=f"custom_take_{order_id}"
                )
            ]])
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления мастера: {e}")

    # Подтверждение пользователю
    await callback.message.edit_text(
        f"✅ *ЗАЯВКА #{order_id} ПРИНЯТА!*\n\n"
        f"Мастер свяжется с тобой в течение 24 часов.\n\n"
        f"*Твой запрос:*\n"
        f"• Цель: {data.get('purpose', '—')}\n"
        f"• Камни: {data.get('stones_preference', '—')}\n"
        f"• Размер: {data.get('size', '—')}\n"
        f"• Бюджет: {data.get('budget', '—')}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🩺 ДИАГНОСТИКА — глубже", callback_data="diagnostic")],
            [InlineKeyboardButton(text="← ГЛАВНОЕ МЕНЮ",          callback_data="menu")],
        ])
    )
