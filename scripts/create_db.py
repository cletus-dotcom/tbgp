import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="password",
    dbname="postgres",
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'tbgp'")
if cur.fetchone():
    print("Database tbgp already exists")
else:
    cur.execute("CREATE DATABASE tbgp")
    print("Database tbgp created")
