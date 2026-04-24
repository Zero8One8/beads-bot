"""
Админ-раздел для управления контентом сайта через Supabase site_content.
"""
import json
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.database.models import UserModel
from src.services.site_content import SiteContentClient, SITE_CONTENT_SECTIONS

logger = logging.getLogger(__name__)
router = Router()


class AdminSiteStates(StatesGroup):
    waiting_json = State()


def _back_to_site_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К сайту", callback_data="admin_site")]
    ])


def _truncate_json(content: object, limit: int = 3200) -> str:
    pretty = json.dumps(content, ensure_ascii=False, indent=2)
    if len(pretty) <= limit:
        return pretty
    return pretty[:limit] + "\n...\n[обрезано]"


@router.callback_query(F.data == "admin_site")
async def admin_site_menu(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    if not SiteContentClient.is_configured():
        await callback.message.edit_text(
            "🌐 УПРАВЛЕНИЕ САЙТОМ\n\n"
            "Не настроены переменные SUPABASE_URL и/или SUPABASE_SERVICE_ROLE_KEY.\n"
            "Без них бот не сможет редактировать site_content.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu")]
            ])
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=f"🌐 {meta['label']}", callback_data=f"admin_site_section_{key}")]
        for key, meta in SITE_CONTENT_SECTIONS.items()
    ]
    buttons.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu")])

    await callback.message.edit_text(
        "🌐 УПРАВЛЕНИЕ САЙТОМ\n\n"
        "Здесь можно менять контент сайта, который читает фронтенд из site_content.\n"
        "Формат редактирования: JSON по секциям.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_section_"))
async def admin_site_section(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_section_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    try:
        row = await SiteContentClient.get_content(content_key)
    except Exception as exc:
        logger.error("site_content read error for %s: %s", content_key, exc)
        await callback.answer("❌ Не удалось загрузить секцию", show_alert=True)
        return

    current_content = row["content"] if row else meta["template"]
    updated_by = row.get("updated_by") if row else "fallback"
    updated_at = row.get("updated_at") if row else "используется fallback сайта"

    text = (
        f"🌐 {meta['label']}\n\n"
        f"{meta['description']}\n\n"
        f"Обновил: {updated_by}\n"
        f"Когда: {updated_at}\n\n"
        f"Текущее значение:\n{_truncate_json(current_content)}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать JSON", callback_data=f"admin_site_edit_{content_key}")],
            [InlineKeyboardButton(text="📋 Показать шаблон", callback_data=f"admin_site_template_{content_key}")],
            [InlineKeyboardButton(text="🔙 К разделам сайта", callback_data="admin_site")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_template_"))
async def admin_site_template(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_template_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    await callback.message.edit_text(
        f"📋 ШАБЛОН: {meta['label']}\n\n{_truncate_json(meta['template'])}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать JSON", callback_data=f"admin_site_edit_{content_key}")],
            [InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_edit_"))
async def admin_site_edit(callback: CallbackQuery, state: FSMContext):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_edit_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    await state.set_state(AdminSiteStates.waiting_json)
    await state.update_data(site_content_key=content_key)

    await callback.message.edit_text(
        f"✏️ РЕДАКТИРОВАНИЕ: {meta['label']}\n\n"
        f"Отправьте одним сообщением валидный JSON для секции `{content_key}`.\n\n"
        f"Подсказка: если записи ещё нет, используйте шаблон как основу.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Показать шаблон", callback_data=f"admin_site_template_{content_key}")],
            [InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")],
        ])
    )
    await callback.answer()


@router.message(AdminSiteStates.waiting_json)
async def admin_site_save(message: Message, state: FSMContext):
    if not UserModel.is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    data = await state.get_data()
    content_key = data.get("site_content_key")
    if not content_key:
        await state.clear()
        await message.answer("❌ Потерян контекст редактирования", reply_markup=_back_to_site_kb())
        return

    try:
        content = json.loads(message.text)
    except json.JSONDecodeError as exc:
        await message.answer(
            f"❌ JSON невалидный: {exc.msg} (строка {exc.lineno}, колонка {exc.colno})\n\n"
            f"Исправьте JSON и отправьте ещё раз.",
            reply_markup=_back_to_site_kb()
        )
        return

    try:
        updated_by = message.from_user.username or str(message.from_user.id)
        await SiteContentClient.upsert_content(content_key, content, updated_by)
    except Exception as exc:
        logger.error("site_content upsert error for %s: %s", content_key, exc)
        await message.answer("❌ Не удалось сохранить секцию сайта", reply_markup=_back_to_site_kb())
        return

    await state.clear()
    await message.answer(
        f"✅ Секция `{content_key}` сохранена. Сайт начнёт брать новые данные из site_content.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 К разделам сайта", callback_data="admin_site")]
        ])
    )