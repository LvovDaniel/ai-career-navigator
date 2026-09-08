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
import time

# =========================================================
# ENV
# =========================================================

load_dotenv(override=True)


# =========================================================
# YANDEX AI STUDIO
# =========================================================

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL")

client = OpenAI(
    api_key=YANDEX_API_KEY,
    project=YANDEX_FOLDER_ID,
    base_url="https://ai.api.cloud.yandex.net/v1"
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

AVAILABLE_SKILLS = [
    "Python",
    "C++",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "HTML",
    "CSS",
    "FastAPI",
    "Django",
    "PostgreSQL",
    "SQL",
    "Git",
    "Docker",
    "Linux",
    "REST API",
    "OOP",
    "STL",
    "CMake",
    "Pandas",
    "NumPy",
    "Power BI",
    "Excel",
    "UML",
    "BPMN",
    "Testing",
    "CI/CD"
]
# =========================================================
# NORMALIZE PROFESSION
# =========================================================

def normalize_profession(value: str) -> str:
    return " ".join(
        (value or "").strip().lower().split()
    )


# =========================================================
# NORMALIZE SKILL
# =========================================================

def normalize_skill_name(value: str) -> str:

    value = str(
        value or ""
    ).strip().lower()

    replacements = {
        "с": "c",
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "х": "x",
        "у": "y",
        "к": "k",
        "м": "m",
        "т": "t",
        "в": "b"
    }

    return "".join(
        replacements.get(
            char,
            char
        )
        for char in value
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
        normalize_profession(
            profession
        )
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

    goal = (
        goal or ""
    ).strip()

    experience = (
        experience or ""
    ).strip()

    if not is_valid_profession(goal):
        return False

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

                user_id = (
                    cur.fetchone()[0]
                )

        return {
            "user_id": user_id
        }

    except Exception as e:

        print(
            "CREATE USER ERROR:",
            e
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
            e
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
            e
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
            skill.skill.strip()
        )

        if not skill_name:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Название навыка "
                    "не может быть пустым."
                )
            )

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = %s
                    """,
                    (skill.user_id,)
                )

                user = cur.fetchone()

                if not user:

                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

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

                    skill_id = (
                        cur.fetchone()[0]
                    )

                cur.execute(
                    """
                    INSERT INTO user_skills
                    (user_id, skill_id, level)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, skill_id)
                    DO UPDATE SET
                        level = EXCLUDED.level
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
            e
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

    if payload.user_id != user_id:

        raise HTTPException(
            status_code=400,
            detail="user_id не совпадает."
        )

    try:

        with get_db() as conn:

            with conn.cursor() as cur:

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

                cur.execute(
                    """
                    DELETE FROM user_skills
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                saved_skills = []
                seen_skills = set()

                for item in payload.skills:

                    skill_name = (
                        item.skill.strip()
                    )

                    normalized_name = (
                        normalize_skill_name(
                            skill_name
                        )
                    )

                    if (
                        not skill_name
                        or normalized_name
                        in seen_skills
                    ):
                        continue

                    seen_skills.add(
                        normalized_name
                    )

                    cur.execute(
                        """
                        SELECT id
                        FROM skills
                        WHERE LOWER(name) = LOWER(%s)
                        LIMIT 1
                        """,
                        (skill_name,)
                    )

                    skill_row = (
                        cur.fetchone()
                    )

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

                        skill_id = (
                            skill_row[0]
                        )

                    cur.execute(
                        """
                        INSERT INTO user_skills (
                            user_id,
                            skill_id,
                            level
                        )
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, skill_id)
                        DO UPDATE SET
                            level = EXCLUDED.level
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
            "user_id": user_id,
            "skills": saved_skills,
            "count": len(saved_skills)
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "REPLACE SKILLS ERROR:",
            e
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
            e
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

                cur.execute(
                    """
                    SELECT
                        s.name,
                        us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    """,
                    (user_id,)
                )

                skill_rows = (
                    cur.fetchall()
                )

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

                project_rows = (
                    cur.fetchall()
                )

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
            e
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
        },
        {
            "id": "demo-4",
            "title": "Junior C++ Developer",
            "company": "C++ Solutions",
            "description": (
                "C++, Git, OOP, STL, CMake"
            ),
            "required_skills": [
                "C++",
                "Git",
                "OOP",
                "STL",
                "CMake"
            ],
            "url": "",
            "area": "Екатеринбург",
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
        "per_page": 3
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
            e
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
    print("🔥 ANALYZE START", user_id)
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
        # ПРОВЕРКА ПРОФЕССИИ
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

                skill_rows = (
                    cur.fetchall()
                )

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
        # DEMO VACANCIES
        # =================================================

        vacancies_data = get_vacancies()

        hh_data = {
            "source": "demo",
            "vacancies": vacancies_data
        }
        print("ANALYZE: DEMO VACANCIES OK")
        # =================================================
        # EXACT VACANCY MATCH
        # =================================================

        user_skill_names = {
            normalize_skill_name(
                skill.get(
                    "skill",
                    ""
                )
            )
            for skill in user_skills
            if str(
                skill.get(
                    "skill",
                    ""
                )
            ).strip()
        }

        print(
            "USER SKILLS:",
            user_skills
        )

        print(
            "USER SKILL NAMES:",
            user_skill_names
        )

        print(
            "VACANCIES SOURCE:",
            hh_data.get("source")
        )

        if hh_data.get("source") == "demo":

            for vacancy in vacancies_data:

                required_skills = (
                    vacancy.get(
                        "required_skills",
                        []
                    )
                )

                matched = []
                missing = []

                for required_skill in required_skills:

                    required_name = (
                        normalize_skill_name(
                            required_skill
                        )
                    )

                    if required_name in user_skill_names:

                        matched.append(
                            required_skill
                        )

                    else:

                        missing.append(
                            required_skill
                        )

                if required_skills:

                    total_score = 0

                    for required_skill in required_skills:

                        required_name = normalize_skill_name(
                            required_skill
                        )

                        actual_skill = None

                        for user_skill in user_skills:

                            user_skill_name = normalize_skill_name(
                                user_skill.get("skill", "")
                            )

                            if user_skill_name == required_name:
                                actual_skill = user_skill
                                break

                        if actual_skill is not None:
                            current_level = int(
                                actual_skill.get(
                                    "level",
                                    0
                                ) or 0
                            )

                            # Каждый навык даёт вклад
                            # в зависимости от его уровня.
                            # 5/5 = 100% покрытия навыка
                            # 3/5 = 60% покрытия навыка
                            skill_score = (
                                                  current_level / 5
                                          ) * 100

                            total_score += skill_score

                    match_percent = round(
                        total_score / len(required_skills)
                    )

                else:

                    match_percent = 0


                vacancy["match_percent"] = (
                    match_percent
                )

                vacancy["matched_skills"] = (
                    matched
                )

                vacancy["missing_skills"] = (
                    missing
                )

        # =================================================
        # VACANCIES TEXT
        # =================================================

        vacancies_text = "\n".join(
            [
                (
                    f"{vacancy.get('title', '')}: "
                    f"{vacancy.get('required_skills', [])}"
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

        Проведи краткий карьерный анализ пользователя.

        Целевая профессия:
        {goal}

        Навыки пользователя:
        {skills_text}

        Опыт:
        {experience}

        Вакансии:
        {vacancies_text}

        Определи:
        1. Сильные стороны пользователя.
        2. Какие навыки стоит изучить.
        3. Какой практический проект сделать.
        4. Краткий план развития.

        ВАЖНО:
        - Не придумывай навыки пользователя.
        - Не рассчитывай проценты соответствия.
        - Не анализируй вакансии подробно.
        - Ответ должен быть коротким.
        - Верни ТОЛЬКО валидный JSON.
        - Без markdown.
        - Без ```json.
        - Без текста до или после JSON.

        Формат ответа:

        {{
            "analysis": "Краткая оценка текущего уровня",
            "strengths": [
                "сильная сторона 1",
                "сильная сторона 2"
            ],
            "missing_skills": [
                {{
                    "skill": "Python",
                    "reason": "Почему навык нужен"
                }}
            ],
            "learning": [
                "Что изучить сначала",
                "Что изучить потом"
            ],
            "project": {{
                "title": "Название проекта",
                "description": "Краткое описание проекта"
            }},
            "roadmap": [
                {{
                    "step": 1,
                    "title": "Первый шаг",
                    "description": "Что сделать"
                }},
                {{
                    "step": 2,
                    "title": "Второй шаг",
                    "description": "Что сделать"
                }},
                {{
                    "step": 3,
                    "title": "Третий шаг",
                    "description": "Что сделать"
                }}
            ]
        }}
        """

        # =================================================
        # YANDEX AI
        # =================================================
        start_time = time.time()

        response = client.chat.completions.create(
            model=YANDEX_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=900
        )

        raw_result = (
                response.choices[0].message.content
                or ""
        ).strip()

        print(
            f"YANDEX AI TIME: {time.time() - start_time:.2f} sec"
        )

        # =================================================
        # CLEAN JSON
        # =================================================

        if not raw_result:

            raise HTTPException(
                status_code=500,
                detail="AI не вернул результат."
            )

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

        if raw_result.endswith("```"):

            raw_result = raw_result[
                :-3
            ].strip()

        # =================================================
        # EXTRACT JSON
        # =================================================

        first_brace = (
            raw_result.find("{")
        )

        last_brace = (
            raw_result.rfind("}")
        )

        if (
            first_brace != -1
            and last_brace != -1
            and last_brace > first_brace
        ):

            raw_result = raw_result[
                first_brace:
                last_brace + 1
            ]

        else:

            print(
                "AI JSON ERROR: "
                "JSON object not found"
            )

            raise HTTPException(
                status_code=500,
                detail="AI вернул некорректный результат."
            )

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
                e
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
        # ACTUAL USER SKILLS
        # =================================================

        actual_skills = {
            normalize_skill_name(
                item.get(
                    "skill",
                    ""
                )
            ): item
            for item in user_skills
            if str(
                item.get(
                    "skill",
                    ""
                )
            ).strip()
        }
        # =================================================
        # CAREER PATHS BY USER SKILLS
        # =================================================

        CAREER_REQUIREMENTS = {
            "Backend Developer": [
                "Python",
                "FastAPI",
                "PostgreSQL",
                "Git",
                "Docker"
            ],

            "Python Developer": [
                "Python",
                "Git",
                "SQL",
                "REST API"
            ],

            "C++ Developer": [
                "C++",
                "Git",
                "OOP",
                "STL",
                "CMake"
            ],

            "Frontend Developer": [
                "JavaScript",
                "TypeScript",
                "React",
                "HTML",
                "CSS"
            ],

            "DevOps Engineer": [
                "Linux",
                "Docker",
                "Git",
                "CI/CD"
            ],

            "Data Analyst": [
                "Python",
                "SQL",
                "Excel",
                "Pandas",
                "Power BI"
            ],

            "System Analyst": [
                "SQL",
                "UML",
                "BPMN",
                "API",
                "REST API"
            ],

            "QA Engineer": [
                "Testing",
                "Python",
                "SQL",
                "Git",
                "API"
            ]
        }

        def calculate_skill_match(required_skills, user_skills):

            if not required_skills:
                return 0

            total = 0

            for required_skill in required_skills:

                required_name = normalize_skill_name(
                    required_skill
                )

                best_level = 0

                for user_skill in user_skills:

                    user_name = normalize_skill_name(
                        user_skill.get("skill", "")
                    )

                    if user_name == required_name:

                        try:
                            level = int(
                                user_skill.get(
                                    "level",
                                    0
                                ) or 0
                            )
                        except:
                            level = 0

                        best_level = max(
                            best_level,
                            level
                        )

                # 5/5 = 100%
                # 4/5 = 80%
                # 3/5 = 60%
                # 2/5 = 40%
                # 1/5 = 20%
                total += (
                                 best_level / 5
                         ) * 100

            return round(
                total / len(required_skills)
            )

        # -------------------------------------------------
        # Формируем 3 лучших направления
        # -------------------------------------------------

        career_candidates = []

        for title, required_skills in CAREER_REQUIREMENTS.items():

            percent = calculate_skill_match(
                required_skills,
                user_skills
            )

            matched = []
            missing = []

            for required_skill in required_skills:

                required_name = normalize_skill_name(
                    required_skill
                )

                found = False

                for user_skill in user_skills:

                    user_name = normalize_skill_name(
                        user_skill.get("skill", "")
                    )

                    if user_name == required_name:

                        try:
                            level = int(
                                user_skill.get(
                                    "level",
                                    0
                                ) or 0
                            )
                        except:
                            level = 0

                        if level > 0:
                            matched.append(
                                required_skill
                            )
                            found = True

                        break

                if not found:
                    missing.append(
                        required_skill
                    )

            career_candidates.append(
                {
                    "title": title,
                    "match_percent": percent,
                    "why": (
                        "Процент рассчитан на основе "
                        "текущих навыков и их уровня."
                    ),
                    "description": (
                        f"Направление {title} "
                        "соответствует части текущих навыков."
                    ),
                    "required_skills": required_skills,
                    "missing_skills": missing,
                    "first_step": (
                        f"Развить навыки: "
                        f"{', '.join(missing[:2])}"
                        if missing
                        else "Углубить текущие навыки."
                    ),
                    "recommended_project": (
                        f"Создать учебный проект "
                        f"для направления {title}."
                    )
                }
            )

        career_candidates.sort(
            key=lambda x: x["match_percent"],
            reverse=True
        )

        result["career_paths"] = career_candidates[:3]
        # =================================================
        # PROTECT STRENGTHS
        # =================================================

        filtered_strengths = []

        for strength in result.get(
            "strengths",
            []
        ):

            if not isinstance(
                strength,
                str
            ):
                continue

            strength_lower = (
                normalize_skill_name(
                    strength
                )
            )

            if any(
                skill_name in strength_lower
                for skill_name in actual_skills
            ):

                filtered_strengths.append(
                    strength
                )

        if not filtered_strengths:

            filtered_strengths = [
                (
                    f"{item['skill']}: "
                    f"уровень {item['level']}"
                )
                for item in user_skills
            ]

        result["strengths"] = (
            filtered_strengths
        )

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

            normalized_missing_name = (
                normalize_skill_name(
                    skill_name
                )
            )

            actual = actual_skills.get(
                normalized_missing_name
            )

            if actual is not None:

                current_level = int(
                    actual.get(
                        "level",
                        0
                    ) or 0
                )

                required_level = int(
                    item.get(
                        "required_level",
                        5
                    ) or 5
                )

                if current_level >= required_level:

                    continue

                item["current_level"] = (
                    current_level
                )

            filtered_missing.append(
                item
            )

        result["missing_skills"] = (
            filtered_missing
        )

        # =================================================
        # REAL CAREER MATCH
        # =================================================

        target_requirements = (
            CAREER_REQUIREMENTS.get(
                goal,
                []
            )
        )

        if target_requirements:

            result["career_match_percent"] = (
                calculate_skill_match(
                    target_requirements,
                    user_skills
                )
            )

        else:

            result["career_match_percent"] = 0

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
        # FORCE DEMO VACANCY MATCH
        # =================================================

        if hh_data.get("source") == "demo":

            result["vacancies"] = [
                {
                    "id": vacancy.get(
                        "id"
                    ),
                    "title": vacancy.get(
                        "title"
                    ),
                    "company": vacancy.get(
                        "company"
                    ),
                    "description":
                        vacancy.get(
                            "description"
                        ),
                    "required_skills":
                        vacancy.get(
                            "required_skills",
                            []
                        ),
                    "match_percent":
                        vacancy.get(
                            "match_percent",
                            0
                        ),
                    "matched_skills":
                        vacancy.get(
                            "matched_skills",
                            []
                        ),
                    "missing_skills":
                        vacancy.get(
                            "missing_skills",
                            []
                        ),
                    "url":
                        vacancy.get(
                            "url",
                            ""
                        )
                }
                for vacancy in vacancies_data
            ]

        # =================================================
        # SORT VACANCIES
        # =================================================

        def vacancy_match(vacancy):

            try:

                return float(
                    vacancy.get(
                        "match_percent",
                        0
                    ) or 0
                )

            except Exception:

                return 0

        result["vacancies"] = [
            vacancy
            for vacancy in result["vacancies"]
            if vacancy_match(vacancy) > 0
        ]

        result["vacancies"] = sorted(
            result["vacancies"],
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
                    (user_id, target_role, result)
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
            e
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
            e
        )

        raise HTTPException(
            status_code=500,
            detail="Не удалось получить историю."
        )