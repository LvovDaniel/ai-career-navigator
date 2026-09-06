from fastapi import FastAPI
from pydantic import BaseModel
import psycopg
from psycopg.types.json import Json
from dotenv import load_dotenv
from openai import OpenAI
import os
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()


def get_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "ai_navigator"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "admin123")
    )


# =========================
# МОДЕЛИ
# =========================

class User(BaseModel):
    name: str
    email: str
    goal: str


class Profile(BaseModel):
    user_id: int
    skills: list[str] = []
    experience: str = ""
    projects: list[str] = []


class UserSkill(BaseModel):
    user_id: int
    skill: str
    level: int


# =========================
# ГЛАВНАЯ
# =========================

@app.get("/")
def root():
    return {
        "message": "AI Career Navigator работает!"
    }


# =========================
# ПРОВЕРКА СЕРВЕРА
# =========================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================
# СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
# =========================

@app.post("/users")
def create_user(user: User):

    conn = get_db()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (name, email, goal)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                user.name,
                user.email,
                user.goal
            )
        )

        user_id = cur.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "message": "Пользователь создан",
        "user_id": user_id,
        "user": user
    }


# =========================
# ПОЛУЧИТЬ ПРОФИЛЬ
# =========================

@app.get("/profile/{user_id}")
def get_profile(user_id: int):

    conn = get_db()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, resume, goal
            FROM users
            WHERE id = %s;
            """,
            (user_id,)
        )

        user = cur.fetchone()

    conn.close()

    if user is None:
        return {
            "error": "Пользователь не найден"
        }

    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
        "resume": user[3],
        "goal": user[4]
    }


# =========================
# СОХРАНИТЬ ПРОФИЛЬ
# =========================

@app.post("/profile")
def create_profile(profile: Profile):

    conn = get_db()

    with conn.cursor() as cur:

        for project in profile.projects:
            cur.execute(
                """
                INSERT INTO projects (user_id, name, description)
                VALUES (%s, %s, %s);
                """,
                (
                    profile.user_id,
                    project,
                    ""
                )
            )

    conn.commit()
    conn.close()

    return {
        "message": "Профиль сохранён",
        "profile": profile
    }


# =========================
# ДОБАВИТЬ НАВЫК
# =========================

@app.post("/skills")
def add_skill(user_skill: UserSkill):

    if user_skill.level < 1 or user_skill.level > 5:
        return {
            "error": "Уровень навыка должен быть от 1 до 5"
        }

    conn = get_db()

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO skills (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
            """,
            (user_skill.skill,)
        )

        result = cur.fetchone()

        if result:
            skill_id = result[0]
        else:
            cur.execute(
                """
                SELECT id
                FROM skills
                WHERE name = %s;
                """,
                (user_skill.skill,)
            )

            skill_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO user_skills (user_id, skill_id, level)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, skill_id)
            DO UPDATE SET level = EXCLUDED.level;
            """,
            (
                user_skill.user_id,
                skill_id,
                user_skill.level
            )
        )

    conn.commit()
    conn.close()

    return {
        "message": "Навык сохранён",
        "skill": user_skill.skill,
        "level": user_skill.level
    }


# =========================
# ПОЛУЧИТЬ НАВЫКИ
# =========================

@app.get("/skills/{user_id}")
def get_skills(user_id: int):

    conn = get_db()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT skills.name, user_skills.level
            FROM user_skills
            JOIN skills
                ON skills.id = user_skills.skill_id
            WHERE user_skills.user_id = %s;
            """,
            (user_id,)
        )

        skills = cur.fetchall()

    conn.close()

    return {
        "user_id": user_id,
        "skills": [
            {
                "name": skill[0],
                "level": skill[1]
            }
            for skill in skills
        ]
    }


# =========================
# ПОЛНЫЙ ПРОФИЛЬ
# =========================

@app.get("/profile/full/{user_id}")
def get_full_profile(user_id: int):

    conn = get_db()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id, name, email, resume, goal
            FROM users
            WHERE id = %s;
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if user is None:
            conn.close()

            return {
                "error": "Пользователь не найден"
            }

        cur.execute(
            """
            SELECT skills.name, user_skills.level
            FROM user_skills
            JOIN skills
                ON skills.id = user_skills.skill_id
            WHERE user_skills.user_id = %s;
            """,
            (user_id,)
        )

        skills = cur.fetchall()

        cur.execute(
            """
            SELECT name, description
            FROM projects
            WHERE user_id = %s;
            """,
            (user_id,)
        )

        projects = cur.fetchall()

    conn.close()

    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
        "resume": user[3],
        "goal": user[4],

        "skills": [
            {
                "name": skill[0],
                "level": skill[1]
            }
            for skill in skills
        ],

        "projects": [
            {
                "name": project[0],
                "description": project[1]
            }
            for project in projects
        ]
    }


# =========================
# ПОЛУЧИТЬ ВАКАНСИИ
# =========================

@app.get("/vacancies")
def get_vacancies():

    conn = get_db()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id, title, company, description, required_skills
            FROM vacancies;
            """
        )

        vacancies = cur.fetchall()

    conn.close()

    return {
        "vacancies": [
            {
                "id": vacancy[0],
                "title": vacancy[1],
                "company": vacancy[2],
                "description": vacancy[3],
                "required_skills": vacancy[4]
            }
            for vacancy in vacancies
        ]
    }


# =========================
# АНАЛИЗ ПРОФИЛЯ С AI
# =========================

@app.post("/analyze")
def analyze_profile(user_id: int):

    # =========================
    # ПОЛУЧАЕМ ДАННЫЕ ИЗ БД
    # =========================

    conn = get_db()

    with conn.cursor() as cur:

        # Пользователь
        cur.execute(
            """
            SELECT name, resume, goal
            FROM users
            WHERE id = %s;
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if user is None:
            conn.close()

            return {
                "error": "Пользователь не найден"
            }

        name = user[0]
        resume = user[1] or ""
        goal = user[2]

        # Навыки
        cur.execute(
            """
            SELECT skills.name, user_skills.level
            FROM user_skills
            JOIN skills
                ON skills.id = user_skills.skill_id
            WHERE user_skills.user_id = %s;
            """,
            (user_id,)
        )

        skills = cur.fetchall()

        # Проекты
        cur.execute(
            """
            SELECT name, description
            FROM projects
            WHERE user_id = %s;
            """,
            (user_id,)
        )

        projects = cur.fetchall()

        # Вакансии
        cur.execute(
            """
            SELECT id, title, company, description, required_skills
            FROM vacancies;
            """
        )

        vacancies = cur.fetchall()

    conn.close()

    # =========================
    # ПОДГОТОВКА ДАННЫХ
    # =========================

    user_skills = [
        {
            "name": skill[0],
            "level": skill[1]
        }
        for skill in skills
    ]

    user_projects = [
        {
            "name": project[0],
            "description": project[1]
        }
        for project in projects
    ]

    vacancy_data = [
        {
            "id": vacancy[0],
            "title": vacancy[1],
            "company": vacancy[2],
            "description": vacancy[3],
            "required_skills": vacancy[4]
        }
        for vacancy in vacancies
    ]

    # =========================
    # ФОРМИРУЕМ ЗАПРОС К AI
    # =========================

    prompt = f"""
Ты карьерный консультант системы AI Career Navigator.

Проанализируй профиль пользователя и составь персональный карьерный roadmap.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ

Имя:
{name}

Целевая профессия:
{goal}

Резюме:
{resume}

Навыки:
{user_skills}

Проекты:
{user_projects}

Доступные вакансии:
{vacancy_data}


ЗАДАЧА

Определи:

1. Примерный текущий уровень пользователя.
2. Сильные стороны.
3. Недостающие навыки.
4. Что нужно изучить.
5. Практический проект.
6. Подходящие вакансии.
7. Следующий шаг.
8. Персональный roadmap.


ВАЖНО

Не придумывай навыки, которых нет в профиле.

Если информации недостаточно, укажи это.

Уровень навыков оценивай по шкале от 1 до 5.

Для вакансий рассчитай примерный процент соответствия.

Roadmap должен двигаться от текущего уровня пользователя к целевой профессии.


ФОРМАТ ОТВЕТА

Верни ТОЛЬКО валидный JSON.

Не используй Markdown.

Не добавляй текст до или после JSON.

Структура:

{{
    "target_role": "Backend Developer",

    "current_level": "Junior",

    "strengths": [
        "сильная сторона"
    ],

    "missing_skills": [
        {{
            "skill": "Python",
            "current_level": 3,
            "required_level": 5,
            "reason": "почему навык нужно улучшить"
        }}
    ],

    "learning": [
        {{
            "skill": "Python",
            "recommendation": "что изучить"
        }}
    ],

    "recommended_project": {{
        "name": "Название проекта",
        "description": "Описание проекта",
        "skills": [
            "Python",
            "FastAPI"
        ]
    }},

    "vacancies": [
        {{
            "id": 1,
            "title": "Junior Backend Developer",
            "company": "Tech Company",
            "match_percent": 75,
            "missing_skills": [
                "Git"
            ]
        }}
    ],

    "next_step": "Что пользователю сделать следующим",

    "roadmap": [
        {{
            "step": 1,
            "title": "Название этапа",
            "description": "Что нужно сделать"
        }},
        {{
            "step": 2,
            "title": "Следующий этап",
            "description": "Что нужно сделать"
        }}
    ]
}}
"""

    # =========================
    # ЗАПРОС К OPENAI
    # =========================

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    ai_text = response.output_text

    # =========================
    # ПРЕОБРАЗОВАНИЕ JSON
    # =========================

    try:
        result = json.loads(ai_text)

    except json.JSONDecodeError:

        return {
            "error": "AI вернул некорректный JSON",
            "raw_response": ai_text
        }

    # =========================
    # СОХРАНЯЕМ ROADMAP
    # =========================

    conn = get_db()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO roadmaps (user_id, target_role, result)
            VALUES (%s, %s, %s);
            """,
            (
                user_id,
                goal,
                Json(result)
            )
        )

    conn.commit()
    conn.close()

    # =========================
    # ВОЗВРАЩАЕМ РЕЗУЛЬТАТ
    # =========================

    return result


# =========================
# ПОЛУЧИТЬ ROADMAP
# =========================

@app.get("/roadmap/{user_id}")
def get_roadmap(user_id: int):

    conn = get_db()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id, target_role, result
            FROM roadmaps
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1;
            """,
            (user_id,)
        )

        roadmap = cur.fetchone()

    conn.close()

    if roadmap is None:
        return {
            "error": "Roadmap пока не создан"
        }

    return {
        "id": roadmap[0],
        "target_role": roadmap[1],
        "result": roadmap[2]
    }