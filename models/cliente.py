from database import conectar

def criar_tabela():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT,
        email TEXT,
        cpf_cnpj TEXT,
        rua TEXT,
        numero TEXT,
        bairro TEXT,
        cidade TEXT,
        cep TEXT,
        observacoes TEXT
    )
    """)

    # Migração: adiciona colunas se não existirem (banco já existente)
    colunas_novas = ['email','cpf_cnpj','rua','numero','bairro','cidade','cep','observacoes']
    c.execute("PRAGMA table_info(clientes)")
    existentes = [col[1] for col in c.fetchall()]
    for col in colunas_novas:
        if col not in existentes:
            c.execute(f"ALTER TABLE clientes ADD COLUMN {col} TEXT")

    conn.commit()
    conn.close()
