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


CREATE TABLE IF NOT EXISTS mentor_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO vacancies (
    title,
    company,
    description,
    required_skills
)
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