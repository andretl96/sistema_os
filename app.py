from flask import Flask, redirect, session
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


from flask import send_file
import io, csv, zipfile

@app.route("/backup")
def backup_db():
    if not session.get("user") or session.get("nivel") != "admin":
        return redirect("/login")
    
    conn = conectar()
    c = conn.cursor()
    
    zip_buffer = io.BytesIO()
    
    tabelas = ["clientes", "os", "itens", "os_parciais", "componentes",
               "tipos_reparo", "chamados", "usuarios"]
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for tabela in tabelas:
            try:
                c.execute(f"SELECT * FROM {tabela}")
                rows = c.fetchall()
                if not rows:
                    zf.writestr(f"{tabela}.csv", "")
                    continue
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(r) for r in rows])
                zf.writestr(f"{tabela}.csv", out.getvalue())
            except Exception as e:
                zf.writestr(f"{tabela}_erro.txt", str(e))
    
    conn.close()
    zip_buffer.seek(0)
    from datetime import datetime as dt
    nome = f"backup_techrepair_{dt.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(zip_buffer, as_attachment=True, download_name=nome, mimetype="application/zip")

if __name__ == "__main__":
    app.run(debug=True)
