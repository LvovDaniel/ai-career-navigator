import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_navigator",
    user="admin",
    password="admin123"
)

print("PostgreSQL подключен!")

conn.close()