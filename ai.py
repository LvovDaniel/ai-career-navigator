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


# =========================================================
# ENV
# =========================================================

load_dotenv()


# =========================================================
# OPENAI
# =========================================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="AI Career Navigator",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://frontend-production-75c1.up.railway.app",
]

frontend_url = os.getenv("FRONTEND_URL")

if frontend_url:
    allowed_origins.append(frontend_url)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    return psycopg.connect(
        host=os.getenv(
            "DB_HOST",
            "localhost"
        ),
        port=int(
            os.getenv(
                "DB_PORT",
                5432
            )
        ),
        dbname=os.getenv(
            "DB_NAME",
            "ai_navigator"
        ),
        user=os.getenv(
            "DB_USER",
            "admin"
        ),
        password=os.getenv(
            "DB_PASSWORD",
            "admin123"
        )
    )


# =========================================================
# AVAILABLE PROFESSIONS
# =========================================================

AVAILABLE_PROFESSIONS = [
    "Backend Developer",
    "Frontend Developer",
    "Fullstack Developer",
    "Python Developer",
    "C++ Developer",
    "Java Developer",
    "JavaScript Developer",
    "TypeScript Developer",
    "Data Analyst",
    "Data Scientist",
    "System Analyst",
    "Business Analyst",
    "DevOps Engineer",
    "QA Engineer",
    "Software Engineer",
    "ML Engineer",
    "Machine Learning Engineer",
]


# =========================================================
# NORMALIZE PROFESSION
# =========================================================

def normalize_profession(value: str) -> str:
    return " ".join(
        (value or "").strip().lower().split()
    )


# =========================================================
# CHECK PROFESSION
# =========================================================

def is_valid_profession(goal: str) -> bool:

    normalized_goal = normalize_profession(
        goal
    )

    if not normalized_goal:
        return False

    return normalized_goal in {
        normalize_profession(profession)
        for profession in AVAILABLE_PROFESSIONS
    }


# =========================================================
# MODELS
# =========================================================

class User(BaseModel):
    name: str
    email: str
    goal: str
    resume: str = ""


class Profile(BaseModel):
    user_id: int
    goal: str = ""
    skills: list[str] = Field(
        default_factory=list
    )
    projects: list[str] = Field(
        default_factory=list
    )
    experience: str = ""


class UserSkill(BaseModel):
    user_id: int
    skill: str
    level: int = Field(
        default=3,
        ge=1,
        le=5
    )


class SkillsUpdate(BaseModel):
    user_id: int
    skills: list[UserSkill] = Field(
        default_factory=list
    )


# =========================================================
# INPUT VALIDATION
# =========================================================

def validate_profile_input(
    goal: str,
    skills: list[dict],
    experience: str
):
    goal = (goal or "").strip()
    experience = (experience or "").strip()

    # -----------------------------------------------------
    # ПРОФЕССИЯ
    # -----------------------------------------------------

    if not is_valid_profession(goal):
        return False

    # -----------------------------------------------------
    # НАВЫКИ И ОПЫТ
    # -----------------------------------------------------

    fields = [
        experience,
        *[
            str(
                skill.get(
                    "skill",
                    ""
                )
            ).strip()
            for skill in skills
        ]
    ]

    for value in fields:

        if not value:
            continue

        if not any(
            char.isalpha()
            for char in value
        ):
            return False

        cleaned = "".join(
            char.lower()
            for char in value
            if char.isalnum()
        )

        # -------------------------------------------------
        # ОДИН СИМВОЛ 6 РАЗ ПОДРЯД
        # -------------------------------------------------

        if len(cleaned) >= 6:

            for char in set(cleaned):

                if char * 6 in cleaned:
                    return False

    return True


# =========================================================
# HOME
# =========================================================

@app.get("/")
def root():

    return {
        "message": "AI Career Navigator API",
        "status": "running"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================================================
# PROFESSIONS
# =========================================================

@app.get("/professions")
def get_professions():

    return {
        "count": len(
            AVAILABLE_PROFESSIONS
        ),
        "professions": AVAILABLE_PROFESSIONS
    }


# =========================================================
# CREATE USER
# =========================================================

@app.post("/users")
def create_user(user: User):

    if not is_valid_profession(
        user.goal
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Ошибка. Проверьте введённые "
                "данные и попробуйте ещё раз."
            )
        )

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

        print(
            "CREATE USER ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось создать пользователя."
        )


# =========================================================
# GET PROFILE
# =========================================================

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

                user = cur.fetchone()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="Пользователь не найден"
            )

        return {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "goal": user[3],
            "resume": user[4]
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "GET PROFILE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить профиль."
        )


# =========================================================
# SAVE PROFILE
# =========================================================

@app.post("/profile")
def save_profile(profile: Profile):

    if not is_valid_profession(
        profile.goal
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Ошибка. Проверьте введённые "
                "данные и попробуйте ещё раз."
            )
        )

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # -------------------------------------------------
                # Проверяем пользователя
                # -------------------------------------------------

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

                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

                # -------------------------------------------------
                # Обновляем профиль
                # -------------------------------------------------

                cur.execute(
                    """
                    UPDATE users
                    SET
                        goal = %s,
                        resume = %s
                    WHERE id = %s
                    """,
                    (
                        profile.goal.strip(),
                        profile.experience.strip(),
                        profile.user_id
                    )
                )

                # -------------------------------------------------
                # Сохраняем проекты
                # -------------------------------------------------

                for project in profile.projects:

                    project = str(
                        project
                    ).strip()

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

        return {
            "status": "ok",
            "user_id": profile.user_id
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "SAVE PROFILE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить профиль."
        )


# =========================================================
# ADD SKILL
# =========================================================

@app.post("/skills")
def add_skill(skill: UserSkill):

    try:

        skill_name = (
            skill.skill or ""
        ).strip()

        if not skill_name:

            raise HTTPException(
                status_code=400,
                detail="Название навыка не может быть пустым."
            )

        with get_db() as conn:

            with conn.cursor() as cur:

                # -------------------------------------------------
                # Проверяем пользователя
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = %s
                    """,
                    (skill.user_id,)
                )

                if cur.fetchone() is None:

                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

                # -------------------------------------------------
                # Ищем навык
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT id
                    FROM skills
                    WHERE LOWER(name) = LOWER(%s)
                    LIMIT 1
                    """,
                    (skill_name,)
                )

                row = cur.fetchone()

                if row:

                    skill_id = row[0]

                else:

                    cur.execute(
                        """
                        INSERT INTO skills
                        (name)
                        VALUES (%s)
                        RETURNING id
                        """,
                        (skill_name,)
                    )

                    skill_id = cur.fetchone()[0]

                # -------------------------------------------------
                # Проверяем существующую связь
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT id
                    FROM user_skills
                    WHERE user_id = %s
                      AND skill_id = %s
                    LIMIT 1
                    """,
                    (
                        skill.user_id,
                        skill_id
                    )
                )

                existing = cur.fetchone()

                if existing:

                    # ---------------------------------------------
                    # Обновляем уровень
                    # ---------------------------------------------

                    cur.execute(
                        """
                        UPDATE user_skills
                        SET level = %s
                        WHERE id = %s
                        """,
                        (
                            skill.level,
                            existing[0]
                        )
                    )

                else:

                    # ---------------------------------------------
                    # Создаём связь
                    # ---------------------------------------------

                    cur.execute(
                        """
                        INSERT INTO user_skills
                        (
                            user_id,
                            skill_id,
                            level
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            skill.user_id,
                            skill_id,
                            skill.level
                        )
                    )

        return {
            "status": "ok",
            "skill": skill_name,
            "level": skill.level
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ADD SKILL ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить навык."
        )


# =========================================================
# REPLACE USER SKILLS
# =========================================================

@app.put("/skills/{user_id}")
def replace_skills(
    user_id: int,
    payload: SkillsUpdate
):

    # -----------------------------------------------------
    # Проверяем ID
    # -----------------------------------------------------

    if payload.user_id != user_id:

        raise HTTPException(
            status_code=400,
            detail="user_id не совпадает."
        )

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # -------------------------------------------------
                # Проверяем пользователя
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                if cur.fetchone() is None:

                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден."
                    )

                # -------------------------------------------------
                # Удаляем абсолютно все старые навыки
                # -------------------------------------------------

                cur.execute(
                    """
                    DELETE FROM user_skills
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                saved_skills = []
                seen_skills = set()

                # -------------------------------------------------
                # Сохраняем текущие навыки
                # -------------------------------------------------

                for item in payload.skills:

                    skill_name = (
                        item.skill or ""
                    ).strip()

                    if not skill_name:
                        continue

                    normalized_name = (
                        skill_name.lower()
                    )

                    # -------------------------------------------------
                    # Защита от дубликатов
                    # -------------------------------------------------

                    if normalized_name in seen_skills:
                        continue

                    seen_skills.add(
                        normalized_name
                    )

                    # -------------------------------------------------
                    # Ищем навык
                    # -------------------------------------------------

                    cur.execute(
                        """
                        SELECT id
                        FROM skills
                        WHERE LOWER(name) = LOWER(%s)
                        LIMIT 1
                        """,
                        (skill_name,)
                    )

                    skill_row = cur.fetchone()

                    # -------------------------------------------------
                    # Если навыка нет — создаём
                    # -------------------------------------------------

                    if skill_row is None:

                        cur.execute(
                            """
                            INSERT INTO skills
                            (name)
                            VALUES (%s)
                            RETURNING id
                            """,
                            (skill_name,)
                        )

                        skill_id = (
                            cur.fetchone()[0]
                        )

                    else:

                        skill_id = skill_row[0]

                    # -------------------------------------------------
                    # Добавляем связь
                    # -------------------------------------------------

                    cur.execute(
                        """
                        INSERT INTO user_skills
                        (
                            user_id,
                            skill_id,
                            level
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            user_id,
                            skill_id,
                            item.level
                        )
                    )

                    saved_skills.append(
                        {
                            "skill": skill_name,
                            "level": item.level
                        }
                    )

        return {
            "status": "ok",
            "user_id": user_id,
            "skills": saved_skills,
            "count": len(saved_skills)
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "REPLACE SKILLS ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось синхронизировать навыки."
        )


# =========================================================
# GET USER SKILLS
# =========================================================

@app.get("/skills/{user_id}")
def get_skills(user_id: int):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        s.name,
                        us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    ORDER BY s.name
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

        print(
            "GET SKILLS ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить навыки."
        )


# =========================================================
# FULL PROFILE
# =========================================================

@app.get("/profile/full/{user_id}")
def get_full_profile(user_id: int):

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

                # -------------------------------------------------
                # USER
                # -------------------------------------------------

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
                        detail="Пользователь не найден"
                    )

                # -------------------------------------------------
                # SKILLS
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT
                        s.name,
                        us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    ORDER BY s.name
                    """,
                    (user_id,)
                )

                skill_rows = cur.fetchall()

                # -------------------------------------------------
                # PROJECTS
                # -------------------------------------------------

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
                for row in skill_rows
            ],
            "projects": [
                {
                    "name": row[0],
                    "description": row[1]
                }
                for row in project_rows
            ]
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "FULL PROFILE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить полный профиль."
        )


# =========================================================
# DEMO VACANCIES
# =========================================================

def get_vacancies():

    return [
        {
            "id": "demo-1",
            "title": "Junior Backend Developer",
            "company": "Demo Tech",
            "description": (
                "Python, FastAPI, PostgreSQL, "
                "Git, Docker"
            ),
            "required_skills": [
                "Python",
                "FastAPI",
                "PostgreSQL",
                "Git",
                "Docker"
            ],
            "url": "",
            "area": "Екатеринбург",
            "salary": None
        },
        {
            "id": "demo-2",
            "title": "Junior Python Developer",
            "company": "Demo Software",
            "description": (
                "Python, SQL, Git, REST API"
            ),
            "required_skills": [
                "Python",
                "SQL",
                "Git",
                "REST API"
            ],
            "url": "",
            "area": "Екатеринбург",
            "salary": None
        },
        {
            "id": "demo-3",
            "title": "Backend Developer",
            "company": "AI Solutions",
            "description": (
                "Python, FastAPI, PostgreSQL, "
                "Docker, REST API"
            ),
            "required_skills": [
                "Python",
                "FastAPI",
                "PostgreSQL",
                "Docker",
                "REST API"
            ],
            "url": "",
            "area": "Удалённо",
            "salary": None
        }
    ]


# =========================================================
# REAL HH VACANCIES
# =========================================================

@app.get("/vacancies/real")
def get_real_vacancies(
    query: str = "Backend Developer"
):

    url = "https://api.hh.ru/vacancies"

    headers = {
        "User-Agent":
            "AI-Career-Navigator/1.0"
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

        for item in data.get(
            "items",
            []
        ):

            employer = (
                item.get("employer")
                or {}
            )

            snippet = (
                item.get("snippet")
                or {}
            )

            area = (
                item.get("area")
                or {}
            )

            vacancies.append(
                {
                    "id": item.get("id"),
                    "title": item.get("name"),
                    "company":
                        employer.get("name"),
                    "description":
                        snippet.get(
                            "requirement"
                        ) or "",
                    "url":
                        item.get(
                            "alternate_url"
                        ),
                    "area":
                        area.get("name"),
                    "salary":
                        item.get("salary")
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
            repr(e)
        )

        demo = get_vacancies()

        return {
            "source": "demo",
            "query": query,
            "count": len(demo),
            "vacancies": demo
        }


# =========================================================
# VACANCIES
# =========================================================

@app.get("/vacancies")
def vacancies():

    return get_vacancies()


# =========================================================
# AI ANALYSIS
# =========================================================

@app.post("/analyze")
def analyze(user_id: int):

    try:

        # =================================================
        # GET USER
        # =================================================

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
                detail="Пользователь не найден"
            )

        goal = (
            user[3] or ""
        ).strip()

        experience = (
            user[4] or ""
        ).strip()

        # =================================================
        # ПРОФЕССИЯ
        # =================================================

        if not is_valid_profession(goal):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Ошибка. Проверьте введённые "
                    "данные и попробуйте ещё раз."
                )
            )

        # =================================================
        # GET SKILLS
        # =================================================

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        s.name,
                        us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    ORDER BY s.name
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

        # =================================================
        # VALIDATE
        # =================================================

        if not validate_profile_input(
            goal=goal,
            skills=user_skills,
            experience=experience
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Ошибка. Проверьте введённые "
                    "данные и попробуйте ещё раз."
                )
            )

        # =================================================
        # VACANCIES
        # =================================================

        hh_data = get_real_vacancies(
            query=goal
        )

        vacancies_data = (
            hh_data.get(
                "vacancies",
                []
            )
        )

        if not vacancies_data:

            vacancies_data = get_vacancies()

            hh_data["source"] = "demo"

        # =================================================
        # VACANCIES TEXT
        # =================================================

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
                for vacancy in vacancies_data
            ]
        )

        # =================================================
        # SKILLS TEXT
        # =================================================

        skills_text = "\n".join(
            [
                (
                    f"- {skill['skill']}: "
                    f"уровень {skill['level']}/5"
                )
                for skill in user_skills
            ]
        )

        if not skills_text:

            skills_text = (
                "Пользователь пока не указал навыки."
            )

        if not experience:

            experience = (
                "Пользователь пока не указал опыт."
            )

        # =================================================
        # AI PROMPT
        # =================================================

        prompt = f"""
Ты — AI Career Navigator.

Твоя задача — провести карьерный анализ
пользователя и построить персональный
карьерный маршрут.

ЦЕЛЕВАЯ ПРОФЕССИЯ:
{goal}

ТЕКУЩИЕ НАВЫКИ ПОЛЬЗОВАТЕЛЯ:
{skills_text}

ОПЫТ:
{experience}

ВАКАНСИИ:
{vacancies_text}

Проанализируй:

1. Текущий уровень пользователя.
2. Его сильные стороны.
3. Недостающие навыки.
4. Что нужно изучить в первую очередь.
5. Практический проект.
6. Подходящие вакансии.
7. Карьерный маршрут.
8. Следующий конкретный шаг.
9. Другие подходящие карьерные направления.

ВАЖНЫЕ ПРАВИЛА:

- Никогда не придумывай текущие навыки пользователя.
- Текущими навыками считаются ТОЛЬКО навыки
  из блока "ТЕКУЩИЕ НАВЫКИ ПОЛЬЗОВАТЕЛЯ".
- Не считай требования вакансий текущими навыками.
- Не считай навыки из названия профессии текущими навыками.
- Используй переданные уровни навыков.
- Если навыков нет, считай пользователя начинающим.
- Если опыта нет, не придумывай его.
- Отсутствие навыка не является ошибкой.
- Недостающие навыки должны быть только теми,
  которых нет среди текущих навыков пользователя
  или уровень которых недостаточен.
- Сильные стороны должны основываться только
  на текущих навыках пользователя.

Для вакансий оцени соответствие примерно
по формуле:

matched skills / required skills * 100

Если точный список требований отсутствует,
оцени его по описанию вакансии.

Отсортируй вакансии по match_percent
от большего к меньшему.

Верни ТОЛЬКО JSON.

Формат:

{{
  "target_role": "Backend Developer",

  "current_level":
    "Начальный уровень (Junior)",

  "strengths": [
    "Python: уровень 3/5",
    "C++: уровень 3/5"
  ],

  "missing_skills": [
    {{
      "skill": "FastAPI",
      "current_level": 0,
      "required_level": 3,
      "reason":
        "Навык требуется для backend-разработки."
    }}
  ],

  "learning": [
    "Изучить FastAPI",
    "Изучить PostgreSQL",
    "Изучить Docker"
  ],

  "recommended_project": {{
    "name": "Название проекта",
    "description":
      "Описание проекта",
    "technologies": [
      "Python",
      "FastAPI",
      "PostgreSQL"
    ]
  }},

  "vacancies": [
    {{
      "title":
        "Junior Backend Developer",
      "company":
        "Company",
      "match_percent": 65,
      "matched_skills": [
        "Python"
      ],
      "missing_skills": [
        "FastAPI"
      ],
      "url": "https://..."
    }}
  ],

  "next_step":
    "Начать изучение FastAPI.",

  "roadmap": [
    {{
      "step": 1,
      "title": "Изучить FastAPI",
      "description":
        "Изучить маршруты, запросы и ответы."
    }},
    {{
      "step": 2,
      "title": "Изучить PostgreSQL",
      "description":
        "Научиться работать с базой данных."
    }},
    {{
      "step": 3,
      "title": "Создать проект",
      "description":
        "Сделать полноценный backend-проект."
    }}
  ],

  "career_match_percent": 55,

  "career_paths": [
    {{
      "title": "Backend Developer",
      "match_percent": 70,
      "why":
        "Направление соответствует текущим навыкам.",
      "description":
        "Разработка серверной части приложений.",
      "required_skills": [
        "Python",
        "FastAPI",
        "SQL"
      ],
      "missing_skills": [
        "FastAPI",
        "Docker"
      ],
      "first_step":
        "Изучить FastAPI.",
      "recommended_project":
        "Создать REST API."
    }},
    {{
      "title": "Python Developer",
      "match_percent": 65,
      "why":
        "Текущие навыки Python хорошо подходят.",
      "description":
        "Разработка приложений на Python.",
      "required_skills": [
        "Python",
        "Git"
      ],
      "missing_skills": [],
      "first_step":
        "Создать полноценный Python-проект.",
      "recommended_project":
        "Создать приложение на Python."
    }},
    {{
      "title": "DevOps Engineer",
      "match_percent": 40,
      "why":
        "Есть база программирования, но нужно изучить инфраструктуру.",
      "description":
        "Автоматизация и инфраструктура.",
      "required_skills": [
        "Linux",
        "Docker",
        "Git"
      ],
      "missing_skills": [
        "Linux",
        "Docker"
      ],
      "first_step":
        "Начать изучение Linux и Docker.",
      "recommended_project":
        "Развернуть приложение в Docker."
    }}
  ]
}}

Не добавляй markdown.
Не добавляй пояснения до или после JSON.
"""

        # =================================================
        # OPENAI
        # =================================================

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        raw_result = (
            response.output_text or ""
        ).strip()

        if not raw_result:

            raise HTTPException(
                status_code=500,
                detail="AI не вернул результат."
            )

        # =================================================
        # CLEAN JSON
        # =================================================

        if raw_result.startswith(
            "```json"
        ):

            raw_result = raw_result[
                len("```json"):
            ].strip()

        elif raw_result.startswith(
            "```"
        ):

            raw_result = raw_result[
                len("```"):
            ].strip()

        if raw_result.endswith(
            "```"
        ):

            raw_result = raw_result[
                :-3
            ].strip()

        # =================================================
        # PARSE JSON
        # =================================================

        try:

            result = json.loads(
                raw_result
            )

        except json.JSONDecodeError as e:

            print(
                "AI JSON ERROR:",
                repr(e)
            )

            print(
                "RAW AI RESULT:",
                raw_result
            )

            raise HTTPException(
                status_code=500,
                detail="AI вернул некорректный результат."
            )

        # =================================================
        # CHECK RESULT
        # =================================================

        if not isinstance(
            result,
            dict
        ):

            raise HTTPException(
                status_code=500,
                detail="AI вернул некорректную структуру."
            )

        # =================================================
        # NORMALIZE ARRAYS
        # =================================================

        array_fields = [
            "strengths",
            "missing_skills",
            "learning",
            "vacancies",
            "roadmap",
            "career_paths"
        ]

        for field in array_fields:

            if not isinstance(
                result.get(field),
                list
            ):

                result[field] = []

        # =================================================
        # PROTECT USER SKILLS
        # =================================================
        #
        # Сильные стороны берём напрямую
        # из user_skills.
        #
        # AI не может добавить сюда навыки,
        # которых нет у пользователя.
        # =================================================

        result["strengths"] = [
            f"{item['skill']}: уровень {item['level']}/5"
            for item in user_skills
        ]

        # =================================================
        # ACTUAL USER SKILLS
        # =================================================

        actual_skills = {
            str(
                item.get(
                    "skill",
                    ""
                )
            ).strip().lower():
            item
            for item in user_skills
            if str(
                item.get(
                    "skill",
                    ""
                )
            ).strip()
        }

        # =================================================
        # FILTER MISSING SKILLS
        # =================================================

        filtered_missing = []

        for item in result.get(
            "missing_skills",
            []
        ):

            if not isinstance(
                item,
                dict
            ):
                continue

            skill_name = str(
                item.get(
                    "skill",
                    ""
                )
            ).strip()

            if not skill_name:
                continue

            actual = actual_skills.get(
                skill_name.lower()
            )

            # -------------------------------------------------
            # Навык уже есть у пользователя
            # -------------------------------------------------

            if actual is not None:

                current_level = int(
                    actual.get(
                        "level",
                        0
                    ) or 0
                )

                try:

                    required_level = int(
                        item.get(
                            "required_level",
                            5
                        ) or 5
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    required_level = 5

                # -------------------------------------------------
                # Навык уже достаточно развит
                # -------------------------------------------------

                if current_level >= required_level:
                    continue

                item["current_level"] = (
                    current_level
                )

            else:

                # -------------------------------------------------
                # Навык отсутствует
                # -------------------------------------------------

                item["current_level"] = 0

            filtered_missing.append(
                item
            )

        result["missing_skills"] = (
            filtered_missing
        )

        # =================================================
        # CAREER MATCH
        # =================================================

        career_match = result.get(
            "career_match_percent"
        )

        if isinstance(
            career_match,
            (int, float)
        ):

            result[
                "career_match_percent"
            ] = round(
                max(
                    0,
                    min(
                        100,
                        float(career_match)
                    )
                )
            )

        else:

            total_skills = (
                len(user_skills)
                + len(
                    result.get(
                        "missing_skills",
                        []
                    )
                )
            )

            if total_skills > 0:

                fallback_match = round(
                    len(user_skills)
                    / total_skills
                    * 100
                )

            else:

                fallback_match = 0

            result[
                "career_match_percent"
            ] = fallback_match

        # =================================================
        # SORT VACANCIES
        # =================================================

        def vacancy_match(
            vacancy
        ):

            if not isinstance(
                vacancy,
                dict
            ):
                return 0

            try:

                return float(
                    vacancy.get(
                        "match_percent",
                        0
                    ) or 0
                )

            except (
                TypeError,
                ValueError
            ):

                return 0

        result["vacancies"] = sorted(
            result.get(
                "vacancies",
                []
            ),
            key=vacancy_match,
            reverse=True
        )

        # =================================================
        # SAVE ROADMAP
        # =================================================

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO roadmaps
                    (
                        user_id,
                        target_role,
                        result
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        result.get(
                            "target_role",
                            goal
                        ),
                        Json(result)
                    )
                )

                roadmap_id = (
                    cur.fetchone()[0]
                )

        # =================================================
        # RESPONSE
        # =================================================

        return {
            "id": roadmap_id,
            "user_id": user_id,
            "source": hh_data.get(
                "source",
                "demo"
            ),
            **result
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ANALYZE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET LAST ROADMAP
# =========================================================

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
                detail="Roadmap не найден"
            )

        return {
            "id": row[0],
            "target_role": row[1],
            "result": row[2]
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "GET ROADMAP ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить roadmap."
        )


# =========================================================
# ROADMAP HISTORY
# =========================================================

@app.get("/roadmaps/{user_id}")
def get_roadmaps_history(
    user_id: int
):

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
                    """,
                    (user_id,)
                )

                rows = cur.fetchall()

        history = []

        for row in rows:

            result = row[2] or {}

            history.append(
                {
                    "id": row[0],
                    "target_role": row[1],
                    "career_match_percent":
                        result.get(
                            "career_match_percent",
                            0
                        ),
                    "result": result
                }
            )

        return {
            "user_id": user_id,
            "count": len(history),
            "history": history
        }

    except Exception as e:

        print(
            "HISTORY ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить историю."
        )