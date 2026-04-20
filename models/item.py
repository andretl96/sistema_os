from database import conectar

def criar_tabela():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        os_id INTEGER,
        equipamento TEXT,
        defeito TEXT,
        garantia TEXT,
        solucao TEXT,
        status TEXT,
        FOREIGN KEY(os_id) REFERENCES os(id)
    )
    """)

    conn.commit()
    conn.close()