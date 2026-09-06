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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY is not set")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="AI Career Navigator API",
    version="1.0.0"
)


# =========================
# CORS
# =========================

FRONTEND_URL = os.getenv("FRONTEND_URL", "")

allow_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://delightful-adaptation-production-fd1f.up.railway.app",
]

if FRONTEND_URL and FRONTEND_URL not in allow_origins:
    allow_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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
        password=os.getenv("DB_PASSWORD", "admin123"),
    )


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    resume TEXT DEFAULT '',
                    goal VARCHAR(255) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS skills (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_skills (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
                    level INTEGER CHECK (level >= 1 AND level <= 5),
                    PRIMARY KEY (user_id, skill_id)
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS vacancies (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    company VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    required_skills JSONB DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS roadmaps (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    target_role VARCHAR(255) NOT NULL,
                    result JSONB NOT NULL
                );
            """)

            # Добавляем демо-вакансии только если таблица пустая
            cur.execute("SELECT COUNT(*) FROM vacancies")
            vacancy_count = cur.fetchone()[0]

            if vacancy_count == 0:
                cur.execute("""
                    INSERT INTO vacancies
                    (title, company, description, required_skills)
                    VALUES
                    (
                        'Junior Backend Developer',
                        'Tech Company',
                        'Разработка backend-приложений',
                        '["Python", "SQL", "Git", "FastAPI"]'
                    ),
                    (
                        'Python Developer',
                        'IT Company',
                        'Разработка сервисов на Python',
                        '["Python", "PostgreSQL", "Docker", "Git"]'
                    ),
                    (
                        'Backend Developer',
                        'AI Company',
                        'Разработка API и backend-сервисов',
                        '["Python", "FastAPI", "PostgreSQL", "Docker", "SQL"]'
                    )
                """)

            conn.commit()

    print("Database initialized successfully")


@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as e:
        print("DATABASE INITIALIZATION ERROR:", e)


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
    level: int = 3


# =========================
# ROOT
# =========================

@app.get("/")
def root():
    return {
        "message": "AI Career Navigator API",
        "status": "running"
    }


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

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO users
                    (name, email, goal, resume)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        goal = EXCLUDED.goal,
                        resume = EXCLUDED.resume
                    RETURNING id
                """, (
                    user.name,
                    user.email,
                    user.goal,
                    user.resume
                ))

                user_id = cur.fetchone()[0]

                conn.commit()

        return {
            "user_id": user_id,
            "message": "User created successfully"
        }

    except Exception as e:
        print("CREATE USER ERROR:", e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# PROFILE
# =========================

@app.post("/profile")
def save_profile(profile: Profile):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # Проверяем пользователя
                cur.execute(
                    "SELECT id FROM users WHERE id = %s",
                    (profile.user_id,)
                )

                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                # Сохраняем опыт / резюме
                cur.execute("""
                    UPDATE users
                    SET resume = %s
                    WHERE id = %s
                """, (
                    profile.experience,
                    profile.user_id
                ))

                # Пересоздаём проекты
                cur.execute("""
                    DELETE FROM projects
                    WHERE user_id = %s
                """, (profile.user_id,))

                for project in profile.projects:
                    project = project.strip()

                    if project:
                        cur.execute("""
                            INSERT INTO projects
                            (user_id, name, description)
                            VALUES (%s, %s, %s)
                        """, (
                            profile.user_id,
                            project[:100],
                            project
                        ))

                conn.commit()

        return {
            "message": "Profile saved successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print("SAVE PROFILE ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# SKILLS
# =========================

@app.post("/skills")
def add_skill(skill_data: UserSkill):

    if skill_data.level < 1 or skill_data.level > 5:
        raise HTTPException(
            status_code=400,
            detail="Skill level must be between 1 and 5"
        )

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # Создаём навык, если его ещё нет
                cur.execute("""
                    INSERT INTO skills (name)
                    VALUES (%s)
                    ON CONFLICT (name)
                    DO NOTHING
                """, (skill_data.skill,))

                # Получаем ID навыка
                cur.execute("""
                    SELECT id
                    FROM skills
                    WHERE name = %s
                """, (skill_data.skill,))

                skill_row = cur.fetchone()

                if not skill_row:
                    raise HTTPException(
                        status_code=500,
                        detail="Could not create skill"
                    )

                skill_id = skill_row[0]

                # Привязываем навык пользователю
                cur.execute("""
                    INSERT INTO user_skills
                    (user_id, skill_id, level)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, skill_id)
                    DO UPDATE SET
                        level = EXCLUDED.level
                """, (
                    skill_data.user_id,
                    skill_id,
                    skill_data.level
                ))

                conn.commit()

        return {
            "message": "Skill saved successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print("ADD SKILL ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/skills/{user_id}")
def get_skills(user_id: int):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        skills.name,
                        user_skills.level
                    FROM user_skills
                    JOIN skills
                        ON skills.id = user_skills.skill_id
                    WHERE user_skills.user_id = %s
                    ORDER BY skills.name
                """, (user_id,))

                rows = cur.fetchall()

        return [
            {
                "name": row[0],
                "level": row[1]
            }
            for row in rows
        ]

    except Exception as e:
        print("GET SKILLS ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# FULL PROFILE
# =========================

@app.get("/profile/{user_id}")
def get_profile(user_id: int):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT id, name, email, goal, resume
                    FROM users
                    WHERE id = %s
                """, (user_id,))

                user = cur.fetchone()

                if not user:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found"
                    )

                cur.execute("""
                    SELECT skills.name, user_skills.level
                    FROM user_skills
                    JOIN skills
                        ON skills.id = user_skills.skill_id
                    WHERE user_skills.user_id = %s
                """, (user_id,))

                skills = cur.fetchall()

                cur.execute("""
                    SELECT name, description
                    FROM projects
                    WHERE user_id = %s
                """, (user_id,))

                projects = cur.fetchall()

        return {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "goal": user[3],
            "resume": user[4],
            "skills": [
                {
                    "name": row[0],
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
            ]
        }

    except HTTPException:
        raise

    except Exception as e:
        print("GET PROFILE ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/profile/full/{user_id}")
def get_full_profile(user_id: int):
    return get_profile(user_id)


# =========================
# VACANCIES
# =========================

@app.get("/vacancies")
def get_vacancies():

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        title,
                        company,
                        description,
                        required_skills
                    FROM vacancies
                    ORDER BY id
                """)

                rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "description": row[3],
                "required_skills": row[4]
            }
            for row in rows
        ]

    except Exception as e:
        print("GET VACANCIES ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/vacancies/real")
def get_real_vacancies():

    # Для MVP оставляем демо-вакансии.
    return get_vacancies()


# =========================
# ANALYZE
# =========================

@app.post("/analyze")
def analyze(user_id: int):

    if client is None:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured"
        )

    try:
        # Получаем профиль
        profile = get_profile(user_id)

        # Получаем вакансии
        vacancies = get_vacancies()

        skills_text = "\n".join(
            [
                f"- {skill['name']}: уровень {skill['level']}/5"
                for skill in profile["skills"]
            ]
        )

        projects_text = "\n".join(
            [
                f"- {project['name']}: {project['description']}"
                for project in profile["projects"]
            ]
        )

        vacancies_text = json.dumps(
            vacancies,
            ensure_ascii=False
        )

        prompt = f"""
Ты — карьерный AI-помощник.

Проанализируй профиль пользователя и построй персональный карьерный маршрут.

Целевая профессия:
{profile["goal"]}

Резюме / опыт:
{profile["resume"]}

Текущие навыки:
{skills_text}

Проекты:
{projects_text}

Доступные вакансии:
{vacancies_text}


ВАЖНО

Навыки из раздела "Текущие навыки" являются навыками,
которые пользователь указал как имеющиеся.

Не считай такой навык отсутствующим только потому,
что он не упомянут в резюме или проектах.

Используй указанное пользователем значение level
как текущий уровень навыка.

Например:

если в профиле есть:
Python — уровень 3,

то Python является текущим навыком пользователя
с уровнем 3.

В этом случае Python нельзя помещать
в missing_skills как полностью отсутствующий навык.

Можно указать его как навык,
который нужно улучшить,
если требуемый уровень выше текущего.

Не придумывай навыки,
которых нет в профиле.

Если информации недостаточно,
укажи это.

Уровень навыков оценивай по шкале от 1 до 5.

Для вакансий рассчитай примерный процент соответствия.

Roadmap должен двигаться от текущего уровня
пользователя к целевой профессии.


Верни ТОЛЬКО валидный JSON.

Структура:

{{
    "target_role": "string",
    "current_level": "string",
    "strengths": [
        {{
            "skill": "string",
            "level": 1
        }}
    ],
    "missing_skills": [
        {{
            "skill": "string",
            "reason": "string",
            "priority": "high"
        }}
    ],
    "learning": [
        {{
            "skill": "string",
            "action": "string"
        }}
    ],
    "recommended_project": {{
        "name": "string",
        "description": "string",
        "skills": ["string"]
    }},
    "vacancies": [
        {{
            "title": "string",
            "company": "string",
            "match_percent": 0,
            "missing_skills": ["string"]
        }}
    ],
    "next_step": "string",
    "roadmap": [
        {{
            "stage": 1,
            "title": "string",
            "description": "string"
        }}
    ]
}}
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result_text = response.output_text.strip()

        # Убираем markdown JSON, если модель его добавила
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "")
            result_text = result_text.replace("```", "")
            result_text = result_text.strip()

        result = json.loads(result_text)

        # Сохраняем roadmap
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO roadmaps
                    (user_id, target_role, result)
                    VALUES (%s, %s, %s)
                """, (
                    user_id,
                    result.get("target_role", profile["goal"]),
                    Json(result)
                ))

                conn.commit()

        return result

    except json.JSONDecodeError as e:
        print("AI JSON ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail="AI returned invalid JSON"
        )

    except HTTPException:
        raise

    except Exception as e:
        print("ANALYZE ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# ROADMAP
# =========================

@app.get("/roadmap/{user_id}")
def get_roadmap(user_id: int):

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        target_role,
                        result
                    FROM roadmaps
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (user_id,))

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
        print("GET ROADMAP ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )