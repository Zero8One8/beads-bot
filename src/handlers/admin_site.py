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
from src.services.site_content import SiteContentClient, SITE_CONTENT_SECTIONS, validate_content

logger = logging.getLogger(__name__)
router = Router()


class AdminSiteStates(StatesGroup):
    waiting_json = State()        # ожидает JSON для публикации
    waiting_json_draft = State()  # ожидает JSON для сохранения черновика


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
            parse_mode=None,
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
        parse_mode=None,
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
        details = str(exc)[:180] if str(exc) else exc.__class__.__name__
        await callback.message.edit_text(
            f"❌ Не удалось загрузить секцию `{content_key}`.\n\nПричина: {details}",
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Повторить", callback_data=f"admin_site_section_{content_key}")],
                [InlineKeyboardButton(text="🔙 К разделам сайта", callback_data="admin_site")],
            ])
        )
        await callback.answer()
        return

    current_content = row["content"] if row else meta["template"]
    updated_by = row.get("updated_by") if row else "fallback"
    updated_at = row.get("updated_at") if row else "используется fallback сайта"

    has_draft = bool(row and row.get("draft_content"))
    draft_line = ""
    if has_draft:
        draft_by = row.get("draft_updated_by") or "?"
        draft_at = (row.get("draft_updated_at") or "?")[:16]
        draft_line = f"\n\n📝 Черновик от {draft_by} ({draft_at})"

    text = (
        f"🌐 {meta['label']}\n\n"
        f"{meta['description']}\n\n"
        f"Обновил: {updated_by}\n"
        f"Когда: {updated_at}"
        f"{draft_line}\n\n"
        f"Текущее значение:\n{_truncate_json(current_content)}"
    )

    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать и опубликовать", callback_data=f"admin_site_edit_{content_key}")],
        [InlineKeyboardButton(text="📝 Сохранить как черновик", callback_data=f"admin_site_edit_draft_{content_key}")],
    ]
    if has_draft:
        buttons.append([InlineKeyboardButton(text="👁 Посмотреть черновик", callback_data=f"admin_site_preview_draft_{content_key}")])
        buttons.append([InlineKeyboardButton(text="📤 Опубликовать черновик", callback_data=f"admin_site_publish_draft_{content_key}")])
    buttons.append([InlineKeyboardButton(text="📋 Показать шаблон", callback_data=f"admin_site_template_{content_key}")])
    buttons.append([InlineKeyboardButton(text="🕓 История версий", callback_data=f"admin_site_history_{content_key}")])
    buttons.append([InlineKeyboardButton(text="🔙 К разделам сайта", callback_data="admin_site")])

    await callback.message.edit_text(text, parse_mode=None, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
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
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать и опубликовать", callback_data=f"admin_site_edit_{content_key}")],
            [InlineKeyboardButton(text="📝 Сохранить как черновик", callback_data=f"admin_site_edit_draft_{content_key}")],
            [InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_edit_draft_"))
async def admin_site_edit_draft(callback: CallbackQuery, state: FSMContext):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_edit_draft_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    await state.set_state(AdminSiteStates.waiting_json_draft)
    await state.update_data(site_content_key=content_key)

    await callback.message.edit_text(
        f"📝 ЧЕРНОВИК: {meta['label']}\n\n"
        f"Отправьте JSON. Будет сохранён как черновик (не опубликован).\n"
        f"Чтобы опубликовать черновик — используйте кнопку в разделе секции.",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Показать шаблон", callback_data=f"admin_site_template_{content_key}")],
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
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Показать шаблон", callback_data=f"admin_site_template_{content_key}")],
            [InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_preview_draft_"))
async def admin_site_preview_draft(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_preview_draft_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    try:
        row = await SiteContentClient.get_content(content_key)
    except Exception as exc:
        await callback.answer(f"❌ Ошибка: {exc}", show_alert=True)
        return

    if not row or not row.get("draft_content"):
        await callback.answer("Черновика нет", show_alert=True)
        return

    draft_by = row.get("draft_updated_by") or "?"
    draft_at = (row.get("draft_updated_at") or "?")[:16]

    await callback.message.edit_text(
        f"👁 ЧЕРНОВИК: {meta['label']}\nАвтор: {draft_by} ({draft_at})\n\n"
        f"{_truncate_json(row['draft_content'])}",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Опубликовать черновик", callback_data=f"admin_site_publish_draft_{content_key}")],
            [InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_publish_draft_"))
async def admin_site_publish_draft(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_publish_draft_", "")
    updated_by = callback.from_user.username or str(callback.from_user.id)

    try:
        await SiteContentClient.publish_draft(content_key, updated_by)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except Exception as exc:
        logger.error("publish_draft error for %s: %s", content_key, exc)
        await callback.answer("❌ Не удалось опубликовать черновик", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Черновик секции `{content_key}` опубликован. Сайт начнёт брать новые данные.",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 К разделам сайта", callback_data="admin_site")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_history_"))
async def admin_site_history(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    content_key = callback.data.replace("admin_site_history_", "")
    meta = SITE_CONTENT_SECTIONS.get(content_key)
    if not meta:
        await callback.answer("❌ Неизвестная секция", show_alert=True)
        return

    try:
        history = await SiteContentClient.get_history(content_key, limit=5)
    except Exception as exc:
        await callback.answer(f"❌ Ошибка: {exc}", show_alert=True)
        return

    if not history:
        await callback.answer("История пуста — изменений ещё не было", show_alert=True)
        return

    buttons = []
    for item in history:
        saved_at = (item.get("saved_at") or "?")[:16]
        saved_by = item.get("saved_by") or "?"
        buttons.append([
            InlineKeyboardButton(
                text=f"⏪ {saved_at} ({saved_by})",
                callback_data=f"admin_site_rollback_{content_key}_{item['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 К секции", callback_data=f"admin_site_section_{content_key}")])

    await callback.message.edit_text(
        f"🕓 ИСТОРИЯ: {meta['label']}\n\nВыберите версию для отката:",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_site_rollback_"))
async def admin_site_rollback(callback: CallbackQuery):
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Format: admin_site_rollback_{content_key}_{history_id}
    rest = callback.data.replace("admin_site_rollback_", "")
    # history_id is UUID with '-' separators, split by the last underscore.
    if "_" not in rest:
        await callback.answer("❌ Неверный формат callback", show_alert=True)
        return
    content_key, history_id = rest.rsplit("_", 1)

    if not content_key or not history_id:
        await callback.answer("❌ Неверный формат callback", show_alert=True)
        return

    updated_by = callback.from_user.username or str(callback.from_user.id)

    try:
        await SiteContentClient.rollback_to(history_id, content_key, updated_by)
    except Exception as exc:
        logger.error("rollback error for %s/%s: %s", content_key, history_id, exc)
        await callback.answer(f"❌ Откат не удался: {exc}", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Секция `{content_key}` откатана к выбранной версии.",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 К разделам сайта", callback_data="admin_site")]
        ])
    )
    await callback.answer()


async def _handle_json_save(message: Message, state: FSMContext, as_draft: bool):
    """Общая логика для сохранения JSON (публикация или черновик)."""
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
            parse_mode=None,
            reply_markup=_back_to_site_kb()
        )
        return

    # Валидация схемы
    errors = validate_content(content_key, content)
    if errors:
        error_list = "\n".join(f"• {e}" for e in errors[:10])
        await message.answer(
            f"❌ Ошибки структуры JSON для `{content_key}`:\n\n{error_list}\n\n"
            f"Исправьте и отправьте ещё раз.",
            parse_mode=None,
            reply_markup=_back_to_site_kb()
        )
        return

    updated_by = message.from_user.username or str(message.from_user.id)

    try:
        if as_draft:
            await SiteContentClient.save_draft(content_key, content, updated_by)
        else:
            await SiteContentClient.upsert_content(content_key, content, updated_by)
    except Exception as exc:
        logger.error("site_content save error for %s: %s", content_key, exc)
        await message.answer("❌ Не удалось сохранить секцию сайта", parse_mode=None, reply_markup=_back_to_site_kb())
        return

    await state.clear()

    if as_draft:
        text = (
            f"📝 Черновик `{content_key}` сохранён. Опубликуйте его из раздела секции."
        )
    else:
        text = (
            f"✅ Секция `{content_key}` сохранена. Сайт начнёт брать новые данные из site_content."
        )

    await message.answer(
        text,
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 К разделам сайта", callback_data="admin_site")]
        ])
    )


@router.message(AdminSiteStates.waiting_json)
async def admin_site_save(message: Message, state: FSMContext):
    await _handle_json_save(message, state, as_draft=False)


@router.message(AdminSiteStates.waiting_json_draft)
async def admin_site_save_draft(message: Message, state: FSMContext):
    await _handle_json_save(message, state, as_draft=True)



