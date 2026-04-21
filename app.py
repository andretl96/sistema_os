from flask import Flask, redirect
from config import SECRET_KEY

from routes.auth_routes import auth
from routes.os_routes import os_bp
from routes.estoque_routes import estoque
from routes.dashboard_routes import dashboard
from routes.clientes_routes import clientes_bp
from routes.reparo_routes import reparo_bp
from routes.tipos_reparo_routes import tipos_reparo_bp
from routes.portal_routes import portal_bp

from database import conectar
from models.init_db import criar_tabelas

# 1. Cria todas as tabelas PRIMEIRO
criar_tabelas()

# 2. Só depois insere o admin
def criar_admin():
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, senha, tipo) VALUES ('admin', '123', 'admin')")
        conn.commit()
    conn.close()

criar_admin()

# 3. Cria o app
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def home():
    return redirect("/login")

app.register_blueprint(auth)
app.register_blueprint(os_bp)
app.register_blueprint(estoque)
app.register_blueprint(dashboard)
app.register_blueprint(clientes_bp)
app.register_blueprint(reparo_bp)
app.register_blueprint(tipos_reparo_bp)
app.register_blueprint(portal_bp)

if __name__ == "__main__":
    app.run(debug=True)
