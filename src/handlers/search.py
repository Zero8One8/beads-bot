"""
Поиск по базе знаний — написать название или свойство камня.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()


class SearchStates(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "search_stones")
async def search_start(callback: CallbackQuery, state: FSMContext):
    """Начало поиска."""
    await state.set_state(SearchStates.waiting_query)
    await callback.message.edit_text(
        "🔍 *ПОИСК ПО БАЗЕ КАМНЕЙ*\n\n"
        "Напиши название камня или свойство:\n\n"
        "_Примеры:_\n"
        "• `аметист`\n"
        "• `защита`\n"
        "• `деньги`\n"
        "• `розовый`\n"
        "• `сердце`\n"
        "• `тревога`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← ОТМЕНА", callback_data="knowledge")]
        ])
    )
    await callback.answer()


@router.message(SearchStates.waiting_query)
async def search_process(message: Message, state: FSMContext):
    """Поиск по базе знаний."""
    await state.clear()
    query = message.text.strip().lower()

    if len(query) < 2:
        await message.answer(
            "Запрос слишком короткий. Напиши хотя бы 2 символа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← К БАЗЕ", callback_data="knowledge")]
            ])
        )
        return

    stones = ContentLoader.load_all_stones()
    results = []

    for stone_id, data in stones.items():
        title = data.get('TITLE', '').lower()
        props = data.get('PROPERTIES', '').lower()
        short = data.get('SHORT_DESC', '').lower()
        full = data.get('FULL_DESC', '').lower()
        color = data.get('COLOR', '').lower()
        chakra = data.get('CHAKRA', '').lower()
        notes = data.get('NOTES', '').lower()

        score = 0
        if query in title: score += 10
        if query in props: score += 6
        if query in short: score += 4
        if query in color: score += 3
        if query in chakra: score += 3
        if query in notes: score += 2
        if query in full: score += 1

        if score > 0:
            results.append((score, stone_id, data))

    results.sort(key=lambda x: x[0], reverse=True)

    if not results:
        await message.answer(
            f"🔍 По запросу *«{query}»* ничего не найдено.\n\n"
            "Попробуй другое слово или посмотри весь список.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📚 ВСЯ БАЗА", callback_data="knowledge")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
        return

    top = results[:5]
    text = f"🔍 *Найдено по запросу «{query}»:*\n\n"
    buttons = []

    for score, stone_id, data in top:
        emoji = data.get('EMOJI', '💎')
        title = data.get('TITLE', stone_id)
        short = data.get('SHORT_DESC', '')
        text += f"{emoji} *{title}*\n_{short}_\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {title}",
            callback_data=f"know_{stone_id}"
        )])

    if len(results) > 5:
        text += f"_...и ещё {len(results) - 5} камней_"

    buttons.append([InlineKeyboardButton(text="🔍 НОВЫЙ ПОИСК", callback_data="search_stones")])
    buttons.append([InlineKeyboardButton(text="← К БАЗЕ", callback_data="knowledge")])

    await message.answer(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
