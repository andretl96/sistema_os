from flask import Blueprint, render_template, request, redirect
from database import conectar
from routes.auth_routes import login_required, admin_required

estoque = Blueprint("estoque", __name__)

@estoque.route("/componentes", methods=["GET", "POST"])
@admin_required
def componentes():
    conn = conectar()
    c = conn.cursor()
    if request.method == "POST":
        nome = request.form.get("nome")
        quantidade = request.form.get("quantidade", 0)
        preco = request.form.get("preco", 0.0)
        c.execute("INSERT INTO componentes (nome, quantidade, preco) VALUES (%s, %s, %s)",
                  (nome, quantidade, preco))
        conn.commit()
    c.execute("SELECT * FROM componentes")
    lista = c.fetchall()
    alerta = [comp for comp in lista if comp["quantidade"] < 5]
    conn.close()
    return render_template("componentes.html", componentes=lista, alerta=alerta)

@estoque.route("/excluir_componente/<int:id>")
@admin_required
def excluir_componente(id):
    conn = conectar()
    c = conn.cursor()
    c.execute("DELETE FROM componentes WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/componentes")
