"""
Базовые пользовательские хендлеры.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.database.models import UserModel, SettingsModel
from src.keyboards.inline import get_main_keyboard
from src.services.analytics import FunnelTracker
from src.config import Config

logger = logging.getLogger(__name__)
router = Router()


def _get_selector_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Деньги и успех", callback_data="sel_money"),
         InlineKeyboardButton(text="💞 Любовь", callback_data="sel_love")],
        [InlineKeyboardButton(text="🛡 Защита", callback_data="sel_protect"),
         InlineKeyboardButton(text="⚡ Энергия", callback_data="sel_energy")],
        [InlineKeyboardButton(text="🌿 Спокойствие", callback_data="sel_calm"),
         InlineKeyboardButton(text="✨ Духовный рост", callback_data="sel_spirit")],
        [InlineKeyboardButton(text="🌱 Здоровье", callback_data="sel_health"),
         InlineKeyboardButton(text="🧠 Ясность ума", callback_data="sel_clarity")],
        [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
    ])


def _get_master_contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать мастеру", url=f"https://t.me/{Config.MASTER_USERNAME}")],
        [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
    ])


async def _send_deep_link_content(message: Message, deep_link: str):
    if deep_link in ("diagnostika", "diagnostic"):
        from src.keyboards.diagnostic import get_diagnostic_keyboard
        await message.answer(
            "🔮 *ЭНЕРГЕТИЧЕСКАЯ ДИАГНОСТИКА*\n\n"
            "Мастер анализирует ваше состояние по двум фото и даёт "
            "персональные рекомендации по камням и практикам.\n\n"
            "📸 *Что нужно прислать:*\n"
            "1. Лицом в полный рост, глаза в объектив (без очков)\n"
            "2. Спиной в полный рост\n"
            "Оба фото — на нейтральном светлом фоне.\n\n"
            "🔒 Фото нужны только для диагностики и после удаляются.\n"
            "⏱ Ответ мастера — в течение 24 часов.",
            parse_mode="Markdown",
            reply_markup=get_diagnostic_keyboard()
        )
        return

    if deep_link == "services":
        from src.database.models import ServiceModel
        from src.keyboards.services import get_services_keyboard
        services = ServiceModel.get_all(active_only=True)
        if services:
            await message.answer(
                "✨ *НАШИ УСЛУГИ*\n\nИндивидуальная работа с мастером.",
                parse_mode="Markdown",
                reply_markup=get_services_keyboard(services)
            )
        else:
            await message.answer(
                "✨ *УСЛУГИ МАСТЕРА*\n\nРасписание обновляется. Напишите мастеру напрямую:",
                parse_mode="Markdown",
                reply_markup=_get_master_contact_keyboard()
            )
        return

    if deep_link == "shop":
        from src.database.models import CategoryModel
        from src.keyboards.shop import get_categories_keyboard
        categories = CategoryModel.get_all()
        await message.answer(
            "💎 *ВИТРИНА*\n\nВыберите категорию:",
            parse_mode="Markdown",
            reply_markup=get_categories_keyboard(categories)
        )
        return

    if deep_link == "selector":
        await message.answer(
            "💎 *ПОДБОРЩИК БРАСЛЕТА*\n\nЧто тебе нужно?",
            parse_mode="Markdown",
            reply_markup=_get_selector_keyboard()
        )
        return

    if deep_link == "knowledge":
        await message.answer(
            "📚 *БАЗА ЗНАНИЙ*\n\nВыберите раздел:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📚 Открыть базу знаний", callback_data="knowledge")],
                [InlineKeyboardButton(text="🔍 Поиск по камням", callback_data="search_stones")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
        return

    if deep_link == "faq":
        await message.answer(
            "❓ *ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❓ Открыть FAQ", callback_data="faq")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # Парсим реферальный код и deep links с сайта
    ref_id = None
    deep_link = None
    if message.text and len(message.text.split()) > 1:
        try:
            ref_arg = message.text.split()[1]
            if ref_arg.startswith('ref'):
                ref_id = int(ref_arg.replace('ref', ''))
                if ref_id == user_id:
                    ref_id = None
            elif ref_arg in ('diagnostika', 'diagnostic', 'services', 'shop', 'selector', 'knowledge', 'faq'):
                deep_link = ref_arg
        except Exception:
            ref_id = None
    
    # Регистрируем пользователя
    is_new = not UserModel.get(user_id)
    UserModel.create_or_update(user_id, username, first_name, ref_id)
    
    # Начисляем бонусы за реферала
    if is_new and ref_id:
        from src.database.models import ReferralModel
        ReferralModel.add(ref_id, user_id)
        try:
            await bot.send_message(
                ref_id,
                "🎉 *По вашей реферальной ссылке зарегистрировался новый пользователь!*\n"
                "Вам начислено *100 бонусов*!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.debug("Не удалось уведомить реферера %s: %s", ref_id, e)
            pass
    
    # Отслеживаем в воронке
    await FunnelTracker.track(user_id, 'start')
    await state.clear()
    
    # Отправляем приветствие
    settings = SettingsModel.get_all()
    welcome_text = settings.get('welcome_text', '🌟 ДОБРО ПОЖАЛОВАТЬ!')
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

    if deep_link:
        await _send_deep_link_content(message, deep_link)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Вход в админ-панель."""
    if not UserModel.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    from src.keyboards.admin import get_admin_main_keyboard
    await message.answer(
        "⚙️ *АДМИН-ПАНЕЛЬ*",
        parse_mode="Markdown",
        reply_markup=get_admin_main_keyboard()
    )


@router.message(Command("links"))
@router.message(Command("link"))
async def cmd_links(message: Message):
    """Показывает список deep links для быстрого доступа к разделам."""
    bot_username = (await message.bot.get_me()).username
    base = f"https://t.me/{bot_username}?start="

    text = (
        "🔗 *DEEP LINKS*\n\n"
        f"🩺 Диагностика: {base}diagnostika\n"
        f"✨ Услуги: {base}services\n"
        f"💎 Витрина: {base}shop\n"
        f"🦊 Подбор камня: {base}selector\n"
        f"📚 База знаний: {base}knowledge\n"
        f"❓ FAQ: {base}faq\n\n"
        "🤝 Реферальная ссылка формируется автоматически в разделе РЕФЕРАЛЫ."
    )

    await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data.in_({
    "quiz", "wishmap", "custom_order", "streak", "ai_consult", "marathon",
    "astro_advice", "club", "music", "club_content", "admin_club", "admin_site"
}))
async def deprecated_callbacks(callback: CallbackQuery):
    """Совместимость со старыми кнопками из старых сообщений в чате."""
    data = callback.data or ""

    if data.startswith("admin_"):
        if not UserModel.is_admin(callback.from_user.id):
            await callback.answer("❌ Нет прав администратора", show_alert=True)
            return
        from src.keyboards.admin import get_admin_main_keyboard
        await callback.message.edit_text(
            "⚙️ Раздел обновлен. Используйте актуальное меню админ-панели.",
            reply_markup=get_admin_main_keyboard()
        )
        await callback.answer("Раздел обновлен")
        return

    await callback.message.edit_text(
        "ℹ️ Этот раздел был обновлен или удален.\n\nОткрыл актуальное главное меню.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer("Меню обновлено")


@router.callback_query(F.data == "menu")
async def menu_cb(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "👋 *Главное меню*",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "contact_master")
async def contact_master(callback: CallbackQuery, state: FSMContext):
    """Связь с мастером."""
    await state.set_state("waiting_contact_message")
    await callback.message.edit_text(
        "📞 *СВЯЗЬ С МАСТЕРОМ*\n\n"
        "Напишите ваш вопрос или запрос, и я передам его мастеру.\n"
        "Ответ придёт в течение 24 часов.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← ОТМЕНА", callback_data="menu")]
        ])
    )
    await callback.answer()


@router.message(F.text)
async def contact_message_received(message: Message, state: FSMContext, bot: Bot):
    """Получение сообщения для мастера."""
    current_state = await state.get_state()
    if current_state != "waiting_contact_message":
        return
    
    user_id = message.from_user.id
    user = UserModel.get(user_id)
    name = user['first_name'] or user['username'] or str(user_id)
    
    await bot.send_message(
        Config.ADMIN_ID,
        f"📞 *СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ*\n\n"
        f"👤 {name} (@{user['username']})\n"
        f"🆔 {user_id}\n\n"
        f"{message.text}"
    )
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено мастеру. Ожидайте ответа.",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "referral")
async def referral_info(callback: CallbackQuery):
    """Информация о реферальной программе."""
    user_id = callback.from_user.id
    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    
    with db.cursor() as c:
        c.execute("SELECT balance, total_earned, referral_count FROM referral_balance WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    
    if row:
        balance = row['balance']
        total_earned = row['total_earned']
        referral_count = row['referral_count']
    else:
        balance = total_earned = referral_count = 0
    
    text = (
        "🤝 *РЕФЕРАЛЬНАЯ ПРОГРАММА*\n\n"
        f"💰 *Ваш баланс:* {balance} бонусов\n"
        f"📊 *Всего заработано:* {total_earned} бонусов\n"
        f"👥 *Приглашено друзей:* {referral_count}\n\n"
        f"🔗 *Ваша реферальная ссылка:*\n`{ref_link}`\n\n"
        "За каждого приглашённого друга вы получаете 100 бонусов!"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="menu")]
        ])
    )
    await callback.answer()