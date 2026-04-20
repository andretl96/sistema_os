from routes.auth_routes import admin_required
from flask import Blueprint, render_template, request, redirect, jsonify
from database import conectar

tipos_reparo_bp = Blueprint("tipos_reparo", __name__)

@tipos_reparo_bp.route("/tipos_reparo", methods=["GET", "POST"])
@admin_required
def listar():
    conn = conectar()
    c = conn.cursor()

    if request.method == "POST":
        nome  = request.form.get("nome", "").strip()
        desc  = request.form.get("descricao", "").strip()
        valor = request.form.get("valor_padrao", "0").replace(",", ".")
        try:
            valor = float(valor)
        except ValueError:
            valor = 0.0

        if nome:
            c.execute(
                "INSERT INTO tipos_reparo (nome, descricao, valor_padrao) VALUES (%s,%s,%s)",
                (nome, desc, valor)
            )
            conn.commit()

    c.execute("SELECT * FROM tipos_reparo ORDER BY nome")
    tipos = c.fetchall()
    conn.close()
    return render_template("tipos_reparo.html", tipos=tipos)


@tipos_reparo_bp.route("/editar_tipo_reparo/<int:id>", methods=["GET", "POST"])
@admin_required
def editar(id):
    conn = conectar()
    c = conn.cursor()

    if request.method == "POST":
        nome  = request.form.get("nome","").strip()
        desc  = request.form.get("descricao","").strip()
        valor = request.form.get("valor_padrao","0").replace(",",".")
        try:
            valor = float(valor)
        except ValueError:
            valor = 0.0

        c.execute(
            "UPDATE tipos_reparo SET nome=%s, descricao=%s, valor_padrao=%s WHERE id=%s",
            (nome, desc, valor, id)
        )
        conn.commit()
        conn.close()
        return redirect("/tipos_reparo")

    c.execute("SELECT * FROM tipos_reparo WHERE id=%s", (id,))
    tipo = c.fetchone()
    conn.close()
    return render_template("editar_tipo_reparo.html", tipo=tipo)


@tipos_reparo_bp.route("/excluir_tipo_reparo/<int:id>")
@admin_required
def excluir(id):
    conn = conectar()
    c = conn.cursor()
    c.execute("DELETE FROM tipos_reparo WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/tipos_reparo")


@tipos_reparo_bp.route("/api/tipo_reparo/<int:id>")
@admin_required
def api_valor(id):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT valor_padrao FROM tipos_reparo WHERE id=%s", (id,))
    row = c.fetchone()
    conn.close()
    return jsonify({"valor": row["valor_padrao"] if row else 0.0})
