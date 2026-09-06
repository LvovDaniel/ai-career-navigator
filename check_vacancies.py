import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_navigator",
    user="admin",
    password="admin123"
)

with conn.cursor() as cur:
    cur.execute("SELECT * FROM vacancies;")
    rows = cur.fetchall()

    print(rows)

conn.close()