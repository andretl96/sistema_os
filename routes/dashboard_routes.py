from flask import Blueprint, render_template, session
from database import conectar
from routes.auth_routes import login_required

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard")
@login_required
def dashboard_view():
    conn = conectar()
    c = conn.cursor()
    is_admin = session.get("nivel") == "admin"

    c.execute("SELECT COUNT(*) FROM clientes")
    clientes = c.fetchone()["count"]

    c.execute("SELECT COUNT(*) FROM itens WHERE status='aguardando'")
    abertas = c.fetchone()["count"]

    c.execute("SELECT COUNT(*) FROM itens WHERE status='reparado'")
    finalizadas = c.fetchone()["count"]

    c.execute("SELECT COUNT(*) FROM itens WHERE status='aguardando_componente'")
    aguardando = c.fetchone()["count"]

    receita = None
    if is_admin:
        c.execute("""
            SELECT COALESCE(SUM(CASE WHEN garantia=0 THEN valor_cobrado ELSE 0 END), 0)
            FROM itens WHERE status='reparado'
        """)
        receita = list(c.fetchone().values())[0]

    conn.close()
    return render_template("dashboard.html", clientes=clientes, abertas=abertas,
                           finalizadas=finalizadas, aguardando=aguardando,
                           receita=receita, is_admin=is_admin)
