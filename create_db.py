import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_navigator",
    user="admin",
    password="admin123"
)

with conn.cursor() as cur:
    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            resume TEXT DEFAULT '',
            goal VARCHAR(255) NOT NULL
        );
    """)

    # Навыки
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL
        );
    """)

    # Навыки пользователя
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
            level INTEGER CHECK (level >= 1 AND level <= 5),
            PRIMARY KEY (user_id, skill_id)
        );
    """)

    # Проекты
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT DEFAULT ''
        );
    """)

    # Курсы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT DEFAULT ''
        );
    """)

    # Вакансии
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            description TEXT DEFAULT '',
            required_skills JSONB DEFAULT '[]'
        );
    """)

    # Карьерные roadmap
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roadmaps (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            target_role VARCHAR(255) NOT NULL,
            result JSONB NOT NULL
        );
    """)

conn.commit()
conn.close()

print("Все таблицы созданы!")


