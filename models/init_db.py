from database import conectar

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    # USUARIOS
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        senha TEXT,
        tipo TEXT
    )
    """)

    # CLIENTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
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

    # OS
    c.execute("""
    CREATE TABLE IF NOT EXISTS os (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes(id),
        data TEXT,
        status TEXT DEFAULT 'aberta'
    )
    """)

    # TIPOS DE REPARO (antes de itens por causa da FK)
    c.execute("""
    CREATE TABLE IF NOT EXISTS tipos_reparo (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        descricao TEXT,
        valor_padrao REAL NOT NULL DEFAULT 0.0
    )
    """)

    # ITENS
    c.execute("""
    CREATE TABLE IF NOT EXISTS itens (
    id SERIAL PRIMARY KEY,
    os_id INTEGER REFERENCES os(id),
    equipamento TEXT,
    defeito TEXT,
    garantia INTEGER DEFAULT 0,
    solucao TEXT,
    status TEXT DEFAULT 'aguardando',
    tipo_reparo_id INTEGER REFERENCES tipos_reparo(id),
    valor_cobrado REAL DEFAULT 0.0,
    mac TEXT
)
    CREATE TABLE IF NOT EXISTS itens (
        id SERIAL PRIMARY KEY,
        os_id INTEGER REFERENCES os(id),
        equipamento TEXT,
        defeito TEXT,
        garantia INTEGER DEFAULT 0,
        solucao TEXT,
        status TEXT DEFAULT 'aguardando',
        tipo_reparo_id INTEGER REFERENCES tipos_reparo(id),
        valor_cobrado REAL DEFAULT 0.0
    )
    """)

    # COMPONENTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS componentes (
        id SERIAL PRIMARY KEY,
        nome TEXT,
        quantidade INTEGER,
        preco REAL
    )
    """)

    # PARCIAIS DA OS
    c.execute("""
    CREATE TABLE IF NOT EXISTS os_parciais (
        id SERIAL PRIMARY KEY,
        os_id INTEGER NOT NULL REFERENCES os(id),
        data TEXT NOT NULL,
        valor_cobrado REAL DEFAULT 0.0,
        pago INTEGER DEFAULT 0,
        descricao TEXT
    )
    """)

    # Migrações: adiciona colunas que podem faltar em bancos existentes
    migracoes = {
        'clientes': [
            ('email', 'TEXT'),
            ('cpf_cnpj', 'TEXT'),
            ('rua', 'TEXT'),
            ('numero', 'TEXT'),
            ('bairro', 'TEXT'),
            ('cidade', 'TEXT'),
            ('cep', 'TEXT'),
            ('observacoes', 'TEXT'),
        ],
        'itens': [
            ('solucao', 'TEXT'),
            ('tipo_reparo_id', 'INTEGER'),
            ('valor_cobrado', 'REAL DEFAULT 0.0'),
            ('mac', 'TEXT'),
        ],
        'os': [
            ('status', "TEXT DEFAULT 'aberta'"),
        ],
    }

    for tabela, colunas in migracoes.items():
        for col, tipo in colunas:
            c.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name=%s AND column_name=%s
            """, (tabela, col))
            if not c.fetchone():
                c.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")

    conn.commit()
    conn.close()
