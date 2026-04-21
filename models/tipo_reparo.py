from database import conectar

def criar_tabela():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS tipos_reparo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        valor_padrao REAL NOT NULL DEFAULT 0.0
    )
    """)

    conn.commit()
    conn.close()
