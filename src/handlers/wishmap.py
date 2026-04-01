"""
Карта желаний — пользователь описывает цель/мечту,
бот подбирает набор камней + конкретную инструкцию по работе.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()

# База карт желаний — цель → набор камней + инструкция
WISHMAP_DATA = {
    'wish_love': {
        'title': '💞 Найти любовь / Укрепить отношения',
        'stones': ['rose_quartz', 'moonstone', 'rhodonite'],
        'instruction': (
            "💞 *КАРТА ЖЕЛАНИЯ: ЛЮБОВЬ*\n\n"
            "Твой набор камней подобран. Вот как с ним работать:\n\n"
            "📿 *Браслет:* Розовый кварц в центре, лунный камень и родонит по бокам.\n\n"
            "🌅 *Утром:* Надень браслет, возьми розовый кварц в левую руку. "
            "Скажи вслух или про себя: _«Я открыт(а) для любви. Я достоин(на) любви. "
            "Любовь уже идёт ко мне»_. 1 минута.\n\n"
            "🌙 *Перед сном:* Положи лунный камень под подушку. "
            "Он откроет ты к получению любви во сне.\n\n"
            "📅 *Цикл:* Работай с набором 28 дней (один лунный цикл). "
            "На новолуние — очищай камни под проточной водой. "
            "На полнолуние — оставляй на подоконнике на ночь.\n\n"
            "⚡ *Важно:* Родонит работает с тем, что мешает любви внутри тебя. "
            "Первые 7 дней могут всплыть старые обиды — это нормально, это исцеление."
        )
    },
    'wish_money': {
        'title': '💰 Деньги / Финансовый рост',
        'stones': ['citrine', 'tiger_eye', 'pyrite'],
        'instruction': (
            "💰 *КАРТА ЖЕЛАНИЯ: ДЕНЬГИ*\n\n"
            "📿 *Браслет:* Цитрин — основа, тигровый глаз и пирит чередовать.\n\n"
            "🌅 *Утром:* Надень браслет на правую руку (рука действия). "
            "Перед выходом из дома подержи пирит в правой руке 30 секунд и скажи: "
            "_«Я притягиваю деньги. Мои действия приносят результат»_.\n\n"
            "💼 *На важных встречах:* Тигровый глаз в кармане — он обостряет "
            "деловую интуицию и помогает видеть выгодные возможности.\n\n"
            "💳 *В кошельке:* Положи маленький кусочек цитрина или пирита рядом с деньгами.\n\n"
            "📅 *Цикл:* Работай 21 день не снимая. На убывающей луне — "
            "чисти камни (убывает старое, ненужное). "
            "На растущей — заряжай намерением роста.\n\n"
            "⚡ *Важно:* Цитрин не накапливает негатив — единственный такой камень. "
            "Не нужно часто чистить. Но если чувствуешь тяжесть — промой под водой."
        )
    },
    'wish_protect': {
        'title': '🛡 Защита / Очищение пространства',
        'stones': ['black_tourmaline', 'obsidian', 'hematite'],
        'instruction': (
            "🛡 *КАРТА ЖЕЛАНИЯ: ЗАЩИТА*\n\n"
            "📿 *Браслет:* Чёрный турмалин — основа. Гематит и обсидиан — чередовать.\n\n"
            "🏠 *Дом:* По одному чёрному турмалину в каждый угол комнаты или квартиры. "
            "Они создадут защитный периметр.\n\n"
            "💻 *Работа:* Кусок турмалина рядом с компьютером — поглощает электромагнитное излучение.\n\n"
            "🧍 *На себе:* Носи на правой руке — правая отдаёт и защищает. "
            "Гематит заземляет и не позволяет чужой энергии «прилипать».\n\n"
            "🌙 *Очищение:* Обсидиан — мощный, но требует регулярной очистки. "
            "Раз в неделю клади на землю или под проточную воду на 5 минут.\n\n"
            "⚡ *Важно:* Если носишь постоянно — турмалин нужно чистить чаще. "
            "Он буквально «впитывает» чужой негатив. Тяжёлый камень = много поглощено. "
            "Очисти немедленно."
        )
    },
    'wish_health': {
        'title': '🌱 Здоровье / Восстановление сил',
        'stones': ['clear_quartz', 'jade', 'green_tourmaline'],
        'instruction': (
            "🌱 *КАРТА ЖЕЛАНИЯ: ЗДОРОВЬЕ*\n\n"
            "📿 *Браслет:* Горный хрусталь в центре — усилитель. "
            "Нефрит и зелёный турмалин по бокам.\n\n"
            "🌅 *Утром:* Надень браслет на левую руку (принимающая). "
            "Горный хрусталь поднеси к больному месту на 2-3 минуты, "
            "визуализируй как белый свет входит в тело.\n\n"
            "🍃 *Нефрит:* Носи постоянно — это камень долголетия. "
            "В Китае его давали детям, чтобы они росли здоровыми. "
            "Особенно хорош для почек и пищеварения.\n\n"
            "💆 *Массаж:* Холодный нефрит на лоб при головной боли. "
            "Горный хрусталь — на суставы при болях.\n\n"
            "📅 *Цикл:* Работай без перерыва, можно носить постоянно. "
            "Очищай в полнолуние лунным светом.\n\n"
            "⚡ *Важно:* Камни поддерживают, но не заменяют врача. "
            "Используй параллельно с лечением."
        )
    },
    'wish_calm': {
        'title': '🌊 Покой / Снятие стресса и тревоги',
        'stones': ['amethyst', 'lepidolite', 'blue_aventurine'],
        'instruction': (
            "🌊 *КАРТА ЖЕЛАНИЯ: ПОКОЙ*\n\n"
            "📿 *Браслет:* Аметист — основа. Лепидолит и синий авантюрин чередовать.\n\n"
            "😰 *При тревоге:* Лепидолит в обе ладони, сожми. "
            "Медленно дыши 4-7-8 (вдох 4 счёта, задержка 7, выдох 8). "
            "Литий в камне буквально успокаивает нервную систему.\n\n"
            "🌙 *Перед сном:* Аметист под подушку. "
            "Если бывают ночные тревоги — лепидолит тоже рядом.\n\n"
            "🛁 *Ванна:* Положи аметист у края ванны, "
            "не в воду (некоторые камни не переносят долгое замачивание). "
            "Его присутствие рядом уже работает.\n\n"
            "📅 *Цикл:* Особенно важны первые 14 дней. "
            "Потом нервная система перестраивается и становится легче.\n\n"
            "⚡ *Важно:* Лепидолит работает накопительно — "
            "с каждым днём эффект усиливается. Не снимай первые 3 недели."
        )
    },
    'wish_spirit': {
        'title': '✨ Духовный рост / Интуиция / Своё предназначение',
        'stones': ['labradorite', 'amethyst', 'clear_quartz'],
        'instruction': (
            "✨ *КАРТА ЖЕЛАНИЯ: ДУХОВНЫЙ РОСТ*\n\n"
            "📿 *Браслет:* Лабрадорит — основа. "
            "Аметист и горный хрусталь как усилители.\n\n"
            "🧘 *Медитация:* Держи лабрадорит в левой руке. "
            "Закрой глаза. Представь как переливы камня раскрываются внутри тебя — "
            "как дверь в другое измерение. Минимум 10 минут ежедневно.\n\n"
            "📓 *Дневник снов:* Горный хрусталь у кровати. "
            "Сразу после пробуждения запиши сон — камень помогает вспомнить детали. "
            "Лабрадорит открывает доступ к информации из снов.\n\n"
            "🌀 *Работа с третьим глазом:* Аметист приложи ко лбу на 5 минут "
            "в тишине. Появляются образы, ощущения — это нормально, это интуиция.\n\n"
            "📅 *Цикл:* Духовная работа — это марафон, не спринт. "
            "Работай минимум 40 дней без перерыва.\n\n"
            "⚡ *Важно:* Лабрадорит — мощный камень. "
            "Первые дни могут быть яркие сны, обострение чувствительности. "
            "Это признак что камень работает."
        )
    },
    'wish_confidence': {
        'title': '💪 Уверенность / Самооценка / Сила',
        'stones': ['tiger_eye', 'carnelian', 'garnet'],
        'instruction': (
            "💪 *КАРТА ЖЕЛАНИЯ: УВЕРЕННОСТЬ*\n\n"
            "📿 *Браслет:* Тигровый глаз — основа. Сердолик и гранат — огонь.\n\n"
            "🌅 *Утром:* Перед зеркалом. Надень браслет на правую руку. "
            "Посмотри себе в глаза 30 секунд молча. "
            "Камни в этот момент усиливают всё что ты чувствуешь — "
            "позволь себе почувствовать силу.\n\n"
            "⚡ *Перед важным событием:* Гранат в левую руку на 1 минуту — "
            "он активирует корневую чакру и даёт ощущение опоры под ногами.\n\n"
            "🎯 *На важных встречах:* Тигровый глаз в кармане — "
            "он не даёт поддаться на манипуляции и видит истинные намерения людей.\n\n"
            "📅 *Цикл:* 30 дней. После — сделай перерыв 7 дней. "
            "Потом снова если нужно.\n\n"
            "⚡ *Важно:* Сердолик — самый активный из трёх. "
            "Если чувствуешь что «перегреваешься» (раздражительность, жар) — "
            "сними браслет на день, дай себе и камню отдохнуть."
        )
    },
    'wish_career': {
        'title': '🚀 Карьера / Реализация / Новое дело',
        'stones': ['citrine', 'tiger_eye', 'sodalite'],
        'instruction': (
            "🚀 *КАРТА ЖЕЛАНИЯ: КАРЬЕРА*\n\n"
            "📿 *Браслет:* Цитрин — магнит возможностей. "
            "Тигровый глаз — деловая хватка. Содалит — чёткость в коммуникации.\n\n"
            "📋 *Рабочий стол:* Цитрин в левом углу стола — он там «работает» "
            "даже когда ты не в офисе, притягивая возможности.\n\n"
            "💼 *На переговорах:* Тигровый глаз в правом кармане. "
            "Содалит — для ясной речи, помогает формулировать мысли точно.\n\n"
            "🌙 *Вечером:* Запиши 3 конкретных действия на завтра. "
            "Держи при этом цитрин — он усиливает намерение и делает мысли реальностью.\n\n"
            "📅 *Цикл:* 28 дней. Отмечай прогресс — камни работают постепенно, "
            "но точно. На 7-й день обычно появляется первый результат.\n\n"
            "⚡ *Важно:* Содалит поможет найти своё истинное призвание, "
            "если ты ещё в поиске. Носи его с намерением «найти своё»."
        )
    },
}


class WishmapStates(StatesGroup):
    choosing_wish = State()


@router.callback_query(F.data == "wishmap")
async def wishmap_start(callback: CallbackQuery):
    """Карта желаний — выбор цели."""
    await callback.answer()
    await callback.message.edit_text(
        "🗺 *КАРТА ЖЕЛАНИЯ*\n\n"
        "Выбери свою главную цель — получишь персональный набор камней "
        "и точную инструкцию как с ними работать.\n\n"
        "_Это не просто список камней — это рабочий протокол._",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💞 Найти любовь / Отношения", callback_data="wish_love")],
            [InlineKeyboardButton(text="💰 Деньги / Финансовый рост", callback_data="wish_money")],
            [InlineKeyboardButton(text="🛡 Защита / Очищение", callback_data="wish_protect")],
            [InlineKeyboardButton(text="🌱 Здоровье / Восстановление", callback_data="wish_health")],
            [InlineKeyboardButton(text="🌊 Покой / Антистресс", callback_data="wish_calm")],
            [InlineKeyboardButton(text="✨ Духовный рост / Интуиция", callback_data="wish_spirit")],
            [InlineKeyboardButton(text="💪 Уверенность / Самооценка", callback_data="wish_confidence")],
            [InlineKeyboardButton(text="🚀 Карьера / Новое дело", callback_data="wish_career")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")],
        ])
    )



@router.callback_query(F.data.startswith("wish_") & ~F.data.startswith("wishmap"))
async def wishmap_result(callback: CallbackQuery):
    """Показать карту желания с инструкцией."""
    key = callback.data
    if key not in WISHMAP_DATA:
        await callback.answer()
        return

    data = WISHMAP_DATA[key]
    stones_all = ContentLoader.load_all_stones()

    stones_text = ""
    for stone_id in data['stones']:
        stone = stones_all.get(stone_id)
        if stone:
            emoji = stone.get('EMOJI', '💎')
            title = stone.get('TITLE', stone_id)
            short = stone.get('SHORT_DESC', '')
            stones_text += f"{emoji} *{title}* — {short}\n"

    full_text = f"{data['instruction']}\n\n*Твой набор:*\n{stones_text}"

    await callback.answer()
    await callback.message.edit_text(
        full_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💍 ЗАКАЗАТЬ ЭТОТ НАБОР", callback_data=f"wishmap_order_{key}")],
            [InlineKeyboardButton(text="🩺 ДИАГНОСТИКА", callback_data="diagnostic")],
            [InlineKeyboardButton(text="🗺 ДРУГАЯ ЦЕЛЬ", callback_data="wishmap")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )



@router.callback_query(F.data.startswith("wishmap_order_"))
async def wishmap_quick_order(callback: CallbackQuery, state: FSMContext):
    """Быстрый заказ из карты желания."""
    key = callback.data.replace("wishmap_order_", "")
    if key not in WISHMAP_DATA:
        await callback.answer()
        return
    wdata = WISHMAP_DATA[key]
    stones_all = ContentLoader.load_all_stones()
    stones_names = [stones_all.get(sid, {}).get('TITLE', sid) for sid in wdata['stones'] if stones_all.get(sid)]
    from src.handlers.custom_order import CustomOrderStates
    await state.update_data(
        purpose=wdata['title'], situation="Карта желания",
        stones_preference=", ".join(stones_names), budget="", notes="Карта желания: " + wdata['title']
    )
    await state.set_state(CustomOrderStates.q_size)
    msg = "*ЗАКАЗ НАБОРА — " + wdata['title'] + "*\n\nКамни: " + ", ".join(stones_names) + "\n\n*Укажи размер запястья:*"
    await callback.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="14-16 см", callback_data="co_sz_15"), InlineKeyboardButton(text="16-17 см", callback_data="co_sz_16")],
        [InlineKeyboardButton(text="17-18 см", callback_data="co_sz_17"), InlineKeyboardButton(text="18+ см", callback_data="co_sz_18")],
        [InlineKeyboardButton(text="<- НАЗАД", callback_data="wishmap")],
    ]))
    await callback.answer()
