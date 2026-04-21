import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def conectar():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn
