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


load_dotenv()


# =========================
# CONFIG
# =========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    level: int


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

                cur.execute(
                    """
                    INSERT INTO users (name, email, goal, resume)
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
                    "user_id": user_id,
                    "message": "User created"
                }

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже существует"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# PROFILE
# =========================

@app.get("/profile/{user_id}")
def get_profile(user_id: int):
    try:
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
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/profile")
def save_profile(profile: Profile):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # Проверяем пользователя
                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = %s
                    """,
                    (profile.user_id,)
                )

                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

                # Сохраняем опыт / резюме
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

                # Удаляем старые проекты
                cur.execute(
                    """
                    DELETE FROM projects
                    WHERE user_id = %s
                    """,
                    (profile.user_id,)
                )

                # Сохраняем проекты
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
                    "message": "Profile saved"
                }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# SKILLS
# =========================

@app.post("/skills")
def add_skill(skill: UserSkill):
    if skill.level < 1 or skill.level > 5:
        raise HTTPException(
            status_code=400,
            detail="Уровень навыка должен быть от 1 до 5"
        )

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # Создаём навык, если его ещё нет
                cur.execute(
                    """
                    INSERT INTO skills (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (skill.skill,)
                )

                # Получаем id навыка
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
                        detail="Не удалось создать навык"
                    )

                skill_id = skill_row[0]

                # Связываем пользователя с навыком
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
                    "message": "Skill saved",
                    "skill": skill.skill,
                    "level": skill.level
                }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/skills/{user_id}")
def get_skills(user_id: int):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT s.name, us.level
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
                        "name": row[0],
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

                # User
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
                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

                # Skills
                cur.execute(
                    """
                    SELECT s.name, us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    """,
                    (user_id,)
                )

                skills = [
                    {
                        "name": row[0],
                        "level": row[1]
                    }
                    for row in cur.fetchall()
                ]

                # Projects
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
                    "user": {
                        "id": user[0],
                        "name": user[1],
                        "email": user[2],
                        "goal": user[3],
                        "resume": user[4]
                    },
                    "skills": skills,
                    "projects": projects
                }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# VACANCIES
# =========================

@app.get("/vacancies")
def get_vacancies():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT id, title, company, description, required_skills
                    FROM vacancies
                    ORDER BY id
                    """
                )

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
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/vacancies/real")
def get_real_vacancies():
    try:
        url = "https://api.hh.ru/vacancies"

        params = {
            "text": "Python backend developer",
            "area": 113,
            "per_page": 10
        }

        response = requests.get(
            url,
            params=params,
            timeout=5,
            headers={
                "User-Agent": "AI-Career-Navigator"
            }
        )

        if response.status_code != 200:
            return get_vacancies()

        data = response.json()

        vacancies = []

        for item in data.get("items", []):
            vacancies.append({
                "id": item.get("id"),
                "title": item.get("name"),
                "company": (
                    item.get("employer", {}).get("name")
                    or "Не указана"
                ),
                "description": "",
                "required_skills": []
            })

        if not vacancies:
            return get_vacancies()

        return vacancies

    except requests.Timeout:
        return get_vacancies()

    except requests.RequestException:
        return get_vacancies()

    except Exception:
        return get_vacancies()


# =========================
# AI ANALYSIS
# =========================

@app.post("/analyze")
def analyze(user_id: int):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                # -------------------------
                # User
                # -------------------------

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
                    raise HTTPException(
                        status_code=404,
                        detail="Пользователь не найден"
                    )

                # -------------------------
                # Skills
                # -------------------------

                cur.execute(
                    """
                    SELECT s.name, us.level
                    FROM user_skills us
                    JOIN skills s
                        ON s.id = us.skill_id
                    WHERE us.user_id = %s
                    """,
                    (user_id,)
                )

                skills = [
                    {
                        "name": row[0],
                        "level": row[1]
                    }
                    for row in cur.fetchall()
                ]

                # -------------------------
                # Projects
                # -------------------------

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

                # -------------------------
                # Vacancies
                # -------------------------

                cur.execute(
                    """
                    SELECT id, title, company, description, required_skills
                    FROM vacancies
                    ORDER BY id
                    """
                )

                vacancies = [
                    {
                        "id": row[0],
                        "title": row[1],
                        "company": row[2],
                        "description": row[3],
                        "required_skills": row[4]
                    }
                    for row in cur.fetchall()
                ]

        # -------------------------
        # AI prompt
        # -------------------------

        prompt = f"""
Ты — AI Career Navigator.

Проанализируй профиль пользователя и построй персональный карьерный маршрут.

Целевая профессия:
{user[3]}

Резюме / опыт:
{user[4]}

Навыки пользователя:
{json.dumps(skills, ensure_ascii=False)}

Проекты пользователя:
{json.dumps(projects, ensure_ascii=False)}

Вакансии:
{json.dumps(vacancies, ensure_ascii=False)}

ВАЖНО

Навыки из раздела "Навыки" являются навыками, которые пользователь указал как имеющиеся.

Не считай такой навык отсутствующим только потому, что он не упомянут в резюме или проектах.

Используй указанное пользователем значение level как текущий уровень навыка.

Например:
если в профиле есть {{"name": "Python", "level": 3}},
то Python является текущим навыком пользователя с уровнем 3.

В этом случае Python нельзя помещать в missing_skills как отсутствующий навык.

Можно указать его как навык, который нужно улучшить, если требуемый уровень выше текущего.

Не придумывай навыки, которых нет в профиле.

Если информации недостаточно, укажи это.

Уровень навыков оценивай по шкале от 1 до 5.

Для вакансий рассчитай примерный процент соответствия.

Roadmap должен двигаться от текущего уровня пользователя к целевой профессии.

Верни результат СТРОГО в JSON.

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
            "required_level": 1,
            "current_level": 1,
            "reason": "string"
        }}
    ],
    "learning": [
        {{
            "skill": "string",
            "action": "string",
            "priority": "high"
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
            "step": 1,
            "title": "string",
            "description": "string"
        }}
    ]
}}
"""

        # -------------------------
        # OpenAI
        # -------------------------

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result_text = response.output_text.strip()

        # Убираем markdown JSON, если AI его добавил
        if result_text.startswith("```json"):
            result_text = result_text[7:]

        if result_text.startswith("```"):
            result_text = result_text[3:]

        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result_text = result_text.strip()

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="AI вернул некорректный JSON"
            )

        # -------------------------
        # Save roadmap
        # -------------------------

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

                conn.commit()

        return result

    except HTTPException:
        raise

    except Exception as e:
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

                cur.execute(
                    """
                    SELECT id, target_role, result
                    FROM roadmaps
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,)
                )

                roadmap = cur.fetchone()

                if not roadmap:
                    raise HTTPException(
                        status_code=404,
                        detail="Roadmap не найден"
                    )

                return {
                    "id": roadmap[0],
                    "target_role": roadmap[1],
                    "result": roadmap[2]
                }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )