from flask import Blueprint, render_template, request, redirect, session, flash
from database import conectar
from routes.auth_routes import login_required, admin_required

clientes_bp = Blueprint("clientes", __name__)

@clientes_bp.route("/clientes", methods=["GET", "POST"])
@login_required
def listar_clientes():
    conn = conectar()
    c = conn.cursor()
    is_admin = session.get("nivel") == "admin"

    if request.method == "POST":
        campos = (
            request.form.get("nome", "").strip(),
            request.form.get("telefone", "").strip(),
            request.form.get("email", "").strip(),
            request.form.get("cpf_cnpj", "").strip(),
            request.form.get("rua", "").strip(),
            request.form.get("numero", "").strip(),
            request.form.get("bairro", "").strip(),
            request.form.get("cidade", "").strip(),
            request.form.get("cep", "").strip(),
            request.form.get("observacoes", "").strip(),
        )
        if campos[0]:
            c.execute("""
                INSERT INTO clientes (nome,telefone,email,cpf_cnpj,rua,numero,bairro,cidade,cep,observacoes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, campos)
            conn.commit()

    busca = request.args.get("q", "").strip()
    if busca:
        c.execute("SELECT * FROM clientes WHERE nome ILIKE %s OR cpf_cnpj ILIKE %s OR telefone ILIKE %s",
                  (f"%{busca}%", f"%{busca}%", f"%{busca}%"))
    else:
        c.execute("SELECT * FROM clientes ORDER BY nome")
    lista = c.fetchall()
    conn.close()
    return render_template("clientes.html", clientes=lista, busca=busca, is_admin=is_admin)


@clientes_bp.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_cliente(id):
    conn = conectar()
    c = conn.cursor()
    if request.method == "POST":
        c.execute("""
            UPDATE clientes SET
                nome=%s, telefone=%s, email=%s, cpf_cnpj=%s,
                rua=%s, numero=%s, bairro=%s, cidade=%s,
                cep=%s, observacoes=%s
            WHERE id=%s
        """, (
            request.form.get("nome","").strip(),
            request.form.get("telefone","").strip(),
            request.form.get("email","").strip(),
            request.form.get("cpf_cnpj","").strip(),
            request.form.get("rua","").strip(),
            request.form.get("numero","").strip(),
            request.form.get("bairro","").strip(),
            request.form.get("cidade","").strip(),
            request.form.get("cep","").strip(),
            request.form.get("observacoes","").strip(),
            id
        ))
        conn.commit()
        conn.close()
        return redirect("/clientes")
    c.execute("SELECT * FROM clientes WHERE id=%s", (id,))
    cliente = c.fetchone()
    conn.close()
    return render_template("editar_cliente.html", cliente=cliente)


@clientes_bp.route("/excluir_cliente/<int:id>")
@admin_required
def excluir_cliente(id):
    conn = conectar()
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/clientes")
