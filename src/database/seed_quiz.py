"""
Заполнение таблиц quiz_questions и totem_questions начальными данными.
Запускается один раз при инициализации.
"""
import json
from src.database.db import db


def seed_quiz_questions():
    """Вставить вопросы квиза если таблица пустая."""
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM quiz_questions")
        if c.fetchone()['cnt'] > 0:
            return

        questions = [
            ("Что сейчас важнее всего в твоей жизни?",
             json.dumps(["Любовь и отношения", "Деньги и карьера", "Защита и стабильность", "Духовное развитие"]),
             json.dumps({"rose_quartz": 3, "citrine": 3, "black_tourmaline": 3, "amethyst": 3}), 1),

            ("Какое твоё внутреннее состояние прямо сейчас?",
             json.dumps(["Тревога и стресс", "Усталость и апатия", "Злость и раздражение", "Поиск и неопределённость"]),
             json.dumps({"lepidolite": 3, "carnelian": 2, "black_tourmaline": 2, "labradorite": 3}), 2),

            ("Чего тебе не хватает?",
             json.dumps(["Любви к себе", "Энергии и сил", "Денег и удачи", "Ясности в голове"]),
             json.dumps({"rose_quartz": 3, "garnet": 3, "citrine": 3, "fluorite": 3}), 3),

            ("Как ты чувствуешь себя среди людей?",
             json.dumps(["Устаю от общения", "Не могу сказать нет", "Одиноко даже в толпе", "Боюсь быть непонятым"]),
             json.dumps({"black_tourmaline": 3, "amazonite": 3, "rhodonite": 3, "sodalite": 3}), 4),

            ("Какой результат хочешь получить?",
             json.dumps(["Больше любви и гармонии", "Силу двигаться вперёд", "Защиту от всего плохого", "Интуицию и связь с собой"]),
             json.dumps({"rose_quartz": 3, "tiger_eye": 3, "black_tourmaline": 3, "amethyst": 3}), 5),
        ]

        for q in questions:
            c.execute("""INSERT INTO quiz_questions (question, options, weights, sort_order)
                         VALUES (?, ?, ?, ?)""",
                      (q[0], q[1], q[2], q[3]))


def seed_totem_questions():
    """Вставить вопросы тотемного квиза если таблица пустая."""
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM totem_questions")
        if c.fetchone()['cnt'] > 0:
            return

        questions = [
            ("Как ты восстанавливаешь силы?",
             json.dumps(["В природе и тишине", "В компании близких", "В одиночестве и медитации", "В движении и действии"]),
             json.dumps({"moonstone": 3, "rose_quartz": 2, "amethyst": 3, "carnelian": 3}), 1),

            ("Что для тебя значит сила?",
             json.dumps(["Любовь — она сильнее всего", "Деньги и независимость", "Защита близких", "Знание и мудрость"]),
             json.dumps({"rose_quartz": 3, "citrine": 3, "black_tourmaline": 3, "labradorite": 3}), 2),

            ("Как ты принимаешь важные решения?",
             json.dumps(["По велению сердца", "Логически взвешивая", "Интуитивно — чувствую", "Советуюсь с кем-то близким"]),
             json.dumps({"rose_quartz": 2, "sodalite": 3, "labradorite": 3, "moonstone": 2}), 3),

            ("Твоя главная мечта?",
             json.dumps(["Настоящая любовь", "Финансовая свобода", "Реализация своего предназначения", "Покой и здоровье близких"]),
             json.dumps({"rose_quartz": 3, "citrine": 3, "labradorite": 3, "lepidolite": 2}), 4),

            ("Если бы у тебя была суперспособность?",
             json.dumps(["Видеть будущее", "Притягивать удачу", "Защищать от любого зла", "Исцелять людей"]),
             json.dumps({"labradorite": 3, "citrine": 3, "black_tourmaline": 3, "rose_quartz": 3}), 5),
        ]

        for q in questions:
            c.execute("""INSERT INTO totem_questions (question, options, weights, sort_order)
                         VALUES (?, ?, ?, ?)""",
                      (q[0], q[1], q[2], q[3]))


def run_all_seeds():
    seed_quiz_questions()
    seed_totem_questions()
