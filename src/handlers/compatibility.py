"""
Совместимость камней — выбираешь 2 камня,
бот говорит совместимы ли они и почему.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.utils.text_loader import ContentLoader

logger = logging.getLogger(__name__)
router = Router()

# Матрица совместимости: (камень1, камень2) -> (уровень, описание)
# Уровни: great / good / neutral / avoid
# ── ПОЛНАЯ МАТРИЦА СОВМЕСТИМОСТИ ──────────────────────────────────────────
# Основана на чакрах, стихиях и энергетических свойствах

COMPATIBILITY = {
    # ── ОТЛИЧНЫЕ ПАРЫ (great) ──────────────────────────────────────────────
    # Любовь + Сердце
    frozenset(['rose_quartz', 'amethyst']): ('great', 'Духовная любовь. Аметист углубляет работу розового кварца, открывая интуицию.'),
    frozenset(['rose_quartz', 'moonstone']): ('great', 'Оба женских, оба мягких. Лунный камень помогает принять любовь, розовый кварц её притягивает.'),
    frozenset(['rose_quartz', 'rhodonite']): ('great', 'Лучшая пара для исцеления сердца. Родонит работает с болью, кварц наполняет место любовью.'),
    frozenset(['rose_quartz', 'kunzite']): ('great', 'Оба открывают сердечную чакру. Кунцит добавляет радость и лёгкость к мягкой любви кварца.'),
    frozenset(['rose_quartz', 'pink_tourmaline']): ('great', 'Двойная сила сердечной чакры. Розовый турмалин защищает, кварц притягивает — мощный любовный дуэт.'),
    frozenset(['rose_quartz', 'lilac_kunzite']): ('great', 'Сиреневый кунцит + розовый кварц = нежность и эмоциональное исцеление.'),
    frozenset(['moonstone', 'labradorite']): ('great', 'Оба камня магии и интуиции. Для серьёзной духовной практики.'),
    frozenset(['moonstone', 'lepidolite']): ('great', 'Оба успокаивают и балансируют. Лепидолит снимает тревогу, лунный камень открывает чувства.'),
    frozenset(['rhodonite', 'lepidolite']): ('great', 'Мягкое исцеление без погружения в боль. Лепидолит успокаивает, родонит работает с травмой деликатно.'),
    frozenset(['rhodonite', 'rose_quartz']): ('great', 'Исцеление сердца. Родонит убирает боль, кварц наполняет любовью.'),

    # Деньги + Земля
    frozenset(['citrine', 'tiger_eye']): ('great', 'Деловой дуэт. Цитрин притягивает деньги, тигровый глаз даёт решительность их заработать.'),
    frozenset(['citrine', 'pyrite']): ('great', 'Двойной финансовый магнит. Цитрин на поток, пирит на уверенность.'),
    frozenset(['citrine', 'green_aventurine']): ('great', 'Удача + деньги. Авантюрин притягивает возможности, цитрин помогает их монетизировать.'),
    frozenset(['tiger_eye', 'pyrite']): ('great', 'Деловая хватка + финансовая уверенность. Для бизнеса и переговоров.'),
    frozenset(['tiger_eye', 'garnet']): ('great', 'Земная сила и страсть к действию. Гранат добавляет огонь к практичности тигрового глаза.'),
    frozenset(['tiger_eye', 'falcon_eye']): ('great', 'Два вида глаза — оба дают ясность видения и защиту. Усиливают друг друга.'),
    frozenset(['tiger_eye', 'bull_eye']): ('great', 'Три глаза вместе — максимальная защита от сглаза и чёткость намерений.'),
    frozenset(['pyrite', 'citrine']): ('great', 'Финансовый дуэт. Пирит — уверенность, цитрин — поток.'),
    frozenset(['sardonyx', 'pyrite']): ('great', 'Оба дают стабильность и защиту в финансах. Сардоникс добавляет дисциплину.'),

    # Защита + Земля
    frozenset(['black_tourmaline', 'hematite']): ('great', 'Мощная защитная броня. Турмалин блокирует негатив, гематит заземляет.'),
    frozenset(['black_tourmaline', 'obsidian']): ('great', 'Максимальная защита. Для тех кто работает с большим количеством людей.'),
    frozenset(['black_tourmaline', 'schorl']): ('great', 'Шерл — разновидность чёрного турмалина. Двойная защитная сила.'),
    frozenset(['black_tourmaline', 'morion']): ('great', 'Чёрный морион усиливает защитные свойства турмалина. Очень сильная защита.'),
    frozenset(['obsidian', 'hematite']): ('great', 'Заземление + очищение. Гематит даёт корни, обсидиан убирает всё лишнее.'),
    frozenset(['hematite', 'red_jasper']): ('great', 'Оба заземляют и дают жизненную силу. Красная яшма добавляет выносливость.'),
    frozenset(['morion', 'black_tourmaline']): ('great', 'Два мощных защитника. Морион + турмалин = непробиваемая защита.'),

    # Духовный рост
    frozenset(['amethyst', 'labradorite']): ('great', 'Лучшая пара для духовных практик. Аметист даёт ясность, лабрадорит открывает скрытое.'),
    frozenset(['amethyst', 'clear_quartz']): ('great', 'Классика. Горный хрусталь усиливает все свойства аметиста в несколько раз.'),
    frozenset(['amethyst', 'lepidolite']): ('great', 'Самая успокаивающая пара. Лепидолит убирает физическую тревогу, аметист — ментальный шум.'),
    frozenset(['amethyst', 'fluorite']): ('great', 'Оба работают с третьим глазом. Флюорит добавляет логику к интуиции аметиста.'),
    frozenset(['amethyst', 'sodalite']): ('great', 'Ум + интуиция. Содалит даёт логику, аметист — чутьё. Хорошо для сложных решений.'),
    frozenset(['amethyst', 'ametrine']): ('great', 'Аметрин содержит аметист. Усиление духовных и финансовых свойств одновременно.'),
    frozenset(['labradorite', 'spectrolite']): ('great', 'Спектролит — редкий лабрадорит. Усиление магических свойств в разы.'),
    frozenset(['labradorite', 'moonstone']): ('great', 'Оба открывают интуицию и связь с высшим. Мощная пара для практиков.'),
    frozenset(['clear_quartz', 'any']): ('great', 'Горный хрусталь усиливает любой камень рядом. Универсальный усилитель.'),
    frozenset(['moldavite', 'clear_quartz']): ('great', 'Молдавит — космический камень. Горный хрусталь усиливает его трансформирующий эффект.'),
    frozenset(['moldavite', 'amethyst']): ('great', 'Молдавит + аметист = глубокая духовная трансформация. Только для опытных.'),
    frozenset(['tanzanite', 'amethyst']): ('great', 'Оба фиолетовые, оба работают с высшими чакрами. Духовное пробуждение.'),
    frozenset(['tanzanite', 'labradorite']): ('great', 'Танзанит открывает высшие чакры, лабрадорит — скрытые знания. Мощная пара.'),
    frozenset(['ametrine', 'citrine']): ('great', 'Аметрин уже содержит цитрин — усиление финансовых потоков.'),
    frozenset(['davudite', 'malachite']): ('great', 'Оба зелёные, оба лечат сердечную чакру. Дополняют друг друга.'),

    # Покой + Вода
    frozenset(['lepidolite', 'amethyst']): ('great', 'Лучшая анти-тревожная пара. Лепидолит действует физически, аметист — ментально.'),
    frozenset(['lepidolite', 'blue_aventurine']): ('great', 'Оба успокаивают нервную систему. Голубой авантюрин добавляет ясность мыслям.'),
    frozenset(['lepidolite', 'sodalite']): ('great', 'Успокоение + ясность. Содалит помогает найти слова, лепидолит — нервы.'),
    frozenset(['blue_aventurine', 'sodalite']): ('great', 'Оба работают с горловой чакрой. Ясная речь и спокойное общение.'),
    frozenset(['sodalite', 'lapis_lazuli']): ('great', 'Оба синие, оба для горловой чакры. Лазурит добавляет мудрость к ясности содалита.'),
    frozenset(['lapis_lazuli', 'sodalite']): ('great', 'Мудрость + ясность. Классическая пара для ораторов и мыслителей.'),
    frozenset(['lapis_lazuli', 'amethyst']): ('great', 'Мудрость + духовность. Оба работают с высшими чакрами.'),
    frozenset(['kyanite', 'lapis_lazuli']): ('great', 'Оба синие, оба очищают. Кианит выравнивает чакры, лазурит наполняет мудростью.'),
    frozenset(['blue_apatite', 'sodalite']): ('great', 'Оба работают с горловой чакрой. Голубой апатит добавляет мотивацию.'),
    frozenset(['chrysocolla', 'blue_aventurine']): ('great', 'Хризоколла + авантюрин = мягкая коммуникация и эмоциональный покой.'),

    # Здоровье + Земля
    frozenset(['jade', 'clear_quartz']): ('great', 'Нефрит + горный хрусталь = усиленное исцеление. Кварц усиливает лечебные свойства нефрита.'),
    frozenset(['jade', 'green_aventurine']): ('great', 'Оба зелёные, оба для здоровья и удачи. Усиливают целительные свойства.'),
    frozenset(['jade', 'green_tourmaline']): ('great', 'Зелёный турмалин + нефрит = исцеление сердца и физического тела.'),
    frozenset(['green_tourmaline', 'jade']): ('great', 'Физическое здоровье + долголетие. Классическая пара для исцеления.'),
    frozenset(['uvarovite', 'green_aventurine']): ('great', 'Уваровит — редкий зелёный гранат. Удача + изобилие в делах.'),
    frozenset(['chrysoprase', 'green_aventurine']): ('great', 'Оба зелёные, оба притягивают удачу. Хризопраз добавляет оптимизм.'),
    frozenset(['chrysoprase', 'rose_quartz']): ('great', 'Хризопраз исцеляет сердце от зависти и обид, кварц наполняет любовью.'),
    frozenset(['malachite', 'jade']): ('great', 'Оба зелёные, оба целители. Малахит трансформирует, нефрит стабилизирует.'),
    frozenset(['amazonite', 'rose_quartz']): ('great', 'Амазонит даёт смелость говорить, кварц открывает сердце. Хорошо для отношений.'),
    frozenset(['amazonite', 'sodalite']): ('great', 'Оба работают с горловой чакрой. Амазонит — смелость, содалит — ясность.'),

    # Энергия + Огонь
    frozenset(['garnet', 'carnelian']): ('great', 'Огненная энергетическая пара. Максимум жизненной силы и страсти.'),
    frozenset(['garnet', 'red_jasper']): ('great', 'Оба красные, оба дают силу и корень. Красная яшма заземляет энергию граната.'),
    frozenset(['carnelian', 'citrine']): ('great', 'Действие + притяжение. Сердолик даёт импульс, цитрин направляет к изобилию.'),
    frozenset(['carnelian', 'tiger_eye']): ('great', 'Огонь + земля. Сердолик зажигает, тигровый глаз удерживает фокус.'),
    frozenset(['red_jasper', 'hematite']): ('great', 'Мощное заземление. Оба красные, оба корневая чакра. Стабильность и сила.'),
    frozenset(['sardonyx', 'garnet']): ('great', 'Оба для силы воли и защиты. Сардоникс добавляет дисциплину к страсти граната.'),
    frozenset(['spinel', 'garnet']): ('great', 'Оба дают жизненную силу и страсть. Шпинель добавляет лёгкость.'),
    frozenset(['spinel', 'carnelian']): ('great', 'Шпинель + сердолик = энергия без перегрева. Шпинель балансирует огонь сердолика.'),
    frozenset(['yellow_apatite', 'citrine']): ('great', 'Оба жёлтые, оба для солнечного сплетения. Апатит добавляет мотивацию к потоку цитрина.'),
    frozenset(['natural_citrine', 'citrine']): ('great', 'Натуральный + облагороженный цитрин. Двойная финансовая сила.'),

    # Редкие и особые
    frozenset(['watermelon_tourmaline', 'rose_quartz']): ('great', 'Арбузный турмалин содержит розовый и зелёный — любовь + исцеление. С кварцем усиливается.'),
    frozenset(['watermelon_tourmaline', 'rhodonite']): ('great', 'Оба для сердечной чакры. Эмоциональное исцеление и баланс.'),
    frozenset(['multicolor_tourmaline', 'clear_quartz']): ('great', 'Многоцветный турмалин охватывает все чакры, хрусталь усиливает каждую.'),
    frozenset(['chrysoberyl', 'tiger_eye']): ('great', 'Оба дают ясность видения. Хризоберилл — дальнозоркость, тигровый глаз — практичность.'),
    frozenset(['blue_chalcedony', 'sodalite']): ('great', 'Оба голубые, оба для горловой чакры. Халцедон добавляет мягкость общению.'),
    frozenset(['blue_chalcedony', 'lepidolite']): ('great', 'Мягкая коммуникация + покой. Оба успокаивают и помогают выражать чувства.'),
    frozenset(['prasiolite', 'amethyst']): ('great', 'Зелёный аметист + фиолетовый аметист = духовность + исцеление сердца.'),
    frozenset(['prasiolite', 'rose_quartz']): ('great', 'Оба для сердечной чакры. Празиолит добавляет спокойную силу к любви кварца.'),

    # ── ХОРОШИЕ ПАРЫ (good) ────────────────────────────────────────────────
    frozenset(['rose_quartz', 'citrine']): ('good', 'Любовь и деньги. Оба несут позитивную энергию, не мешают друг другу.'),
    frozenset(['rose_quartz', 'green_aventurine']): ('good', 'Любовь + удача. Авантюрин притягивает возможности, кварц — тепло отношений.'),
    frozenset(['rose_quartz', 'chrysoprase']): ('good', 'Оба для сердца. Хризопраз убирает негативные эмоции, кварц наполняет любовью.'),
    frozenset(['amethyst', 'moonstone']): ('good', 'Интуиция + духовность. Оба мягкие, дополняют друг друга.'),
    frozenset(['citrine', 'clear_quartz']): ('good', 'Горный хрусталь усиливает финансовые свойства цитрина.'),
    frozenset(['tiger_eye', 'hematite']): ('good', 'Земная пара — оба заземляют. Хорошо для людей "в облаках".'),
    frozenset(['fluorite', 'clear_quartz']): ('good', 'Ясность мышления усилена вдвойне. Хорошо для учёбы и работы.'),
    frozenset(['labradorite', 'amethyst']): ('good', 'Духовность и интуиция. Хорошо дополняют друг друга.'),
    frozenset(['obsidian', 'black_tourmaline']): ('good', 'Двойная защита. Но оба очень мощные — носи по очереди, не постоянно вместе.'),
    frozenset(['garnet', 'citrine']): ('good', 'Страсть + изобилие. Гранат даёт энергию, цитрин направляет её в деньги.'),
    frozenset(['carnelian', 'red_jasper']): ('good', 'Оба огненные. Красная яшма заземляет огонь сердолика.'),
    frozenset(['moonstone', 'rose_quartz']): ('good', 'Мягкая женская пара. Лунный камень открывает к любви, кварц её притягивает.'),
    frozenset(['kyanite', 'amethyst']): ('good', 'Кианит выравнивает чакры, аметист углубляет духовную работу.'),
    frozenset(['blue_apatite', 'labradorite']): ('good', 'Оба работают с высшим знанием. Апатит помогает находить решения, лабрадорит — видеть глубже.'),
    frozenset(['malachite', 'rose_quartz']): ('good', 'Малахит трансформирует сердечные блоки, кварц наполняет освободившееся место любовью.'),
    frozenset(['amazonite', 'moonstone']): ('good', 'Оба для женской энергии. Амазонит — сила, лунный камень — мягкость.'),
    frozenset(['jade', 'citrine']): ('good', 'Нефрит привлекает удачу, цитрин — деньги. Хорошая пара для бизнеса.'),
    frozenset(['uvarovite', 'citrine']): ('good', 'Уваровит + цитрин = изобилие во всех проявлениях.'),
    frozenset(['spinel', 'amethyst']): ('good', 'Шпинель даёт лёгкость, аметист — глубину. Хорошо для медитации.'),
    frozenset(['yellow_apatite', 'tiger_eye']): ('good', 'Оба для солнечного сплетения. Апатит + тигровый глаз = уверенность + действие.'),
    frozenset(['chrysoberyl', 'citrine']): ('good', 'Ясность видения + финансовый поток. Хорошо для предпринимателей.'),
    frozenset(['davudite', 'labradorite']): ('good', 'Оба работают с тайными знаниями. Давудит + лабрадорит = глубокая интуиция.'),
    frozenset(['sardonyx', 'hematite']): ('good', 'Оба для защиты и стабильности. Земная, надёжная пара.'),
    frozenset(['prasiolite', 'citrine']): ('good', 'Зелёный аметист + цитрин = исцеление + изобилие.'),
    frozenset(['tanzanite', 'clear_quartz']): ('good', 'Горный хрусталь усиливает высокие вибрации танзанита.'),
    frozenset(['watermelon_tourmaline', 'clear_quartz']): ('good', 'Хрусталь усиливает все чакры арбузного турмалина.'),
    frozenset(['multicolor_tourmaline', 'labradorite']): ('good', 'Оба работают с несколькими чакрами. Богатая энергетическая работа.'),
    frozenset(['blue_chalcedony', 'moonstone']): ('good', 'Оба мягкие, оба женские. Интуиция + нежная коммуникация.'),
    frozenset(['chrysocolla', 'rose_quartz']): ('good', 'Хризоколла + кварц = исцеление через любовь и принятие.'),
    frozenset(['natural_citrine', 'tiger_eye']): ('good', 'Натуральный цитрин + тигровый глаз = настоящий финансовый амулет.'),

    # ── НЕЙТРАЛЬНЫЕ (neutral) ──────────────────────────────────────────────
    frozenset(['rose_quartz', 'black_tourmaline']): ('neutral', 'Разные энергии, но не конфликтуют. Турмалин защищает, кварц любит — работают независимо.'),
    frozenset(['citrine', 'amethyst']): ('neutral', 'Противоположности (солнце vs луна). В одном браслете часто уравновешивают друг друга. Наблюдай за ощущениями.'),
    frozenset(['labradorite', 'hematite']): ('neutral', 'Лабрадорит поднимает вверх, гематит тянет вниз. Используй если нужен баланс.'),
    frozenset(['obsidian', 'amethyst']): ('neutral', 'Обсидиан погружает в тьму для трансформации, аметист освещает путь. Могут работать, но требуют осторожности.'),
    frozenset(['moldavite', 'hematite']): ('neutral', 'Молдавит поднимает высоко, гематит заземляет. Полезно если молдавит слишком активен.'),
    frozenset(['garnet', 'moonstone']): ('neutral', 'Огонь + вода. Могут быть интересным балансом страсти и интуиции, но непредсказуемо.'),
    frozenset(['carnelian', 'lepidolite']): ('neutral', 'Сердолик активирует, лепидолит успокаивает. Нейтрализуют друг друга. Носи по очереди.'),
    frozenset(['obsidian', 'rose_quartz']): ('neutral', 'Обсидиан — зеркало тьмы, кварц — свет любви. Работают в разных направлениях.'),
    frozenset(['pyrite', 'amethyst']): ('neutral', 'Пирит — земля, деньги; аметист — дух. Могут работать вместе как баланс материального и духовного.'),
    frozenset(['schorl', 'rose_quartz']): ('neutral', 'Шерл защищает жёстко, кварц мягко открывает. Могут работать в паре защита+открытость.'),

    # ── ЛУЧШЕ НЕ СОВМЕЩАТЬ (avoid) ────────────────────────────────────────
    frozenset(['amethyst', 'carnelian']): ('avoid', 'Аметист успокаивает, сердолик возбуждает. Вместе создают внутреннее напряжение.'),
    frozenset(['obsidian', 'labradorite']): ('avoid', 'Оба очень мощные. Вместе могут быть перегрузкой. Только для опытных практиков.'),
    frozenset(['moldavite', 'obsidian']): ('avoid', 'Оба трансформирующие и очень мощные. Вместе — слишком интенсивно даже для опытных.'),
    frozenset(['moldavite', 'black_tourmaline']): ('avoid', 'Молдавит открывает, турмалин защищает-блокирует. Противоположные направления работы.'),
    frozenset(['citrine', 'black_tourmaline']): ('avoid', 'Цитрин притягивает энергию и деньги, турмалин всё отталкивает. Нейтрализуют друг друга.'),
    frozenset(['garnet', 'lepidolite']): ('avoid', 'Гранат активирует и разжигает, лепидолит успокаивает. Сильный конфликт энергий.'),
    frozenset(['carnelian', 'moonstone']): ('avoid', 'Огонь + вода. Сердолик — активное действие, лунный камень — пассивная интуиция. Мешают друг другу.'),
}


# Популярные камни для выбора (первый шаг)
POPULAR_STONES = [
    ('rose_quartz', '💗 Розовый кварц'),
    ('amethyst', '💜 Аметист'),
    ('citrine', '🌟 Цитрин'),
    ('labradorite', '🌈 Лабрадорит'),
    ('black_tourmaline', '🖤 Чёрный турмалин'),
    ('tiger_eye', '🐯 Тигровый глаз'),
    ('moonstone', '🌕 Лунный камень'),
    ('clear_quartz', '💎 Горный хрусталь'),
    ('hematite', '⚫ Гематит'),
    ('lepidolite', '💜 Лепидолит'),
    ('rhodonite', '💕 Родонит'),
    ('carnelian', '🔥 Сердолик'),
    ('green_aventurine', '🍀 Авантюрин зелёный'),
    ('obsidian', '🪨 Обсидиан'),
    ('sodalite', '💙 Содалит'),
    ('garnet', '🔴 Гранат'),
]

LEVEL_EMOJI = {
    'great': '✅ ОТЛИЧНО СОВМЕСТИМЫ',
    'good': '👍 ХОРОШО СОВМЕСТИМЫ',
    'neutral': '🔄 НЕЙТРАЛЬНОЕ СОЧЕТАНИЕ',
    'avoid': '⚠️ ЛУЧШЕ НЕ СОВМЕЩАТЬ',
}

LEVEL_TEXT = {
    'great': 'Эти камни усиливают друг друга. Смело носи вместе.',
    'good': 'Сочетание рабочее. Камни не мешают друг другу.',
    'neutral': 'Могут работать вместе, но эффект непредсказуем. Попробуй и понаблюдай за ощущениями.',
    'avoid': 'Эти камни конфликтуют по энергии. Носи по отдельности.',
}


class CompatibilityStates(StatesGroup):
    choosing_first = State()
    choosing_second = State()


@router.callback_query(F.data == "compatibility")
async def compat_start(callback: CallbackQuery, state: FSMContext):
    """Начало проверки совместимости."""
    await state.clear()
    await state.set_state(CompatibilityStates.choosing_first)

    buttons = []
    row = []
    for i, (stone_id, label) in enumerate(POPULAR_STONES):
        row.append(InlineKeyboardButton(text=label, callback_data=f"compat1_{stone_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="← НАЗАД", callback_data="menu")])

    await callback.answer()
    await callback.message.edit_text(
        "🔮 *СОВМЕСТИМОСТЬ КАМНЕЙ*\n\n"
        "Выбери *первый* камень:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )



@router.callback_query(CompatibilityStates.choosing_first, F.data.startswith("compat1_"))
async def compat_first_chosen(callback: CallbackQuery, state: FSMContext):
    """Первый камень выбран — выбираем второй."""
    stone1 = callback.data.replace("compat1_", "")
    label1 = next((l for s, l in POPULAR_STONES if s == stone1), stone1)
    await state.update_data(stone1=stone1, label1=label1)
    await state.set_state(CompatibilityStates.choosing_second)

    buttons = []
    row = []
    for i, (stone_id, label) in enumerate(POPULAR_STONES):
        if stone_id == stone1:
            continue
        row.append(InlineKeyboardButton(text=label, callback_data=f"compat2_{stone_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="← ЗАНОВО", callback_data="compatibility")])

    await callback.answer()
    await callback.message.edit_text(
        f"🔮 *СОВМЕСТИМОСТЬ КАМНЕЙ*\n\n"
        f"Первый камень: *{label1}*\n\n"
        f"Выбери *второй* камень:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )



@router.callback_query(CompatibilityStates.choosing_second, F.data.startswith("compat2_"))
async def compat_result(callback: CallbackQuery, state: FSMContext):
    """Показать результат совместимости."""
    data = await state.get_data()
    await state.clear()
    stone1 = data['stone1']
    label1 = data['label1']
    stone2 = callback.data.replace("compat2_", "")
    label2 = next((l for s, l in POPULAR_STONES if s == stone2), stone2)
    await state.clear()

    pair = frozenset([stone1, stone2])
    result = COMPATIBILITY.get(pair)

    if result:
        level, description = result
        level_title = LEVEL_EMOJI[level]
        level_desc = LEVEL_TEXT[level]
        text = (
            f"🔮 *СОВМЕСТИМОСТЬ*\n\n"
            f"{label1} + {label2}\n\n"
            f"*{level_title}*\n\n"
            f"{description}\n\n"
            f"_{level_desc}_"
        )
    else:
        text = (
            f"🔮 *СОВМЕСТИМОСТЬ*\n\n"
            f"{label1} + {label2}\n\n"
            f"*🔄 НЕТ ДАННЫХ*\n\n"
            f"Для этой пары у нас пока нет точных данных. "
            f"Носи по отдельности несколько дней, потом вместе — "
            f"и слушай своё тело. Оно скажет лучше любой теории.\n\n"
            f"_Можешь спросить совет мастера — он подберёт индивидуально._"
        )

    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ДРУГУЮ ПАРУ", callback_data="compatibility")],
            [InlineKeyboardButton(text="💎 ВИТРИНА", callback_data="showcase")],
            [InlineKeyboardButton(text="🤖 СПРОСИТЬ МАСТЕРА", callback_data="ai_consult")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )

