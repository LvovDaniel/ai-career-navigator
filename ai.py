from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import psycopg
from psycopg.types.json import Json
from dotenv import load_dotenv
from openai import OpenAI

import os
import requests
import json


# =========================
# ENV
# =========================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="AI Career Navigator",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DATABASE
# =========================

def get_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "ai_navigator"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "admin123")
    )


# =========================
# MODELS
# =========================

class User(BaseModel):
    name: str
    email: str
    goal: str
    resume: str = ""


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
# ROOT
# =========================

@app.get("/")
def root():
    return {
        "message": "AI Career Navigator работает!"
    }


# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================
# USERS
# =========================

@app.post("/users")
def create_user(user: User):

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO users
                (name, email, goal, resume)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user.name,
                    user.email,
                    user.goal,
                    user.resume
                )
            )

            user_id = cur.fetchone()[0]

            conn.commit()

    return {
        "user_id": user_id
    }


# =========================
# GET PROFILE
# =========================

@app.get("/profile/{user_id}")
def get_profile(user_id: int):

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, name, email, goal, resume
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            user = cur.fetchone()

    if not user:
        return {
            "error": "Пользователь не найден"
        }

    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
        "goal": user[3],
        "resume": user[4]
    }


# =========================
# SAVE PROFILE
# =========================

@app.post("/profile")
def save_profile(profile: Profile):

    with get_db() as conn:
        with conn.cursor() as cur:

            # Проверяем существование пользователя
            cur.execute(
                """
                SELECT id
                FROM users
                WHERE id = %s
                """,
                (profile.user_id,)
            )

            user = cur.fetchone()

            if not user:
                return {
                    "error": "Пользователь не найден"
                }

            # Сохраняем опыт в resume.
            # Целевую профессию НЕ изменяем.
            cur.execute(
                """
                UPDATE users
                SET resume = %s
                WHERE id = %s
                """,
                (
                    profile.experience,
                    profile.user_id
                )
            )

            # Удаляем старые проекты пользователя,
            # чтобы они не дублировались.
            cur.execute(
                """
                DELETE FROM projects
                WHERE user_id = %s
                """,
                (profile.user_id,)
            )

            # Сохраняем новые проекты
            for project in profile.projects:

                project = project.strip()

                if not project:
                    continue

                cur.execute(
                    """
                    INSERT INTO projects
                    (user_id, name, description)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        profile.user_id,
                        project[:100],
                        project
                    )
                )

            conn.commit()

    return {
        "message": "Профиль и проекты сохранены"
    }


# =========================
# ADD SKILL
# =========================

@app.post("/skills")
def add_skill(skill: UserSkill):

    if skill.level < 1 or skill.level > 5:
        return {
            "error": "Уровень навыка должен быть от 1 до 5"
        }

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO skills (name)
                VALUES (%s)
                ON CONFLICT (name)
                DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (skill.skill,)
            )

            skill_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO user_skills
                (user_id, skill_id, level)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, skill_id)
                DO UPDATE SET level = EXCLUDED.level
                """,
                (
                    skill.user_id,
                    skill_id,
                    skill.level
                )
            )

            conn.commit()

    return {
        "message": "Навык сохранён",
        "skill": skill.skill,
        "level": skill.level
    }


# =========================
# GET SKILLS
# =========================

@app.get("/skills/{user_id}")
def get_skills(user_id: int):

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    skills.name,
                    user_skills.level
                FROM user_skills
                JOIN skills
                    ON skills.id = user_skills.skill_id
                WHERE user_skills.user_id = %s
                """,
                (user_id,)
            )

            rows = cur.fetchall()

    return [
        {
            "name": row[0],
            "level": row[1]
        }
        for row in rows
    ]


# =========================
# FULL PROFILE
# =========================

@app.get("/profile/full/{user_id}")
def get_full_profile(user_id: int):

    user = get_profile(user_id)

    if "error" in user:
        return user

    skills = get_skills(user_id)

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT name, description
                FROM projects
                WHERE user_id = %s
                """,
                (user_id,)
            )

            projects = [
                {
                    "name": row[0],
                    "description": row[1]
                }
                for row in cur.fetchall()
            ]

    return {
        "user": user,
        "skills": skills,
        "projects": projects
    }


# =========================
# REAL VACANCIES
# =========================

@app.get("/vacancies/real")
def get_real_vacancies(
    query: str = "Backend Developer"
):

    url = "https://api.hh.ru/vacancies"

    headers = {
        "HH-User-Agent": (
            "AI Career Navigator/1.0 "
            "(lvovdaniil902@gmail.com)"
        ),
        "User-Agent": "AI Career Navigator/1.0",
        "Accept": "application/json"
    }

    params = {
        "text": query,
        "per_page": 10,
        "page": 0,
        "area": 1
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=5
        )

        print(
            f"HH status: {response.status_code}"
        )

        if response.status_code == 200:

            data = response.json()

            vacancies = []

            for item in data.get("items", []):

                employer = item.get("employer") or {}
                area = item.get("area") or {}

                vacancies.append({
                    "id": item.get("id"),
                    "title": item.get("name"),
                    "company": employer.get(
                        "name",
                        "Не указана"
                    ),
                    "url": item.get(
                        "alternate_url"
                    ),
                    "salary": item.get(
                        "salary"
                    ),
                    "area": area.get(
                        "name",
                        "Не указано"
                    ),
                    "source": "hh.ru"
                })

            return {
                "query": query,
                "count": len(vacancies),
                "source": "hh.ru",
                "vacancies": vacancies
            }

        print(
            f"HH вернул ошибку: {response.status_code}"
        )

    except requests.Timeout:

        print(
            "HH: запрос превысил 5 секунд"
        )

    except requests.RequestException as e:

        print(
            f"HH RequestException: {e}"
        )

    except Exception as e:

        print(
            f"HH неизвестная ошибка: {e}"
        )


    # =========================
    # FALLBACK — ДЕМО-ВАКАНСИИ
    # =========================

    try:

        demo_vacancies = get_vacancies()

        return {
            "query": query,
            "count": len(demo_vacancies),
            "source": "demo",
            "message": (
                "Реальные вакансии временно "
                "недоступны. Используются "
                "демонстрационные."
            ),
            "vacancies": demo_vacancies
        }

    except Exception as e:

        return {
            "query": query,
            "count": 0,
            "source": "none",
            "error": "Не удалось получить вакансии",
            "details": str(e),
            "vacancies": []
        }


# =========================
# DEMO VACANCIES
# =========================

@app.get("/vacancies")
def get_vacancies():

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    title,
                    company,
                    description,
                    required_skills
                FROM vacancies
                """
            )

            rows = cur.fetchall()

    vacancies = []

    for row in rows:

        vacancies.append({
            "id": row[0],
            "title": row[1],
            "company": row[2],
            "description": row[3],
            "required_skills": row[4]
        })

    return vacancies


# =========================
# AI ANALYSIS
# =========================

@app.post("/analyze")
def analyze(user_id: int):

    # =========================
    # USER
    # =========================

    user = get_profile(user_id)

    if "error" in user:
        return user


    # =========================
    # SKILLS
    # =========================

    skills = get_skills(user_id)


    # =========================
    # PROJECTS
    # =========================

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT name, description
                FROM projects
                WHERE user_id = %s
                """,
                (user_id,)
            )

            project_rows = cur.fetchall()

    projects = [
        {
            "name": row[0],
            "description": row[1]
        }
        for row in project_rows
    ]


    # =========================
    # VACANCIES
    # =========================

    vacancies = get_vacancies()


    # =========================
    # AI PROMPT
    # =========================

    prompt = f"""
Ты — AI Career Navigator.

Проанализируй профиль пользователя
и составь персональный карьерный roadmap.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:

Целевая профессия:
{user.get("goal", "")}

Резюме:
{user.get("resume", "")}

Навыки:
{json.dumps(skills, ensure_ascii=False)}

Проекты:
{json.dumps(projects, ensure_ascii=False)}

Вакансии:
{json.dumps(vacancies, ensure_ascii=False)}


ВАЖНО

Навыки из раздела "Навыки" являются навыками,
которые пользователь указал как имеющиеся.

Не считай такой навык отсутствующим только потому,
что он не упомянут в резюме или проектах.

Используй указанное пользователем значение level
как текущий уровень навыка.

Например:

если в профиле есть:

{{"name": "Python", "level": 3}}

то Python является текущим навыком пользователя
с уровнем 3.

В этом случае Python нельзя помещать
в missing_skills как отсутствующий навык.

Можно указать его как навык, который нужно улучшить,
если требуемый уровень выше текущего.

Не придумывай навыки, которых нет в профиле.

Если информации недостаточно — укажи это.

Уровень навыков оценивай по шкале от 1 до 5.

Для вакансий рассчитай примерный процент соответствия.

Roadmap должен двигаться от текущего уровня
пользователя к целевой профессии.


ОТВЕТ ВЕРНИ ТОЛЬКО В JSON.

Структура:

{{
    "target_role": "...",

    "current_level": "...",

    "strengths": [
        {{
            "skill": "...",
            "level": 1
        }}
    ],

    "missing_skills": [
        {{
            "skill": "...",
            "current_level": 1,
            "required_level": 4
        }}
    ],

    "learning": [
        {{
            "skill": "...",
            "description": "...",
            "priority": "high"
        }}
    ],

    "recommended_project": {{
        "name": "...",
        "description": "...",
        "technologies": []
    }},

    "vacancies": [
        {{
            "title": "...",
            "company": "...",
            "match_percent": 0,
            "missing_skills": []
        }}
    ],

    "next_step": "...",

    "roadmap": [
        {{
            "step": 1,
            "title": "...",
            "description": "..."
        }}
    ]
}}
"""


    # =========================
    # OPENAI
    # =========================

    try:

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result_text = response.output_text

        result = json.loads(result_text)

    except Exception as e:

        return {
            "error": "Ошибка AI анализа",
            "details": str(e)
        }


    # =========================
    # SAVE ROADMAP
    # =========================

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO roadmaps
                (user_id, target_role, result)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    result.get("target_role"),
                    Json(result)
                )
            )

            conn.commit()


    return result


# =========================
# GET ROADMAP
# =========================

@app.get("/roadmap/{user_id}")
def get_roadmap(user_id: int):

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    target_role,
                    result
                FROM roadmaps
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,)
            )

            row = cur.fetchone()

    if not row:

        return {
            "error": "Roadmap пока не создан"
        }

    return {
        "id": row[0],
        "target_role": row[1],
        "result": row[2]
    }