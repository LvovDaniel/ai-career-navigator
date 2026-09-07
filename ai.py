from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    version="1.0.0"
)


# =========================
# CORS
# =========================

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://delightful-adaptation-production-fd1f.up.railway.app"
]

frontend_url = os.getenv("FRONTEND_URL")

if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    skills: list[str] = Field(default_factory=list)
    experience: str = ""
    projects: list[str] = Field(default_factory=list)


class UserSkill(BaseModel):
    user_id: int
    skill: str
    level: int = Field(default=3, ge=1, le=5)


# =========================
# ROOT
# =========================

@app.get("/")
def root():
    return {
        "message": "AI Career Navigator API is running"
    }


# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    try:
        conn = get_db()
        conn.close()

        return {
            "status": "ok",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "error",
            "database": str(e)
        }


# =========================
# USERS
# =========================

@app.post("/users")
def create_user(user: User):

    try:

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

        return {
            "user_id": user_id
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# GET PROFILE
# =========================

@app.get("/profile/{user_id}")
def get_profile(user_id: int):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        email,
                        goal,
                        resume
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "goal": row[3],
            "resume": row[4]
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# SAVE PROFILE
# =========================

@app.post("/profile")
def save_profile(profile: Profile):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # Сохраняем опыт в resume
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

                # Сохраняем проекты
                for project in profile.projects:

                    if not project.strip():
                        continue

                    cur.execute(
                        """
                        INSERT INTO projects
                        (user_id, name, description)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            profile.user_id,
                            project[:255],
                            project
                        )
                    )

        return {
            "status": "saved"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# ADD SKILL
# =========================

@app.post("/skills")
def add_skill(skill: UserSkill):

    if skill.level < 1 or skill.level > 5:

        raise HTTPException(
            status_code=400,
            detail="Skill level must be between 1 and 5"
        )

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # Создаем навык, если его еще нет
                cur.execute(
                    """
                    INSERT INTO skills (name)
                    VALUES (%s)
                    ON CONFLICT (name)
                    DO NOTHING
                    """,
                    (skill.skill,)
                )

                # Получаем ID навыка
                cur.execute(
                    """
                    SELECT id
                    FROM skills
                    WHERE name = %s
                    """,
                    (skill.skill,)
                )

                skill_row = cur.fetchone()

                if not skill_row:

                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create skill"
                    )

                skill_id = skill_row[0]

                # Связываем пользователя и навык
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

        return {
            "status": "saved"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# GET SKILLS
# =========================

@app.get("/skills/{user_id}")
def get_skills(user_id: int):

    try:

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
                "skill": row[0],
                "level": row[1]
            }
            for row in rows
        ]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# FULL PROFILE
# =========================

@app.get("/profile/full/{user_id}")
def get_full_profile(user_id: int):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # Пользователь
                cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        email,
                        goal,
                        resume
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                user = cur.fetchone()

                if not user:

                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                # Skills
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

                skills = cur.fetchall()

                # Projects
                cur.execute(
                    """
                    SELECT
                        name,
                        description
                    FROM projects
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                projects = cur.fetchall()

                # Courses
                cur.execute(
                    """
                    SELECT
                        name,
                        description
                    FROM courses
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                courses = cur.fetchall()

        return {

            "user": {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "goal": user[3],
                "resume": user[4]
            },

            "skills": [
                {
                    "skill": row[0],
                    "level": row[1]
                }
                for row in skills
            ],

            "projects": [
                {
                    "name": row[0],
                    "description": row[1]
                }
                for row in projects
            ],

            "courses": [
                {
                    "name": row[0],
                    "description": row[1]
                }
                for row in courses
            ]
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# DEMO VACANCIES
# =========================

def get_vacancies():

    return [

        {
            "id": 1,
            "title": "Junior Backend Developer",
            "company": "Tech Company",
            "description": "Разработка backend-приложений",
            "required_skills": [
                "Python",
                "SQL",
                "Git",
                "FastAPI"
            ]
        },

        {
            "id": 2,
            "title": "Python Developer",
            "company": "IT Company",
            "description": "Разработка сервисов на Python",
            "required_skills": [
                "Python",
                "PostgreSQL",
                "Docker",
                "Git"
            ]
        },

        {
            "id": 3,
            "title": "Backend Developer",
            "company": "AI Company",
            "description": "Разработка API и backend-сервисов",
            "required_skills": [
                "Python",
                "FastAPI",
                "PostgreSQL",
                "Docker",
                "SQL"
            ]
        }

    ]


# =========================
# REAL HH VACANCIES
# =========================

@app.get("/vacancies/real")
def get_real_vacancies(
    query: str = "Backend Developer"
):

    url = "https://api.hh.ru/vacancies"

    headers = {
        "User-Agent": "AI-Career-Navigator/1.0"
    }

    params = {
        "text": query,
        "area": 113,
        "per_page": 10
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        vacancies = []

        for item in data.get("items", []):

            employer = item.get("employer") or {}
            snippet = item.get("snippet") or {}
            area = item.get("area") or {}

            vacancies.append(
                {
                    "id": item.get("id"),
                    "title": item.get("name"),
                    "company": employer.get("name"),
                    "description": (
                        snippet.get("requirement")
                        or ""
                    ),
                    "url": item.get("alternate_url"),
                    "area": area.get("name"),
                    "salary": item.get("salary")
                }
            )

        return {
            "source": "hh.ru",
            "query": query,
            "count": len(vacancies),
            "vacancies": vacancies
        }

    except Exception as e:

        print(
            "HH API ERROR:",
            e
        )

        demo = get_vacancies()

        return {
            "source": "demo",
            "query": query,
            "count": len(demo),
            "vacancies": demo
        }


# =========================
# VACANCIES
# =========================

@app.get("/vacancies")
def vacancies():

    return get_vacancies()


# =========================
# ANALYZE
# =========================

@app.post("/analyze")
def analyze(user_id: int):

    try:

        # =====================================
        # GET USER
        # =====================================

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        email,
                        goal,
                        resume
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                user = cur.fetchone()

                if not user:

                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                # =====================================
                # GET SKILLS
                # =====================================

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

                skill_rows = cur.fetchall()

                user_skills = [
                    {
                        "skill": row[0],
                        "level": row[1]
                    }
                    for row in skill_rows
                ]

                # =====================================
                # GET PROJECTS
                # =====================================

                cur.execute(
                    """
                    SELECT
                        name,
                        description
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

        # =====================================
        # GET VACANCIES
        # =====================================

        hh_data = get_real_vacancies(
            query=user[3]
        )

        vacancies = hh_data.get(
            "vacancies",
            []
        )

        if not vacancies:

            vacancies = get_vacancies()

            hh_data["source"] = "demo"

        # =====================================
        # EXACT VACANCY MATCH CALCULATION
        # =====================================

        user_skills_lower = {
            skill["skill"].strip().lower()
            for skill in user_skills
        }

        for vacancy in vacancies:

            required_skills = vacancy.get(
                "required_skills",
                []
            )

            # Если есть точные требования,
            # считаем Match непосредственно Backend.
            if required_skills:

                matched = []
                missing = []

                for required_skill in required_skills:

                    required_lower = (
                        required_skill
                        .strip()
                        .lower()
                    )

                    if required_lower in user_skills_lower:

                        matched.append(
                            required_skill
                        )

                    else:

                        missing.append(
                            required_skill
                        )

                match_percent = round(
                    len(matched)
                    / len(required_skills)
                    * 100
                )

                vacancy["match_percent"] = (
                    match_percent
                )

                vacancy["matched_skills"] = (
                    matched
                )

                vacancy["missing_skills"] = (
                    missing
                )

            else:

                # Для HH-вакансий requirements
                # определит AI.
                vacancy["match_percent"] = 0
                vacancy["matched_skills"] = []
                vacancy["missing_skills"] = []


        # =====================================
        # VACANCIES TEXT FOR AI
        # =====================================

        vacancies_text = "\n".join(
            [
                (
                    f"Вакансия {vacancy.get('id', '')}\n"
                    f"Название: {vacancy.get('title', '')}\n"
                    f"Компания: {vacancy.get('company', '')}\n"
                    f"Описание: {vacancy.get('description', '')}\n"
                    f"Регион: {vacancy.get('area', '')}\n"
                    f"Зарплата: {vacancy.get('salary', '')}\n"
                    f"Требуемые навыки: "
                    f"{vacancy.get('required_skills', [])}\n"
                    f"Ссылка: {vacancy.get('url', '')}"
                )
                for vacancy in vacancies
            ]
        )

        # =====================================
        # USER SKILLS TEXT
        # =====================================

        skills_text = "\n".join(
            [
                f"{skill['skill']}: уровень {skill['level']}/5"
                for skill in user_skills
            ]
        )

        # =====================================
        # PROJECTS TEXT
        # =====================================

        projects_text = "\n".join(
            [
                (
                    f"{project['name']}: "
                    f"{project['description']}"
                )
                for project in projects
            ]
        )

        if not projects_text:

            projects_text = "Нет проектов"

        # =====================================
        # AI PROMPT
        # =====================================

        prompt = f"""
Ты — карьерный AI-ассистент.

Проанализируй профиль пользователя и построй
реалистичный карьерный путь.

Целевая профессия:
{user[3]}

Резюме / опыт:
{user[4] or "Нет данных"}

Текущие навыки:
{skills_text or "Нет указанных навыков"}

Проекты:
{projects_text}

Вакансии:
{vacancies_text}

ВАЖНЫЕ ПРАВИЛА:

1. Не считай отсутствующий навык имеющимся.

2. Если пользователь не указал навык,
считай его текущий уровень равным 0.

3. Не добавляй пользователю навыки,
которые он не указывал.

4. Для missing_skills указывай только навыки,
которых действительно не хватает.

5. Для demo-вакансий используй переданные
Backend значения:

- match_percent
- matched_skills
- missing_skills

Они являются источником истины.

Не изменяй эти значения.

Для demo-вакансий match_percent рассчитывается Backend
по формуле:

количество совпавших навыков /
количество требуемых навыков × 100.

6. Для реальных HH-вакансий, если required_skills
отсутствует, определи необходимые навыки
по описанию вакансии.

Для каждой такой вакансии рассчитай приблизительный
match_percent на основе совпадения навыков пользователя
с требованиями вакансии.

7. Обязательно рассчитай career_match_percent.

Это процент соответствия текущего профиля пользователя
требованиям целевой профессии.

Учитывай:

- текущие навыки пользователя;
- уровни навыков от 1 до 5;
- опыт;
- проекты;
- необходимые навыки целевой профессии;
- недостающие навыки.

career_match_percent должен быть целым числом
от 0 до 100.

0% означает практически полное отсутствие
соответствующих навыков.

100% означает практически полное соответствие
требованиям профессии.

Не ставь 0%, если у пользователя уже есть
релевантные навыки.

Например, если пользователь знает Python,
C++ и Git, но ему не хватает SQL, FastAPI,
PostgreSQL и Docker, career_match_percent
должен быть заметно выше 0%.

Верни ТОЛЬКО корректный JSON следующей структуры:

{{
    "target_role": "string",

    "current_level": "string",

    "career_match_percent": 0,

    "strengths": [
        {{
            "skill": "string",
            "level": 1
        }}
    ],

    "missing_skills": [
        {{
            "skill": "string",
            "current_level": 0,
            "required_level": 3,
            "reason": "string"
        }}
    ],

    "learning": [
        {{
            "skill": "string",
            "priority": "high",
            "description": "string"
        }}
    ],

    "recommended_project": "string",

    "vacancies": [
        {{
            "title": "string",
            "company": "string",
            "match_percent": 0,
            "matched_skills": [],
            "missing_skills": [],
            "url": ""
        }}
    ],

    "next_step": "string",

    "roadmap": [
        {{
            "step": 1,
            "title": "string",
            "description": "string"
        }}
    ]
}}

Отсортируй вакансии по match_percent
от большего к меньшему.
"""

        # =====================================
        # OPENAI
        # =====================================

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        ai_text = response.output_text.strip()

        # =====================================
        # REMOVE MARKDOWN IF NECESSARY
        # =====================================

        if ai_text.startswith("```"):

            ai_text = ai_text.replace(
                "```json",
                ""
            )

            ai_text = ai_text.replace(
                "```",
                ""
            )

            ai_text = ai_text.strip()

        # =====================================
        # PARSE JSON
        # =====================================

        try:

            result = json.loads(
                ai_text
            )

        except json.JSONDecodeError:

            raise HTTPException(
                status_code=500,
                detail=(
                    "AI returned invalid JSON: "
                    + ai_text
                )
            )

        # =====================================
        # CAREER MATCH
        # =====================================

        career_match = result.get(
            "career_match_percent"
        )

        if isinstance(
            career_match,
            (int, float)
        ):

            result["career_match_percent"] = round(
                max(
                    0,
                    min(
                        100,
                        career_match
                    )
                )
            )

        else:

            # =================================
            # FALLBACK CALCULATION
            # =================================

            strengths = result.get(
                "strengths",
                []
            )

            missing_skills = result.get(
                "missing_skills",
                []
            )

            total_skills = (
                len(strengths)
                + len(missing_skills)
            )

            if total_skills > 0:

                fallback_match = round(
                    len(strengths)
                    / total_skills
                    * 100
                )

            else:

                fallback_match = 0

            result["career_match_percent"] = (
                fallback_match
            )

        # =====================================
        # FORCE CORRECT VACANCY DATA
        # =====================================

        # Для demo-вакансий используем точные
        # значения, рассчитанные Backend.
        #
        # Это гарантирует, что AI не сможет
        # заменить правильный процент на 0.

        if hh_data.get("source") == "demo":

            result["vacancies"] = [
                {
                    "title": vacancy.get(
                        "title",
                        ""
                    ),

                    "company": vacancy.get(
                        "company",
                        ""
                    ),

                    "match_percent": vacancy.get(
                        "match_percent",
                        0
                    ),

                    "matched_skills": vacancy.get(
                        "matched_skills",
                        []
                    ),

                    "missing_skills": vacancy.get(
                        "missing_skills",
                        []
                    ),

                    "url": vacancy.get(
                        "url",
                        ""
                    )
                }

                for vacancy in vacancies
            ]

        else:

            # Для реальных HH-вакансий
            # используем результат AI.

            ai_vacancies = result.get(
                "vacancies",
                []
            )

            for ai_vacancy in ai_vacancies:

                match_percent = ai_vacancy.get(
                    "match_percent",
                    0
                )

                try:
                    match_percent = float(
                        match_percent
                    )
                except (TypeError, ValueError):
                    match_percent = 0

                ai_vacancy["match_percent"] = round(
                    max(
                        0,
                        min(
                            100,
                            match_percent
                        )
                    )
                )

                if not isinstance(
                    ai_vacancy.get(
                        "matched_skills"
                    ),
                    list
                ):
                    ai_vacancy[
                        "matched_skills"
                    ] = []

                if not isinstance(
                    ai_vacancy.get(
                        "missing_skills"
                    ),
                    list
                ):
                    ai_vacancy[
                        "missing_skills"
                    ] = []

            result["vacancies"] = ai_vacancies

        # =====================================
        # SORT VACANCIES
        # =====================================

        result["vacancies"] = sorted(
            result.get(
                "vacancies",
                []
            ),
            key=lambda x: x.get(
                "match_percent",
                0
            ),
            reverse=True
        )

        # =====================================
        # SAVE ROADMAP
        # =====================================

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
                        result.get(
                            "target_role",
                            user[3]
                        ),
                        Json(result)
                    )
                )

        return result

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ANALYZE ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# GET ROADMAP
# =========================

@app.get("/roadmap/{user_id}")
def get_roadmap(user_id: int):

    try:

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

                    raise HTTPException(
                        status_code=404,
                        detail="Roadmap not found"
                    )

        return {
            "id": row[0],
            "target_role": row[1],
            "result": row[2]
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )