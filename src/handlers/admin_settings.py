"""
Админ-панель: общие настройки бота.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.database.db import db
from src.database.models import UserModel, SettingsModel
from src.utils.helpers import escape_markdown

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    waiting_setting_value = State()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Главное меню настроек."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    
    settings = SettingsModel.get_all()
    
    text = (
        "⚙️ *ОБЩИЕ НАСТРОЙКИ БОТА*\n\n"
        f"👋 *Приветствие новых:*\n{escape_markdown(settings['welcome_text'][:100])}...\n\n"
        f"🔄 *Приветствие вернувшихся:*\n{escape_markdown(settings['return_text'][:100])}...\n\n"
        f"💰 *Кэшбэк:* {settings['cashback_percent']}% (мин. заказ {settings['min_order_for_cashback']}₽)\n"
        f"📞 *Контакты мастера:* {settings['contact_master']}\n"
        f"🚚 *Информация о доставке:*\n{escape_markdown(settings['delivery_info'][:50])}...\n"
    )
    
    buttons = [
        [InlineKeyboardButton(text="👋 Приветствие новых", callback_data="settings_edit_welcome_text")],
        [InlineKeyboardButton(text="🔄 Приветствие вернувшихся", callback_data="settings_edit_return_text")],
        [InlineKeyboardButton(text="💰 Процент кэшбэка", callback_data="settings_edit_cashback_percent")],
        [InlineKeyboardButton(text="📞 Контакт мастера", callback_data="settings_edit_contact_master")],
        [InlineKeyboardButton(text="🚚 Информация о доставке", callback_data="settings_edit_delivery_info")],
        [InlineKeyboardButton(text="🌐 Данные для сайта", callback_data="admin_bot_info")],
        [InlineKeyboardButton(text="📸 Инструкции по фото", callback_data="admin_photo_guide")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_menu")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("settings_edit_"))
async def settings_edit(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование настройки."""
    setting_key = callback.data.replace("settings_edit_", "")
    await state.update_data(setting_key=setting_key)
    await state.set_state(SettingsStates.waiting_setting_value)
    
    prompts = {
        'welcome_text': '✏️ Введите новый текст приветствия для новых пользователей:',
        'return_text': '✏️ Введите новый текст приветствия для вернувшихся пользователей:',
        'cashback_percent': '✏️ Введите процент кэшбэка (только число, например 5):',
        'min_order_for_cashback': '✏️ Введите минимальную сумму заказа для начисления кэшбэка (в рублях):',
        'contact_master': '✏️ Введите контакт мастера (например @username):',
        'delivery_info': '✏️ Введите информацию о доставке:',
        'contact_phone': '✏️ Введите номер телефона (например +7 999 123 45 67):',
        'contact_email': '✏️ Введите email (например info@magic-stones.ru):',
        'contact_address': '✏️ Введите адрес (или напишите "онлайн"):',
        'working_hours': '✏️ Введите часы работы (например: Ежедневно 10:00-22:00):'
    }
    
    await callback.message.edit_text(prompts.get(setting_key, "Введите новое значение:"))
    await callback.answer()


@router.message(SettingsStates.waiting_setting_value)
async def settings_save(message: Message, state: FSMContext):
    """Сохранить новое значение настройки."""
    data = await state.get_data()
    setting_key = data['setting_key']
    new_value = message.text
    
    # Валидация для числовых полей
    if setting_key in ['cashback_percent', 'min_order_for_cashback']:
        try:
            int(new_value)
        except ValueError:
            await message.answer("❌ Введите число!")
            return
    
    success = SettingsModel.set(setting_key, new_value)
    await state.clear()
    
    if success:
        await message.answer(
            f"✅ *Настройка {setting_key} обновлена!*",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К НАСТРОЙКАМ", callback_data="admin_settings")]
            ])
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К НАСТРОЙКАМ", callback_data="admin_settings")]
            ])
        )

# ──────────────────────────────────────────────────────────────
# УПРАВЛЕНИЕ ФОТО И ИНСТРУКЦИЯМИ ДЛЯ КЛИЕНТОВ
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_photo_guide")
async def admin_photo_guide(callback: CallbackQuery):
    """Инструкции для клиентов по загрузке фото."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    text = (
        "📸 *ИНСТРУКЦИИ ПО ФОТО ДЛЯ КЛИЕНТОВ*\n\n"
        "Клиенты загружают фото в двух разделах:\n\n"
        "🔮 *ДИАГНОСТИКА* — 2 фото:\n"
        "• Фото 1: лицо крупным планом\n"
        "• Фото 2: в полный рост (опционально)\n"
        "Назначение: мастер видит энергетику клиента\n\n"
        "💍 *КАСТОМНЫЙ ЗАКАЗ* — 2 фото:\n"
        "• Фото 1: запястье (для размера)\n"
        "• Фото 2: любое фото для вдохновения\n"
        "Назначение: точный подбор камней\n\n"
        "📋 *Технические требования:*\n"
        "• Любой формат (JPG, PNG)\n"
        "• Telegram сжимает автоматически\n"
        "• Достаточно обычного смартфона\n\n"
        "Все фото приходят к вам в разделе\n"
        "🩺 ДИАГНОСТИКА и 💍 КАСТОМНЫЕ ЗАКАЗЫ"
    )

    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🩺 Посмотреть диагностики", callback_data="admin_diagnostics")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_settings")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "admin_bot_info")
async def admin_bot_info(callback: CallbackQuery):
    """Информация о боте и управление контактами для сайта."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    from src.database.db import db
    with db.cursor() as c:
        c.execute("SELECT key, value FROM bot_settings WHERE key IN ('contact_phone','contact_email','contact_address','working_hours')")
        settings_rows = c.fetchall()

    settings = {r['key']: r['value'] for r in settings_rows}

    text = (
        "🌐 *ДАННЫЕ ДЛЯ САЙТА И КОНТАКТОВ*\n\n"
        f"📱 Телефон: {settings.get('contact_phone', 'не указан')}\n"
        f"📧 Email: {settings.get('contact_email', 'не указан')}\n"
        f"📍 Адрес: {settings.get('contact_address', 'не указан')}\n"
        f"🕒 Часы работы: {settings.get('working_hours', 'не указаны')}\n\n"
        "Эти данные используются при генерации сайта."
    )

    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="settings_edit_contact_phone")],
            [InlineKeyboardButton(text="📧 Изменить email", callback_data="settings_edit_contact_email")],
            [InlineKeyboardButton(text="📍 Изменить адрес", callback_data="settings_edit_contact_address")],
            [InlineKeyboardButton(text="🕒 Часы работы", callback_data="settings_edit_working_hours")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_settings")]
        ])
    )
    await callback.answer()
