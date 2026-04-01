"""
База знаний — просмотр камней из файлов knowledge_base.
С пагинацией по 12 камней на страницу.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()

PER_PAGE = 12


@router.callback_query(F.data == "knowledge")
async def knowledge_list(callback: CallbackQuery):
    """Список всех камней — первая страница."""
    await callback.answer()
    await _show_page(callback, 1)


@router.callback_query(F.data.startswith("knowledge_page_"))
async def knowledge_page(callback: CallbackQuery):
    """Пагинация по списку камней."""
    await callback.answer()
    page = int(callback.data.replace("knowledge_page_", ""))
    await _show_page(callback, page)


async def _show_page(callback: CallbackQuery, page: int):
    stones = ContentLoader.load_all_stones()

    if not stones:
        await callback.message.edit_text(
            "📚 *БАЗА ЗНАНИЙ*\n\nБаза знаний пока пуста.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")]
            ])
        )
        return

    stone_items = list(stones.items())
    total = len(stone_items)
    total_pages = (total + PER_PAGE - 1) // PER_PAGE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PER_PAGE
    page_stones = stone_items[offset:offset + PER_PAGE]

    text = f"📚 *БАЗА ЗНАНИЙ КАМНЕЙ*\n\n💎 Всего: {total} камней\n_Выбери камень для подробного описания:_\n"

    buttons = []
    row = []
    for stone_id, data in page_stones:
        title = data.get('TITLE', stone_id)
        emoji = data.get('EMOJI', '💎')
        label = f"{emoji} {title[:14]}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"know_{stone_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"knowledge_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"knowledge_page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="🔍 ПОИСК", callback_data="search_stones"),
        InlineKeyboardButton(text="← НАЗАД", callback_data="menu")
    ])

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("know_"))
async def knowledge_stone(callback: CallbackQuery):
    """Подробное описание камня."""
    await callback.answer()
    stone_id = callback.data.replace("know_", "")
    stone = ContentLoader.load_stone(stone_id)

    if not stone:
        await callback.answer("❌ Камень не найден", show_alert=True)
        return

    emoji = stone.get('EMOJI', '💎')
    title = stone.get('TITLE', stone_id)
    short_desc = stone.get('SHORT_DESC', '')
    full_desc = stone.get('FULL_DESC', '')
    properties = stone.get('PROPERTIES', '')
    chakra = stone.get('CHAKRA', '')
    zodiac = stone.get('ZODIAC', '')
    color = stone.get('COLOR', '')
    forms = stone.get('FORMS', '')
    price = stone.get('PRICE_PER_BEAD', '')
    notes = stone.get('NOTES', '')

    text = f"{emoji} *{title.upper()}*\n"
    if short_desc:
        text += f"_{short_desc}_\n\n"
    if full_desc:
        desc = full_desc[:2200] + "..." if len(full_desc) > 2200 else full_desc
        text += f"{desc}\n\n"

    details = []
    if properties:
        details.append(f"✨ *Свойства:* {properties}")
    if chakra:
        details.append(f"🌀 *Чакры:* {chakra}")
    if zodiac:
        details.append(f"♈ *Зодиак:* {zodiac}")
    if color:
        details.append(f"🎨 *Цвет:* {color}")
    if forms:
        details.append(f"📿 *Размеры:* {forms}")
    if price and str(price) not in ('0', ''):
        details.append(f"💰 *Цена за бусину:* {price} руб.")
    if notes:
        details.append(f"💡 *Заметка мастера:* _{notes}_")
    if details:
        text += "\n".join(details)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 ЗАКАЗАТЬ БРАСЛЕТ", callback_data="showcase")],
            [InlineKeyboardButton(text="🔮 СОВМЕСТИМОСТЬ", callback_data="compatibility")],
            [InlineKeyboardButton(text="← К СПИСКУ", callback_data="knowledge")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )
