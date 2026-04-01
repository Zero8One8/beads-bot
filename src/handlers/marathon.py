"""
Марафон 21 день — платный закрытый клуб ежедневных практик.
Каждый день новая практика с камнями. Оплата через Stars.
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.database.models import UserModel
from src.config import Config
from src.services.stars_payment import StarsPayment

logger = logging.getLogger(__name__)
router = Router()

MARATHON_PRICE_STARS = 500  # Цена марафона в Stars

# 21 день практик с камнями
MARATHON_DAYS = [
    ("🌱 День 1: Начало пути", "rose_quartz",
     "Сегодня — день знакомства с собой.\n\n"
     "Возьми розовый кварц в обе ладони. Сядь удобно, закрой глаза. "
     "10 минут просто дыши и чувствуй тепло камня. Никаких мыслей о делах — "
     "только ты и камень. Если мысли приходят — не гони, просто возвращайся к ощущению тепла.\n\n"
     "После: запиши одно слово — как ты себя чувствуешь прямо сейчас."),
    ("🔥 День 2: Зажги огонь", "carnelian",
     "Сегодня — день пробуждения энергии.\n\n"
     "Возьми сердолик. Встань прямо, ноги на ширине плеч. "
     "Держи камень в правой руке у солнечного сплетения. "
     "3 глубоких вдоха — на каждом выдохе чувствуй как энергия поднимается от живота вверх.\n\n"
     "Скажи вслух: «Я полон(а) сил. Я действую. Я создаю свою жизнь».\n\n"
     "Носи сердолик весь день на правой руке."),
    ("🛡 День 3: Защити себя", "black_tourmaline",
     "Сегодня — день создания защиты.\n\n"
     "Утром: возьми чёрный турмалин, пройди по всем комнатам своего дома. "
     "Представляй как от камня исходит чёрный защитный свет, заполняющий пространство.\n\n"
     "Вечером: положи турмалин у входной двери или под кровать.\n\n"
     "Практика: запиши 3 вещи от которых хочешь защититься. Сожги бумагу (или порви)."),
    ("💰 День 4: Открой поток", "citrine",
     "Сегодня — день финансового намерения.\n\n"
     "Утром: положи цитрин на купюру (любую). Скажи: «Деньги легко приходят ко мне. "
     "Я принимаю изобилие». Оставь так на весь день.\n\n"
     "В течение дня: обращай внимание на все возможности заработать — даже маленькие. "
     "Цитрин обостряет финансовое зрение.\n\n"
     "Вечером: запиши 3 способа как ты можешь получить больше денег."),
    ("💜 День 5: Углубись", "amethyst",
     "Сегодня — день медитации.\n\n"
     "Самая сложная и самая важная практика марафона: 20 минут в тишине с аметистом.\n\n"
     "Ляг на спину. Аметист на третий глаз (лоб между бровями). "
     "Ничего не делай — просто наблюдай за своим умом как зритель. "
     "Не оценивай мысли — просто смотри как они приходят и уходят.\n\n"
     "После: запиши всё что пришло. Иногда в медитации приходят важные ответы."),
    ("🌙 День 6: Женская сила", "moonstone",
     "Сегодня — день связи с интуицией.\n\n"
     "Лунный камень — камень чувств и предвидения. "
     "Носи его весь день на левом запястье.\n\n"
     "Практика: в течение дня 3 раза останови всё что делаешь. "
     "Закрой глаза на 30 секунд. Задай себе вопрос: «Что я сейчас чувствую?» "
     "Не думай — почувствуй. Запиши ответ.\n\n"
     "На ночь: камень под подушку. Утром запиши сон — даже обрывки."),
    ("🌿 День 7: Итог первой недели", "clear_quartz",
     "Сегодня — день интеграции.\n\n"
     "🎉 Ты прошёл(а) первую неделю! Это важно.\n\n"
     "Горный хрусталь — усилитель и чистильщик. "
     "Сегодня возьми все камни которые у тебя есть. Разложи перед собой. "
     "Горный хрусталь в центр. Посиди с ними 10 минут.\n\n"
     "Потом: почисти все камни (вода, земля или лунный свет).\n\n"
     "Напиши: что изменилось за 7 дней? Даже маленькое — считается."),
    ("❤️ День 8: Исцели сердце", "rhodonite",
     "Сегодня — день прощения.\n\n"
     "Родонит работает с болью которую мы не отпустили.\n\n"
     "Сядь. Родонит в левой руке у сердца. Подумай о человеке "
     "которого тяжело простить — даже себя. Не нужно говорить вслух.\n\n"
     "Скажи мысленно: «Я вижу твою боль. Я вижу свою боль. "
     "Я выбираю освободиться от этого». Повтори 3 раза.\n\n"
     "Это не значит что ты одобряешь то что было. Это значит что ты свободен(на)."),
    ("🔮 День 9: Открой интуицию", "labradorite",
     "Сегодня — день магии.\n\n"
     "Лабрадорит — камень мага. Он показывает то что скрыто.\n\n"
     "Утром: не смотри в телефон первые 10 минут. Держи лабрадорит и наблюдай "
     "за образами которые приходят в полудрёме.\n\n"
     "В течение дня: если чувствуешь интуитивный импульс — последуй ему "
     "(если это безопасно). Запиши что вышло.\n\n"
     "Вечером: медитация 15 минут. Вопрос к камню: «Что мне важно знать прямо сейчас?»"),
    ("💙 День 10: Говори правду", "sodalite",
     "Сегодня — день честности.\n\n"
     "Содалит помогает говорить правду — себе и другим.\n\n"
     "Практика: напиши 5 вещей которые ты давно хотел(а) сказать — "
     "но не говорил(а). Кому угодно, о чём угодно. Только честно.\n\n"
     "Потом реши: какую из них ты готов(а) сказать сегодня? Даже одну.\n\n"
     "Носи содалит на шее весь день — он поможет найти слова."),
    ("⚡ День 11: Зарядись", "garnet",
     "Сегодня — день максимальной энергии.\n\n"
     "Гранат — огонь в крови, жизненная сила.\n\n"
     "Утренняя зарядка с камнем: 10 минут любого движения (прыжки, ходьба, танец) "
     "с гранатом в правой руке. Чувствуй как энергия растёт.\n\n"
     "Практика: запиши 3 желания которые тебя ВОЗБУЖДАЮТ — не «надо», а «хочу». "
     "Гранат усиливает страсть и желание.\n\n"
     "Не снимай весь день. Вечером — можно снять, он активный."),
    ("🌊 День 12: Найди покой", "lepidolite",
     "Сегодня — день тишины.\n\n"
     "После 11 дней активных практик — день отдыха нервной системы.\n\n"
     "Лепидолит весь день. Никаких форсированных действий.\n\n"
     "Практика: найди 30 минут которые принадлежат только тебе. "
     "Выключи всё. Просто будь. С камнем в руках.\n\n"
     "Вечером: тёплая ванна (камень рядом, не в воде). "
     "Перед сном — под подушку. Сегодня твоя задача — хорошо поспать."),
    ("🎯 День 13: Укрепи намерение", "tiger_eye",
     "Сегодня — день решимости.\n\n"
     "Тигровый глаз — хладнокровие и точность.\n\n"
     "Практика: запиши свою ГЛАВНУЮ цель. Одну. Максимально конкретно: "
     "не «хочу денег», а «хочу зарабатывать 150 000 рублей к марту».\n\n"
     "Держи тигровый глаз в руках пока пишешь. Потом перечитай вслух.\n\n"
     "Носи весь день на правой руке. Каждый раз когда видишь камень — "
     "вспоминай цель. Это программирование подсознания."),
    ("🌸 День 14: Полюби себя", "rose_quartz",
     "Сегодня — день безусловной любви к себе.\n\n"
     "Две недели позади. Ты молодец(молодчина) — серьёзно.\n\n"
     "Практика перед зеркалом: встань, посмотри себе в глаза. "
     "Розовый кварц к сердцу. Скажи вслух — голосом, не мысленно:\n\n"
     "«Я принимаю себя таким(ой) как есть. Я достоин(на) любви. "
     "Я забочусь о себе. Я важен(важна)».\n\n"
     "Да, это неловко. Да, именно поэтому это работает."),
    ("💎 День 15: Усиль всё", "clear_quartz",
     "Сегодня — день усиления.\n\n"
     "Горный хрусталь — универсальный усилитель.\n\n"
     "Сегодня носи горный хрусталь вместе с камнем с которым у тебя "
     "самый сильный отклик за эти 2 недели. Они будут работать вместе.\n\n"
     "Практика: перечитай всё что ты записывал(а) за 14 дней. "
     "Отметь что изменилось. Это важно — мы часто не замечаем прогресс."),
    ("🌟 День 16: Витрина желаний", "citrine",
     "Сегодня — день материализации.\n\n"
     "Найди 3 картинки которые символизируют твою цель. "
     "Распечатай или сохрани в телефоне как обои.\n\n"
     "Цитрин перед этими картинками на 15 минут. "
     "Смотри на них и чувствуй как будто это уже есть в твоей жизни. "
     "Не «хочу» — а «имею, чувствую, живу с этим».\n\n"
     "Это основа метода вайб-манифестации — камень усиливает вибрацию."),
    ("🌀 День 17: Чистка пространства", "obsidian",
     "Сегодня — день глубокой уборки.\n\n"
     "Обсидиан — зеркало которое показывает что нужно убрать.\n\n"
     "Физически: разбери одно место в доме которое давно ждёт — "
     "ящик, полку, шкаф. Во время уборки обсидиан рядом.\n\n"
     "Энергетически: пройди по дому с обсидианом в руке. "
     "В каждом углу скажи: «Здесь только свет, покой и сила».\n\n"
     "После — обязательно очисти обсидиан под проточной водой."),
    ("🦋 День 18: Принятие перемен", "labradorite",
     "Сегодня — день трансформации.\n\n"
     "Лабрадорит — камень тех кто меняется.\n\n"
     "Запиши: что в твоей жизни ты хочешь изменить, но боишься?\n\n"
     "Держи лабрадорит и перечитай. Задай себе вопрос: "
     "«Что самое страшное случится если я это изменю?» Запиши ответ.\n\n"
     "Чаще всего страх оказывается больше реальной угрозы. "
     "Камень помогает увидеть это ясно."),
    ("💫 День 19: Благодарность", "rose_quartz",
     "Сегодня — день благодарности.\n\n"
     "Самая мощная практика которую большинство игнорирует.\n\n"
     "Розовый кварц в руках. Напиши 21 вещь за которые ты благодарен(на). "
     "Именно 21 — первые 5 легко, дальше начинается настоящая работа.\n\n"
     "Включи в список: тело (оно работает), камни (они с тобой эти 19 дней), "
     "эту практику, что-то болезненное что тебя чему-то научило.\n\n"
     "Благодарность открывает канал для следующего изобилия."),
    ("⚡ День 20: Финальный разгон", "garnet",
     "Сегодня — день максимального импульса.\n\n"
     "Завтра последний день. Сегодня — мощный финальный разгон.\n\n"
     "Напиши конкретный план на следующие 30 дней. 3 главные цели. "
     "По каждой — 3 действия которые ты сделаешь на этой неделе.\n\n"
     "Гранат в правой руке пока пишешь.\n\n"
     "Вечером: перечитай весь свой дневник марафона. "
     "Ты прошёл(а) 20 дней — это не маленький результат."),
    ("🏆 День 21: Ты сделал(а) это!", "clear_quartz",
     "🎉 *ПОЗДРАВЛЯЮ! 21 ДЕНЬ ПРОЙДЕН!*\n\n"
     "Это настоящее достижение. Большинство людей не доходят до конца.\n\n"
     "Последняя практика: возьми горный хрусталь и все камни с которыми работал(а). "
     "Разложи перед собой. Посиди в тишине 21 минуту.\n\n"
     "Потом скажи вслух: «Я завершил(а) то что начал(а). "
     "Я держу своё слово себе. Я меняюсь к лучшему».\n\n"
     "Поздравления от мастера придут отдельно. "
     "Ты заслужил(а) скидку 15% на следующий заказ 🎁"),
]


@router.callback_query(F.data == "marathon")
async def marathon_start(callback: CallbackQuery):
    """Страница марафона."""
    user_id = callback.from_user.id

    with db.cursor() as c:
        c.execute("""SELECT day_number, status FROM marathon_participants
                     WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1""",
                  (user_id,))
        participant = c.fetchone()

    if participant:
        day = participant['day_number']
        await callback.message.edit_text(
            f"🏃 *МАРАФОН 21 ДЕНЬ*\n\n"
            f"Ты на дне *{day} из 21*!\n\n"
            f"Нажми чтобы открыть практику сегодняшнего дня.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📖 ПРАКТИКА ДНЯ {day}", callback_data=f"marathon_day_{day}")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
    else:
        await callback.message.edit_text(
            "🏃 *МАРАФОН 21 ДЕНЬ*\n\n"
            "21 день ежедневных практик с камнями.\n\n"
            "Каждый день — новая практика. Каждый день — маленький шаг к большим переменам.\n\n"
            "📅 21 день\n"
            "💎 Разные камни каждый день\n"
            "📝 Дневник практик\n"
            "🎁 Скидка 15% после завершения\n\n"
            f"💰 Стоимость: *{MARATHON_PRICE_STARS}⭐ Telegram Stars*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"⭐ УЧАСТВОВАТЬ — {MARATHON_PRICE_STARS} Stars",
                                      callback_data="marathon_pay")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )
    await callback.answer()


@router.callback_query(F.data == "marathon_pay")
async def marathon_pay(callback: CallbackQuery, bot: Bot):
    """Оплата марафона."""
    await StarsPayment.create_invoice(
        bot=bot,
        user_id=callback.from_user.id,
        title="Марафон 21 день",
        description="21 день ежедневных практик с камнями",
        payload=f"marathon_{callback.from_user.id}",
        amount_rub=MARATHON_PRICE_STARS
    )
    await callback.answer("💳 Счёт создан!", show_alert=False)


@router.callback_query(F.data.startswith("marathon_day_"))
async def marathon_show_day(callback: CallbackQuery):
    """Показать практику дня."""
    user_id = callback.from_user.id
    day = int(callback.data.replace("marathon_day_", ""))

    if day < 1 or day > 21:
        await callback.answer("День не найден", show_alert=True)
        return

    day_data = MARATHON_DAYS[day - 1]
    title, stone_id, text = day_data

    # Load stone info
    from src.utils.text_loader import ContentLoader
    stones = ContentLoader.load_all_stones()
    stone = stones.get(stone_id, {})
    emoji = stone.get('EMOJI', '💎')
    stone_name = stone.get('TITLE', stone_id)

    full_text = (
        f"*{title}*\n\n"
        f"Камень дня: {emoji} *{stone_name}*\n\n"
        f"{text}"
    )

    buttons = []
    if day < 21:
        # Mark as done and show next day button
        buttons.append([InlineKeyboardButton(
            text="✅ ПРАКТИКА ВЫПОЛНЕНА",
            callback_data=f"marathon_done_{day}"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="🏆 МАРАФОН ЗАВЕРШЁН!",
            callback_data="marathon_complete"
        )])
    buttons.append([InlineKeyboardButton(text="← К МАРАФОНУ", callback_data="marathon")])

    await callback.message.edit_text(
        full_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("marathon_done_"))
async def marathon_mark_done(callback: CallbackQuery):
    """Отметить день выполненным."""
    user_id = callback.from_user.id
    day = int(callback.data.replace("marathon_done_", ""))
    next_day = day + 1

    with db.cursor() as c:
        c.execute("""UPDATE marathon_participants SET day_number = ?, last_day_at = ?
                     WHERE user_id = ? AND status = 'active'""",
                  (next_day, datetime.now(), user_id))

    await callback.answer(f"✅ День {day} засчитан!", show_alert=False)

    if next_day <= 21:
        await callback.message.edit_text(
            f"✅ *День {day} выполнен!*\n\n"
            f"Ты на *{next_day} из 21*!\n\n"
            f"Возвращайся завтра за следующей практикой.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📖 ПРАКТИКА ДНЯ {next_day}", callback_data=f"marathon_day_{next_day}")],
                [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
            ])
        )


@router.callback_query(F.data == "marathon_complete")
async def marathon_complete(callback: CallbackQuery, bot: Bot):
    """Завершение марафона."""
    user_id = callback.from_user.id

    with db.cursor() as c:
        c.execute("""UPDATE marathon_participants SET status = 'completed', last_day_at = ?
                     WHERE user_id = ? AND status = 'active'""",
                  (datetime.now(), user_id))

    # Начисляем скидку через промокод
    import random, string
    promo_code = f"MARATHON{''.join(random.choices(string.ascii_uppercase, k=6))}"
    with db.cursor() as c:
        c.execute("""INSERT OR IGNORE INTO promocodes
                     (code, discount_pct, max_uses, created_at, active)
                     VALUES (?, 15, 1, ?, 1)""",
                  (promo_code, datetime.now()))

    await callback.message.edit_text(
        f"🏆 *МАРАФОН ЗАВЕРШЁН!*\n\n"
        f"Ты прошёл(а) все 21 день! Это настоящий результат.\n\n"
        f"🎁 *Твой подарок:*\n"
        f"Промокод на скидку 15%: `{promo_code}`\n\n"
        f"Действует на следующий заказ. Введи при оформлении.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 СДЕЛАТЬ ЗАКАЗ", callback_data="showcase")],
            [InlineKeyboardButton(text="← МЕНЮ", callback_data="menu")],
        ])
    )

    # Уведомление мастеру
    try:
        user = UserModel.get(user_id)
        name = user.get('first_name', '') or user.get('username', '') or str(user_id)
        await bot.send_message(
            Config.ADMIN_ID,
            f"🏆 *{name}* завершил(а) Марафон 21 день!\n"
            f"Промокод: `{promo_code}`\n"
            f"ID: {user_id}",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.answer()


async def activate_marathon_participant(user_id: int, charge_id: str):
    """Активировать участие в марафоне после оплаты (вызывается из payment.py)."""
    with db.cursor() as c:
        c.execute("""INSERT OR IGNORE INTO marathon_participants
                     (user_id, day_number, started_at, last_day_at, status, payment_charge_id)
                     VALUES (?, 1, ?, ?, 'active', ?)""",
                  (user_id, datetime.now(), datetime.now(), charge_id))
