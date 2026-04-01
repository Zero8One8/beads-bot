"""
Подборщик браслета под запрос — быстрый подбор за 1 шаг.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()

SELECTOR_MAP = {
    'sel_money': {
        'label': '💰 Деньги и успех',
        'stones': ['citrine', 'tiger_eye', 'pyrite', 'green_aventurine', 'natural_citrine'],
        'text': 'Эти камни работают с финансовым потоком, уверенностью и удачей в делах.'
    },
    'sel_love': {
        'label': '💞 Любовь и отношения',
        'stones': ['rose_quartz', 'moonstone', 'rhodonite', 'kunzite', 'pink_tourmaline'],
        'text': 'Эти камни открывают сердце, притягивают любовь и исцеляют сердечные раны.'
    },
    'sel_protect': {
        'label': '🛡 Защита',
        'stones': ['black_tourmaline', 'obsidian', 'hematite', 'schorl', 'morion'],
        'text': 'Эти камни создают мощный защитный экран от негатива, сглаза и чужой энергии.'
    },
    'sel_energy': {
        'label': '⚡ Энергия и сила',
        'stones': ['garnet', 'carnelian', 'tiger_eye', 'red_jasper', 'bull_eye'],
        'text': 'Эти камни наполняют жизненной силой, смелостью и желанием действовать.'
    },
    'sel_calm': {
        'label': '🌿 Спокойствие',
        'stones': ['amethyst', 'lepidolite', 'blue_aventurine', 'blue_chalcedony', 'kyanite'],
        'text': 'Эти камни успокаивают нервную систему, снимают тревогу и дают внутренний покой.'
    },
    'sel_spirit': {
        'label': '✨ Духовное развитие',
        'stones': ['labradorite', 'amethyst', 'moonstone', 'clear_quartz', 'spectrolite'],
        'text': 'Эти камни раскрывают интуицию, углубляют медитацию и усиливают связь с собой.'
    },
    'sel_health': {
        'label': '🌱 Здоровье и восстановление',
        'stones': ['clear_quartz', 'jade', 'green_tourmaline', 'chrysoprase', 'fluorite'],
        'text': 'Эти камни поддерживают исцеление, укрепляют жизненные силы и иммунитет.'
    },
    'sel_clarity': {
        'label': '🧠 Ясность и концентрация',
        'stones': ['fluorite', 'sodalite', 'clear_quartz', 'falcon_eye', 'blue_apatite'],
        'text': 'Эти камни организуют мысли, улучшают память и помогают принимать решения.'
    },
}


@router.callback_query(F.data == "selector")
async def selector_start(callback: CallbackQuery):
    """Быстрый подборщик браслета."""
    await callback.answer()
    await callback.message.edit_text(
        "💎 *ПОДБОРЩИК БРАСЛЕТА*\n\n"
        "Выбери, что тебе нужно — и я покажу подходящие камни.\n\n"
        "_Если хочешь максимально точный подбор — пройди кастомный заказ_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Деньги и успех", callback_data="sel_money"),
             InlineKeyboardButton(text="💞 Любовь", callback_data="sel_love")],
            [InlineKeyboardButton(text="🛡 Защита", callback_data="sel_protect"),
             InlineKeyboardButton(text="⚡ Энергия", callback_data="sel_energy")],
            [InlineKeyboardButton(text="🌿 Спокойствие", callback_data="sel_calm"),
             InlineKeyboardButton(text="✨ Духовный рост", callback_data="sel_spirit")],
            [InlineKeyboardButton(text="🌱 Здоровье", callback_data="sel_health"),
             InlineKeyboardButton(text="🧠 Ясность ума", callback_data="sel_clarity")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")],
        ])
    )



@router.callback_query(F.data.startswith("sel_") & ~F.data.startswith("sel_stone_"))
async def selector_result(callback: CallbackQuery):
    """Результат подборщика — список камней."""
    key = callback.data
    if key not in SELECTOR_MAP:
        await callback.answer()
        return

    cat = SELECTOR_MAP[key]
    stones_all = ContentLoader.load_all_stones()

    text = f"💎 *{cat['label'].upper()}*\n\n{cat['text']}\n\n*Подходящие камни:*\n\n"
    buttons = []

    for stone_id in cat['stones']:
        stone = stones_all.get(stone_id)
        if stone:
            emoji = stone.get('EMOJI', '💎')
            title = stone.get('TITLE', stone_id)
            short = stone.get('SHORT_DESC', '')
            text += f"{emoji} *{title}*\n_{short}_\n\n"
            buttons.append([InlineKeyboardButton(
                text=f"{emoji} Подробнее о {title}",
                callback_data=f"know_{stone_id}"
            )])

    buttons.append([InlineKeyboardButton(text="💎 ВИТРИНА", callback_data="showcase")])
    buttons.append([InlineKeyboardButton(text="🩺 ДИАГНОСТИКА — точный подбор", callback_data="diagnostic")])
    buttons.append([InlineKeyboardButton(text="← НАЗАД К ВЫБОРУ", callback_data="selector")])

    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

