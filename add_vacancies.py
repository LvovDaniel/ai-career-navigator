import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_navigator",
    user="admin",
    password="admin123"
)

with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO vacancies (title, company, description, required_skills)
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
        );
    """)

conn.commit()
conn.close()

print("Вакансии добавлены!")