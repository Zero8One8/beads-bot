"""
Квиз "Узнай свой камень" и "Тотемный камень".
Мощные вопросы с разделением мужчина/женщина/подарок.
Результат — из базы знаний (файлы knowledge_base).
"""
import logging
import json
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.utils.text_loader import ContentLoader
from src.services.analytics import FunnelTracker

logger = logging.getLogger(__name__)
router = Router()


class QuizStates(StatesGroup):
    choosing_gender = State()
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()


class TotemStates(StatesGroup):
    choosing_gender = State()
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()


# ──────────────────────────────────────────────────────────────
# ВОПРОСЫ КВИЗА — по типу пользователя
# ──────────────────────────────────────────────────────────────

QUIZ_QUESTIONS = {
    'female': [
        {
            'text': '✨ Что сейчас происходит в твоей жизни?\n\nБудь честна с собой — именно это определит твой камень.',
            'options': [
                ('💔 Боль в сердце — разрыв, предательство, потеря', {'rose_quartz': 3, 'rhodonite': 3, 'lepidolite': 2}),
                ('🌪 Хаос и тревога — не могу успокоиться', {'amethyst': 3, 'lepidolite': 3, 'moonstone': 2}),
                ('💰 Хочу большего — денег, успеха, признания', {'citrine': 3, 'tiger_eye': 2, 'pyrite': 2}),
                ('🌿 Ищу себя — кто я, зачем живу, какой мой путь', {'labradorite': 3, 'moonstone': 3, 'amethyst': 2}),
            ]
        },
        {
            'text': '💫 Каким словом ты бы описала своё внутреннее состояние прямо сейчас?',
            'options': [
                ('🥀 Истощена — отдаю больше, чем получаю', {'rose_quartz': 3, 'rhodonite': 2, 'carnelian': 2}),
                ('⚡ На взводе — всё раздражает, нет покоя', {'lepidolite': 3, 'amethyst': 2, 'blue_aventurine': 2}),
                ('🌫 Потеряна — нет ориентиров, нет опоры', {'black_tourmaline': 2, 'hematite': 2, 'labradorite': 3}),
                ('🌟 Готова к переменам — чувствую, что пора', {'labradorite': 3, 'citrine': 2, 'moonstone': 2}),
            ]
        },
        {
            'text': '🔮 Что тебе сейчас нужнее всего?',
            'options': [
                ('🛡 Защита — от чужой энергии, зависти, манипуляций', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('💞 Любовь — к себе, принятие, нежность', {'rose_quartz': 3, 'rhodonite': 2, 'kunzite': 2}),
                ('🧠 Ясность — понять что делать, принять решение', {'sodalite': 3, 'fluorite': 2, 'clear_quartz': 2}),
                ('🔥 Энергия — сил нет, всё даётся с трудом', {'carnelian': 3, 'garnet': 2, 'citrine': 2}),
            ]
        },
        {
            'text': '🌙 Как ты чувствуешь себя среди людей?',
            'options': [
                ('😶 Не могу сказать "нет" — всегда со всеми соглашаюсь', {'amazonite': 3, 'sodalite': 2, 'rose_quartz': 1}),
                ('😤 Всё держу в себе — боюсь быть непонятой', {'blue_aventurine': 3, 'sodalite': 2, 'moonstone': 2}),
                ('🦋 Чувствую себя не такой как все — особенной', {'labradorite': 3, 'moonstone': 2, 'amethyst': 2}),
                ('🌊 Принимаю всё на себя — эмпат, устаю от людей', {'black_tourmaline': 3, 'hematite': 2, 'lepidolite': 2}),
            ]
        },
        {
            'text': '⭐ Какой результат ты хочешь получить от камня?',
            'options': [
                ('🌸 Больше любви и гармонии в жизни', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('💪 Силу двигаться вперёд несмотря ни на что', {'garnet': 3, 'tiger_eye': 2, 'carnelian': 3}),
                ('🔐 Защиту от всего плохого', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('🌟 Интуицию и связь с собой', {'amethyst': 3, 'labradorite': 2, 'moonstone': 3}),
            ]
        },
    ],
    'male': [
        {
            'text': '⚔️ Что сейчас происходит в твоей жизни?\n\nОтвечай честно — именно это покажет твой камень.',
            'options': [
                ('📉 Бизнес или карьера — нужен прорыв, застрял', {'citrine': 3, 'tiger_eye': 3, 'pyrite': 2}),
                ('😤 Конфликты — давление со всех сторон', {'black_tourmaline': 3, 'hematite': 2, 'obsidian': 2}),
                ('🌫 Потерял цель — не понимаю зачем и куда', {'labradorite': 3, 'sodalite': 2, 'clear_quartz': 2}),
                ('💔 Отношения — боль, одиночество, непонимание', {'rhodonite': 3, 'rose_quartz': 2, 'lepidolite': 2}),
            ]
        },
        {
            'text': '🧠 Как ты принимаешь решения?',
            'options': [
                ('🔥 На эмоциях — потом жалею', {'tiger_eye': 3, 'sodalite': 2, 'hematite': 2}),
                ('🧊 Долго думаю — боюсь ошибиться', {'labradorite': 2, 'clear_quartz': 3, 'fluorite': 2}),
                ('💭 Интуитивно — но не всегда доверяю себе', {'amethyst': 3, 'moonstone': 2, 'labradorite': 2}),
                ('👥 Советуюсь — зависимость от чужого мнения', {'sodalite': 3, 'amazonite': 2, 'tiger_eye': 2}),
            ]
        },
        {
            'text': '⚡ Чего тебе не хватает прямо сейчас?',
            'options': [
                ('💰 Денег и финансовой уверенности', {'citrine': 3, 'pyrite': 3, 'tiger_eye': 2}),
                ('🛡 Защиты от чужого влияния и зависти', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('🔥 Энергии и желания что-то делать', {'garnet': 3, 'carnelian': 3, 'citrine': 2}),
                ('🧘 Покоя — устал от постоянного напряжения', {'lepidolite': 3, 'amethyst': 2, 'sodalite': 2}),
            ]
        },
        {
            'text': '🎯 Что мешает тебе достигать целей?',
            'options': [
                ('😨 Страх — не берусь за то, чего хочу', {'tiger_eye': 3, 'carnelian': 2, 'garnet': 2}),
                ('🌪 Рассеянность — не могу сфокусироваться', {'fluorite': 3, 'sodalite': 2, 'clear_quartz': 2}),
                ('😔 Неуверенность — сомневаюсь в себе', {'citrine': 3, 'tiger_eye': 2, 'pyrite': 3}),
                ('🧱 Внешние препятствия — как будто всё против', {'black_tourmaline': 2, 'labradorite': 3, 'obsidian': 2}),
            ]
        },
        {
            'text': '🌟 Каким ты хочешь стать благодаря камню?',
            'options': [
                ('👑 Уверенным лидером, которого уважают', {'tiger_eye': 3, 'citrine': 2, 'pyrite': 2}),
                ('🧙 Мудрым — понимать людей и ситуации насквозь', {'labradorite': 3, 'amethyst': 2, 'sodalite': 3}),
                ('⚡ Энергичным и целеустремлённым', {'garnet': 3, 'carnelian': 3, 'citrine': 2}),
                ('🏔 Спокойным — непробиваемым для любого негатива', {'black_tourmaline': 3, 'hematite': 3, 'obsidian': 2}),
            ]
        },
    ],
    'gift': [
        {
            'text': '🎁 Кому вы выбираете подарок?',
            'options': [
                ('👩 Женщине — близкой, любимой, подруге', {'rose_quartz': 3, 'moonstone': 3, 'amethyst': 2}),
                ('👨 Мужчине — другу, партнёру, родственнику', {'tiger_eye': 3, 'black_tourmaline': 2, 'citrine': 3}),
                ('👧 Ребёнку или подростку', {'rose_quartz': 2, 'clear_quartz': 3, 'green_aventurine': 3}),
                ('👴👵 Пожилому человеку — родителям, бабушке/дедушке', {'rhodonite': 2, 'jade': 3, 'rose_quartz': 2}),
            ]
        },
        {
            'text': '💝 По какому поводу вы дарите?',
            'options': [
                ('🎂 День рождения — хочу пожелать счастья', {'citrine': 2, 'rose_quartz': 3, 'green_aventurine': 2}),
                ('💑 Романтический повод — любовь, годовщина', {'rose_quartz': 3, 'rhodonite': 2, 'moonstone': 2}),
                ('🌱 Новый этап — работа, переезд, начало чего-то', {'citrine': 3, 'tiger_eye': 2, 'labradorite': 2}),
                ('💙 Хочу поддержать — человеку сейчас тяжело', {'lepidolite': 3, 'rhodonite': 3, 'amethyst': 2}),
            ]
        },
        {
            'text': '🌿 Что вы знаете об этом человеке?',
            'options': [
                ('😰 Много стрессует, всё держит в себе', {'lepidolite': 3, 'amethyst': 3, 'blue_aventurine': 2}),
                ('💸 Мечтает о финансовом росте и успехе', {'citrine': 3, 'pyrite': 2, 'tiger_eye': 3}),
                ('💞 Открытый и чувствительный, ищет любовь', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('🔮 Духовный, интересуется эзотерикой', {'amethyst': 3, 'labradorite': 3, 'clear_quartz': 2}),
            ]
        },
        {
            'text': '⭐ Что вы хотите пожелать этому человеку больше всего?',
            'options': [
                ('❤️ Любви, гармонии и счастья в жизни', {'rose_quartz': 3, 'rhodonite': 2, 'moonstone': 2}),
                ('🛡 Защиты от всего плохого', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('✨ Удачи и новых возможностей', {'citrine': 3, 'green_aventurine': 3, 'tiger_eye': 2}),
                ('🌊 Спокойствия и внутреннего баланса', {'amethyst': 3, 'lepidolite': 3, 'sodalite': 2}),
            ]
        },
        {
            'text': '💎 Какой камень вам больше нравится внешне?',
            'options': [
                ('🌸 Нежный розовый — тёплый и мягкий', {'rose_quartz': 4, 'rhodonite': 2, 'kunzite': 2}),
                ('💜 Насыщенный фиолетовый — глубокий и мистичный', {'amethyst': 4, 'labradorite': 2, 'lepidolite': 2}),
                ('🌟 Золотистый и яркий — как солнце', {'citrine': 4, 'tiger_eye': 2, 'pyrite': 2}),
                ('🔮 Тёмный и загадочный — с переливом', {'labradorite': 4, 'black_tourmaline': 2, 'obsidian': 2}),
            ]
        },
    ]
}

TOTEM_QUESTIONS = {
    'female': [
        {
            'text': '🌙 Закрой глаза и представь: ты одна в лесу ночью. Что ты чувствуешь?\n\n_Отвечай первым ощущением — оно самое честное_',
            'options': [
                ('🌟 Покой и единство с природой — я дома', {'moonstone': 3, 'labradorite': 2, 'clear_quartz': 2}),
                ('⚡ Бодрость и острота — все чувства обострились', {'tiger_eye': 2, 'garnet': 3, 'carnelian': 2}),
                ('😰 Страх, но я его преодолеваю — иду вперёд', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('🔮 Чувствую что-то большее — как будто вижу сквозь тьму', {'labradorite': 3, 'amethyst': 3, 'moonstone': 2}),
            ]
        },
        {
            'text': '🌊 Что для тебя означает "быть счастливой"?',
            'options': [
                ('💞 Любить и быть любимой — это всё', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('🔥 Гореть — творить, создавать, воплощать', {'carnelian': 3, 'citrine': 2, 'garnet': 2}),
                ('🛡 Быть в безопасности — мне и близким ничего не угрожает', {'black_tourmaline': 3, 'hematite': 2, 'obsidian': 2}),
                ('✨ Расти и развиваться — каждый день становиться лучше', {'labradorite': 3, 'amethyst': 2, 'clear_quartz': 3}),
            ]
        },
        {
            'text': '🌿 Твоя главная сила — что в тебе самое мощное?',
            'options': [
                ('❤️ Умею любить — глубоко, полностью, без условий', {'rose_quartz': 3, 'rhodonite': 2, 'kunzite': 2}),
                ('🔮 Чувствую людей насквозь — вижу то, что скрыто', {'labradorite': 3, 'moonstone': 3, 'amethyst': 2}),
                ('💪 Не сдаюсь — встаю снова и снова', {'garnet': 3, 'tiger_eye': 2, 'carnelian': 3}),
                ('🧠 Вижу суть — нахожу решения там, где другие не видят', {'sodalite': 3, 'fluorite': 2, 'clear_quartz': 3}),
            ]
        },
        {
            'text': '🌺 Твоя главная слабость — что тебе труднее всего?',
            'options': [
                ('😶 Говорить "нет" — не могу отказать', {'amazonite': 3, 'sodalite': 2, 'blue_aventurine': 2}),
                ('💭 Доверять себе — сомневаюсь в своих решениях', {'amethyst': 2, 'moonstone': 3, 'clear_quartz': 2}),
                ('🌪 Успокоиться — постоянно что-то прокручиваю в голове', {'lepidolite': 3, 'amethyst': 3, 'sodalite': 2}),
                ('🔥 Беречь себя — отдаю всё, забываю о себе', {'rose_quartz': 3, 'rhodonite': 2, 'carnelian': 2}),
            ]
        },
        {
            'text': '⭐ Если бы у тебя была суперспособность — какая?',
            'options': [
                ('👁 Видеть прошлое и будущее — знать наперёд', {'labradorite': 3, 'amethyst': 3, 'moonstone': 2}),
                ('🌊 Исцелять — людей, отношения, ситуации', {'rose_quartz': 3, 'rhodonite': 3, 'clear_quartz': 2}),
                ('⚡ Притягивать удачу — всё что хочу, сбывается', {'citrine': 3, 'green_aventurine': 3, 'tiger_eye': 2}),
                ('🛡 Никого к себе не подпускать — абсолютная защита', {'black_tourmaline': 3, 'obsidian': 3, 'hematite': 2}),
            ]
        },
    ],
    'male': [
        {
            'text': '⚔️ Ты воин. Ты входишь в бой. Что ты чувствуешь в этот момент?',
            'options': [
                ('🔥 Кровь кипит — я рождён для этого', {'garnet': 3, 'carnelian': 3, 'tiger_eye': 2}),
                ('🧊 Холодный расчёт — эмоций нет, только цель', {'tiger_eye': 3, 'sodalite': 2, 'hematite': 3}),
                ('🌟 Я знаю, что победю — это чувство изнутри', {'citrine': 3, 'labradorite': 2, 'clear_quartz': 2}),
                ('🛡 Защищаю тех, кто за мной — это важнее победы', {'black_tourmaline': 3, 'hematite': 2, 'obsidian': 2}),
            ]
        },
        {
            'text': '🌿 Что для тебя значит настоящий успех?',
            'options': [
                ('💰 Финансовая свобода — могу купить всё что хочу', {'citrine': 3, 'pyrite': 3, 'tiger_eye': 2}),
                ('👑 Уважение — люди слушают и следуют за мной', {'tiger_eye': 3, 'labradorite': 2, 'sodalite': 2}),
                ('🔥 Страсть — делать то, что горит внутри', {'carnelian': 3, 'garnet': 3, 'citrine': 2}),
                ('🏔 Спокойствие — всё под контролем, ничто не достаёт', {'hematite': 3, 'black_tourmaline': 2, 'sodalite': 2}),
            ]
        },
        {
            'text': '🎯 Твой главный враг — кто или что тебя останавливает?',
            'options': [
                ('😤 Те, кто завидует и вставляет палки в колёса', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 3}),
                ('😰 Собственный страх и неуверенность', {'tiger_eye': 3, 'carnelian': 2, 'garnet': 2}),
                ('🌪 Хаос — не могу сфокусироваться на главном', {'fluorite': 3, 'sodalite': 3, 'clear_quartz': 2}),
                ('😶 Лень и прокрастинация — откладываю то, что важно', {'carnelian': 3, 'garnet': 2, 'citrine': 3}),
            ]
        },
        {
            'text': '🔮 Что в тебе самое мощное?',
            'options': [
                ('🧠 Интеллект — вижу то, что другие не замечают', {'sodalite': 3, 'labradorite': 3, 'amethyst': 2}),
                ('⚡ Воля — принял решение — иду до конца', {'tiger_eye': 3, 'garnet': 2, 'hematite': 3}),
                ('🎯 Интуиция — чую, как будет, до того как всё случилось', {'labradorite': 3, 'amethyst': 3, 'moonstone': 2}),
                ('❤️ Преданность — тем, кого люблю, отдаю всё', {'rhodonite': 3, 'rose_quartz': 2, 'garnet': 2}),
            ]
        },
        {
            'text': '🌟 Твой архетип — кто ты в глубине души?',
            'options': [
                ('👑 Король — созидатель, держу всё в руках', {'citrine': 3, 'tiger_eye': 3, 'pyrite': 2}),
                ('🧙 Маг — знаю то, что недоступно другим', {'labradorite': 3, 'amethyst': 3, 'obsidian': 2}),
                ('⚔️ Воин — защищаю, борюсь, побеждаю', {'garnet': 3, 'black_tourmaline': 2, 'hematite': 3}),
                ('🌿 Мудрец — ищу смысл, понимаю глубже', {'sodalite': 3, 'clear_quartz': 2, 'amethyst': 3}),
            ]
        },
    ],
    'gift': [
        {
            'text': '🎁 Кому вы ищете тотемный камень?\n\n_Тотемный камень отражает глубинную суть человека_',
            'options': [
                ('👩 Женщине — понять её истинную природу', {'moonstone': 3, 'rose_quartz': 2, 'labradorite': 2}),
                ('👨 Мужчине — найти его истинную силу', {'tiger_eye': 3, 'garnet': 2, 'labradorite': 2}),
                ('👧👦 Ребёнку — увидеть его предназначение', {'clear_quartz': 3, 'green_aventurine': 2, 'rose_quartz': 2}),
                ('🤷 Сам(а) не знаю — покажи мне подходящий', {'labradorite': 3, 'clear_quartz': 2, 'amethyst': 2}),
            ]
        },
        {
            'text': '🌿 Какое первое слово приходит, когда вы думаете об этом человеке?',
            'options': [
                ('💞 Тепло, нежность, забота', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('⚡ Сила, энергия, драйв', {'garnet': 3, 'carnelian': 3, 'tiger_eye': 2}),
                ('🔮 Загадочность, глубина, мудрость', {'labradorite': 3, 'amethyst': 3, 'obsidian': 2}),
                ('🌟 Свет, позитив, радость', {'citrine': 3, 'green_aventurine': 2, 'clear_quartz': 2}),
            ]
        },
        {
            'text': '💫 Что этому человеку нужно прямо сейчас?',
            'options': [
                ('🛡 Защита — что-то давит на него/неё', {'black_tourmaline': 3, 'obsidian': 2, 'hematite': 2}),
                ('💰 Удача и поток — хочет большего', {'citrine': 3, 'tiger_eye': 2, 'pyrite': 3}),
                ('💞 Любовь и принятие — одиноко внутри', {'rose_quartz': 3, 'rhodonite': 3, 'lepidolite': 2}),
                ('✨ Ясность — потерял(а) ориентиры', {'labradorite': 3, 'sodalite': 2, 'clear_quartz': 3}),
            ]
        },
        {
            'text': '🌙 Что этот человек ценит в жизни больше всего?',
            'options': [
                ('❤️ Отношения и близость', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('🏆 Достижения и успех', {'tiger_eye': 3, 'citrine': 3, 'pyrite': 2}),
                ('🌌 Духовный рост и развитие', {'amethyst': 3, 'labradorite': 3, 'clear_quartz': 2}),
                ('🕊 Покой и стабильность', {'hematite': 2, 'lepidolite': 3, 'jade': 3}),
            ]
        },
        {
            'text': '⭐ Каким вы хотите видеть этого человека через год?',
            'options': [
                ('😊 Счастливым и любимым', {'rose_quartz': 3, 'moonstone': 2, 'rhodonite': 2}),
                ('💪 Сильным и уверенным', {'tiger_eye': 3, 'garnet': 2, 'citrine': 2}),
                ('🌟 Реализованным — живёт своим путём', {'labradorite': 3, 'amethyst': 2, 'carnelian': 2}),
                ('🛡 Защищённым от всего плохого', {'black_tourmaline': 3, 'hematite': 2, 'obsidian': 2}),
            ]
        },
    ]
}


def _calculate_result(scores: dict, quiz_type: str = 'quiz') -> str:
    """Считает результат и возвращает stone_id победителя."""
    if not scores:
        return 'rose_quartz'
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return top[0][0]


def _get_stone_info(stone_id: str) -> dict:
    """Загружает описание камня из файлов."""
    stone = ContentLoader.load_stone(stone_id)
    if stone:
        return stone
    stones = ContentLoader.load_all_stones()
    if stones:
        return list(stones.values())[0]
    return {'TITLE': stone_id, 'EMOJI': '💎', 'SHORT_DESC': '', 'FULL_DESC': ''}


def _build_question_keyboard(options: list, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, opt in enumerate(options):
        text = opt[0] if isinstance(opt, tuple) else opt
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"{prefix}{i}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ──────────────────────────────────────────────────────────────
# КВИЗ — СТАРТ
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "quiz")
async def quiz_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await FunnelTracker.track(callback.from_user.id, 'quiz_start')

    await callback.message.edit_text(
        "🔮 *УЗНАЙ СВОЙ КАМЕНЬ*\n\n"
        "5 вопросов — и ты узнаешь, какой камень резонирует с тобой прямо сейчас.\n\n"
        "_Отвечай честно. Камень слышит то, что ты не говоришь вслух._\n\n"
        "Для кого подбираем камень?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👩 Для меня (женщина)", callback_data="quiz_gender_female")],
            [InlineKeyboardButton(text="👨 Для меня (мужчина)", callback_data="quiz_gender_male")],
            [InlineKeyboardButton(text="🎁 Подбираю подарок", callback_data="quiz_gender_gift")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")],
        ])
    )
    await state.set_state(QuizStates.choosing_gender)


@router.callback_query(QuizStates.choosing_gender, F.data.startswith("quiz_gender_"))
async def quiz_gender_selected(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.replace("quiz_gender_", "")
    await state.update_data(gender=gender, scores={}, step=0)
    await state.set_state(QuizStates.q1)
    await _show_quiz_question(callback, state, 'quiz')


async def _show_quiz_question(callback: CallbackQuery, state: FSMContext, qtype: str):
    data = await state.get_data()
    gender = data.get('gender', 'female')
    step = data.get('step', 0)

    questions = QUIZ_QUESTIONS[gender] if qtype == 'quiz' else TOTEM_QUESTIONS[gender]

    if step >= len(questions):
        await _show_result(callback, state, qtype)
        return

    q = questions[step]
    total = len(questions)
    prefix = f"quiz_a{step}_" if qtype == 'quiz' else f"totem_a{step}_"

    await callback.answer()
    await callback.message.edit_text(
        f"{'🔮' if qtype == 'quiz' else '🎯'} *Вопрос {step + 1} из {total}*\n\n{q['text']}",
        parse_mode="Markdown",
        reply_markup=_build_question_keyboard(q['options'], prefix)
    )



@router.callback_query(QuizStates.q1, F.data.startswith("quiz_a0_"))
@router.callback_query(QuizStates.q2, F.data.startswith("quiz_a1_"))
@router.callback_query(QuizStates.q3, F.data.startswith("quiz_a2_"))
@router.callback_query(QuizStates.q4, F.data.startswith("quiz_a3_"))
@router.callback_query(QuizStates.q5, F.data.startswith("quiz_a4_"))
async def quiz_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = data.get('step', 0)
    gender = data.get('gender', 'female')
    scores = data.get('scores', {})

    ans_idx = int(callback.data.split('_')[-1])
    questions = QUIZ_QUESTIONS[gender]

    if step < len(questions):
        q = questions[step]
        if ans_idx < len(q['options']):
            opt = q['options'][ans_idx]
            weights = opt[1] if isinstance(opt, tuple) else {}
            for stone_id, pts in weights.items():
                scores[stone_id] = scores.get(stone_id, 0) + pts

    step += 1
    await state.update_data(step=step, scores=scores)

    states_map = {1: QuizStates.q2, 2: QuizStates.q3, 3: QuizStates.q4, 4: QuizStates.q5}
    if step < len(questions):
        await state.set_state(states_map.get(step, QuizStates.q5))
        await _show_quiz_question(callback, state, 'quiz')
    else:
        await _show_result(callback, state, 'quiz')


# ──────────────────────────────────────────────────────────────
# ТОТЕМ — СТАРТ
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "totem")
async def totem_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await FunnelTracker.track(callback.from_user.id, 'totem_start')

    await callback.message.edit_text(
        "🦊 *ТОТЕМНЫЙ КАМЕНЬ*\n\n"
        "Тотемный камень — это не просто украшение.\n"
        "Это зеркало твоей глубинной природы.\n\n"
        "_5 вопросов раскроют, какой камень является твоим архетипом — тем, что ты несёшь в себе от рождения._\n\n"
        "Для кого ищем тотем?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👩 Для меня (женщина)", callback_data="totem_gender_female")],
            [InlineKeyboardButton(text="👨 Для меня (мужчина)", callback_data="totem_gender_male")],
            [InlineKeyboardButton(text="🎁 Для другого человека", callback_data="totem_gender_gift")],
            [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")],
        ])
    )
    await state.set_state(TotemStates.choosing_gender)


@router.callback_query(TotemStates.choosing_gender, F.data.startswith("totem_gender_"))
async def totem_gender_selected(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.replace("totem_gender_", "")
    await state.update_data(gender=gender, scores={}, step=0)
    await state.set_state(TotemStates.q1)
    await _show_quiz_question(callback, state, 'totem')


@router.callback_query(TotemStates.q1, F.data.startswith("totem_a0_"))
@router.callback_query(TotemStates.q2, F.data.startswith("totem_a1_"))
@router.callback_query(TotemStates.q3, F.data.startswith("totem_a2_"))
@router.callback_query(TotemStates.q4, F.data.startswith("totem_a3_"))
@router.callback_query(TotemStates.q5, F.data.startswith("totem_a4_"))
async def totem_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = data.get('step', 0)
    gender = data.get('gender', 'female')
    scores = data.get('scores', {})

    ans_idx = int(callback.data.split('_')[-1])
    questions = TOTEM_QUESTIONS[gender]

    if step < len(questions):
        q = questions[step]
        if ans_idx < len(q['options']):
            opt = q['options'][ans_idx]
            weights = opt[1] if isinstance(opt, tuple) else {}
            for stone_id, pts in weights.items():
                scores[stone_id] = scores.get(stone_id, 0) + pts

    step += 1
    await state.update_data(step=step, scores=scores)

    states_map = {1: TotemStates.q2, 2: TotemStates.q3, 3: TotemStates.q4, 4: TotemStates.q5}
    if step < len(questions):
        await state.set_state(states_map.get(step, TotemStates.q5))
        await _show_quiz_question(callback, state, 'totem')
    else:
        await _show_result(callback, state, 'totem')


# ──────────────────────────────────────────────────────────────
# РЕЗУЛЬТАТ
# ──────────────────────────────────────────────────────────────

async def _show_result(callback: CallbackQuery, state: FSMContext, qtype: str):
    data = await state.get_data()
    scores = data.get('scores', {})
    gender = data.get('gender', 'female')

    stone_id = _calculate_result(scores, qtype)
    stone = _get_stone_info(stone_id)

    emoji = stone.get('EMOJI', '💎')
    title = stone.get('TITLE', stone_id)
    short_desc = stone.get('SHORT_DESC', '')
    full_desc = stone.get('FULL_DESC', '')
    chakra = stone.get('CHAKRA', '')

    if qtype == 'quiz':
        header = "🔮 *ТВОЙ КАМЕНЬ*"
        sub = "По результатам теста именно этот камень резонирует с тобой прямо сейчас."
        await FunnelTracker.track(callback.from_user.id, 'quiz_complete', stone_id)
    else:
        header = "🦊 *ТВОЙ ТОТЕМНЫЙ КАМЕНЬ*"
        sub = "Этот камень — отражение твоей глубинной природы. Он резонирует с тем, кто ты есть на самом деле."
        await FunnelTracker.track(callback.from_user.id, 'totem_complete', stone_id)

    desc_preview = full_desc[:600] + "..." if len(full_desc) > 600 else full_desc

    text = (
        f"{header}\n\n"
        f"{emoji} *{title}*\n\n"
        f"_{short_desc}_\n\n"
        f"{desc_preview}\n\n"
    )
    if chakra:
        text += f"🌀 *Чакра:* {chakra}\n\n"

    text += f"_{sub}_"

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 ПОСМОТРЕТЬ ВИТРИНУ", callback_data="showcase")],
            [InlineKeyboardButton(text="📚 БАЗА ЗНАНИЙ", callback_data="knowledge")],
            [InlineKeyboardButton(text="🔄 ПРОЙТИ ЕЩЁ РАЗ", callback_data=f"{'quiz' if qtype == 'quiz' else 'totem'}")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )

