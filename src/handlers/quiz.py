"""
Квиз "Узнай свой камень" — перенос из сайта.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.utils.crystals import crystals

logger = logging.getLogger(__name__)
router = Router()


class QuizStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()


# ──────────────────────────────────────────────────────────────
# ВОПРОСЫ КВИЗА — из сайта
# ──────────────────────────────────────────────────────────────

QUIZ_QUESTIONS = [
    {
        'text': 'Что сейчас доминирует в вашем внутреннем состоянии?\n\nВыберите то, что наиболее точно описывает ваш текущий эмоциональный фон.',
        'options': [
            ('Тревога, беспокойство, ощущение угрозы', ['Тревога', 'Защита', 'Страхи']),
            ('Апатия, потеря смысла, эмоциональное выгорание', ['Выгорание', 'Усталость', 'Апатия']),
            ('Гнев, раздражительность, внутреннее напряжение', ['Стресс', 'Гнев', 'Конфликты']),
            ('Грусть, ощущение утраты, одиночество', ['Обиды', 'Потеря', 'Одиночество']),
            ('Рассеянность, потеря фокуса и концентрации', ['Концентрация', 'Ясность', 'Фокус']),
            ('Спокойствие, умиротворение — хочу углубить это состояние', ['Гармония', 'Баланс', 'Медитация', 'Спокойствие']),
            ('Любовь, благодарность — хочу усилить и направить эту энергию', ['Любовь', 'Исцеление', 'Сердечная', 'Гармония']),
        ]
    },
    {
        'text': 'Какая сфера вашей жизни требует наибольшего внимания?\n\nОпределите приоритетное направление для работы с энергией.',
        'options': [
            ('Эмоциональное здоровье и внутренний баланс', ['Баланс', 'Гармония', 'Исцеление']),
            ('Отношения — доверие, близость, принятие', ['Обиды', 'Потеря', 'Самооценка', 'Любовь']),
            ('Карьера, финансы, реализация целей', ['Мотивация', 'Уверенность', 'Успех', 'Финансы']),
            ('Интуиция, духовное развитие, самопознание', ['Интуиция', 'Ясность', 'Медитация', 'Мудрость']),
            ('Физическое самочувствие, восстановление сил', ['Здоровье', 'Усталость', 'Энергия', 'Восстановление']),
        ]
    },
    {
        'text': 'Как вы ощущаете свою энергию прямо сейчас?\n\nЧестная оценка ресурсного состояния — ключ к точной рекомендации.',
        'options': [
            ('Истощение — ресурса нет, нужна мягкая подпитка', ['Усталость', 'Выгорание', 'Восстановление']),
            ('Нестабильность — перепады, непредсказуемые эмоции', ['Баланс', 'Стресс', 'Гармония']),
            ('Блокировка — энергия есть, но она заперта внутри', ['Блокировки', 'Страхи', 'Трансформация']),
            ('Избыточность — слишком много, не могу направить', ['Концентрация', 'Фокус', 'Заземление']),
            ('Стабильность — хочу углубить практику и рост', ['Интуиция', 'Мудрость', 'Медитация']),
        ]
    },
    {
        'text': 'Какой тип поддержки вам нужен от камня?\n\nКаждый минерал работает по-разному — определите вектор.',
        'options': [
            ('Защита — щит от негатива, энергетических атак и сглаза', ['Защита', 'Тревога', 'Заземление']),
            ('Исцеление — освобождение от старых ран, обид и травм', ['Исцеление', 'Обиды', 'Потеря', 'Трансформация']),
            ('Активация — пробуждение внутренней силы и решимости действовать', ['Мотивация', 'Уверенность', 'Энергия', 'Успех']),
            ('Ясность — обострение интуиции и глубинное понимание ситуации', ['Ясность', 'Интуиция', 'Концентрация']),
            ('Гармония — глубокое внутреннее спокойствие и принятие себя', ['Гармония', 'Баланс', 'Спокойствие']),
            ('Трансформация — выход на новый уровень, перезагрузка жизни', ['Трансформация', 'Мудрость', 'Интуиция', 'Медитация']),
        ]
    },
    {
        'text': 'Какой энергетический центр вы чувствуете наиболее ослабленным?\n\nЕсли не уверены — выберите область тела, где ощущаете дискомфорт или пустоту.',
        'options': [
            ('Муладхара (основание) — нестабильность, страх, отсутствие опоры', ['Корневая']),
            ('Свадхистана (низ живота) — подавленные эмоции, потеря радости и удовольствия', ['Сакральная']),
            ('Манипура (солнечное сплетение) — неуверенность, потеря воли и личной силы', ['Солнечное сплетение']),
            ('Анахата (сердце) — закрытость, обиды, недоверие к людям и миру', ['Сердечная']),
            ('Вишудха (горло) — трудно выражать мысли, страх быть услышанным', ['Горловая']),
            ('Аджна (третий глаз) — потеря интуиции, спутанность сознания', ['Третий глаз']),
            ('Сахасрара (макушка) — потеря связи с высшим, духовная пустота', ['Коронная']),
        ]
    },
]


def get_recommendations(selected_answers):
    all_tags = []
    for q_idx, a_idx in selected_answers.items():
        q = QUIZ_QUESTIONS[int(q_idx)]
        tags = q['options'][a_idx][1]
        all_tags.extend(tags)

    scored = []
    for crystal in crystals:
        score = 0
        for tag in all_tags:
            if tag in crystal['problems']:
                score += 3
            if tag in crystal['chakras']:
                score += 2
            if any(tag.lower() in effect.lower() for effect in crystal['effects']):
                score += 1
        if score > 0:
            scored.append((crystal, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:3]


@router.callback_query(F.data == "quiz")
async def quiz_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(QuizStates.q1)
    q = QUIZ_QUESTIONS[0]
    buttons = []
    for i, (label, _) in enumerate(q['options']):
        buttons.append([InlineKeyboardButton(text=f"{i+1}. {label}", callback_data=f"quiz_a_{i}")])
    buttons.append([InlineKeyboardButton(text="← НАЗАД", callback_data="menu")])

    await callback.message.edit_text(
        f"💎 *МИНИ-ДИАГНОСТИКА ЭНЕРГЕТИЧЕСКОГО СОСТОЯНИЯ*\n\n{q['text']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("quiz_a_"), QuizStates())
async def quiz_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    answers = data.get('answers', {})

    q_num = int(str(await state.get_state()).split('.')[-1][1:])  # q1 -> 1
    a_idx = int(callback.data.split('_')[-1])

    answers[q_num - 1] = a_idx
    await state.update_data(answers=answers)

    next_q = q_num
    if next_q < 5:
        await state.set_state(getattr(QuizStates, f"q{next_q + 1}"))
        q = QUIZ_QUESTIONS[next_q]
        buttons = []
        for i, (label, _) in enumerate(q['options']):
            buttons.append([InlineKeyboardButton(text=f"{i+1}. {label}", callback_data=f"quiz_a_{i}")])
        buttons.append([InlineKeyboardButton(text="← НАЗАД", callback_data=f"quiz_back_{q_num}")])

        await callback.message.edit_text(
            f"💎 *МИНИ-ДИАГНОСТИКА ЭНЕРГЕТИЧЕСКОГО СОСТОЯНИЯ*\n\n{q['text']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Results
        recommendations = get_recommendations(answers)
        text = "💎 *РЕЗУЛЬТАТ МИНИ-ДИАГНОСТИКИ*\n\n"
        if recommendations:
            text += "На основе ваших ответов мы определили минералы с наивысшим энергетическим резонансом:\n\n"
            for i, (crystal, score) in enumerate(recommendations, 1):
                text += f"{i}. {crystal['name']} (совпадение {min(int((score / 15) * 100), 99)}%)\n"
        else:
            text += "Рекомендация не найдена. Попробуйте пройти ещё раз."

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="ПРОЙТИ ЕЩЁ РАЗ", callback_data="quiz")],
                [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")]
            ])
        )
        await state.clear()


@router.callback_query(F.data.startswith("quiz_back_"))
async def quiz_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    q_num = int(callback.data.split('_')[-1])
    await state.set_state(getattr(QuizStates, f"q{q_num}"))
    q = QUIZ_QUESTIONS[q_num - 1]
    buttons = []
    for i, (label, _) in enumerate(q['options']):
        buttons.append([InlineKeyboardButton(text=f"{i+1}. {label}", callback_data=f"quiz_a_{i}")])
    buttons.append([InlineKeyboardButton(text="← НАЗАД", callback_data="menu" if q_num == 1 else f"quiz_back_{q_num-1}")])

    await callback.message.edit_text(
        f"💎 *МИНИ-ДИАГНОСТИКА ЭНЕРГЕТИЧЕСКОГО СОСТОЯНИЯ*\n\n{q['text']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


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

