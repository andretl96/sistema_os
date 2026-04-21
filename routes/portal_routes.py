from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from database import conectar
from functools import wraps
from datetime import datetime

portal_bp = Blueprint("portal", __name__)


# ─── DECORATOR PORTAL ───────────────────────────────────────────────────────

def portal_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("portal_cliente_id"):
            return redirect(url_for("portal.portal_login"))
        return f(*args, **kwargs)
    return decorated


# ─── LOGIN DO PORTAL ────────────────────────────────────────────────────────

@portal_bp.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    if request.method == "POST":
        cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if not cpf_cnpj or not telefone:
            flash("Preencha CPF/CNPJ e telefone.", "error")
            return render_template("portal_login.html")

        conn = conectar()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM clientes WHERE cpf_cnpj = %s AND telefone = %s",
            (cpf_cnpj, telefone)
        )
        cliente = c.fetchone()
        conn.close()

        if cliente:
            session["portal_cliente_id"] = cliente["id"]
            session["portal_cliente_nome"] = cliente["nome"]
            return redirect(url_for("portal.portal_dashboard"))
        else:
            flash("CPF/CNPJ ou telefone incorretos. Verifique com a assistência.", "error")

    return render_template("portal_login.html")


@portal_bp.route("/portal/logout")
def portal_logout():
    session.pop("portal_cliente_id", None)
    session.pop("portal_cliente_nome", None)
    return redirect(url_for("portal.portal_login"))


# ─── DASHBOARD DO PORTAL ────────────────────────────────────────────────────

@portal_bp.route("/portal")
@portal_required
def portal_dashboard():
    cliente_id = session["portal_cliente_id"]
    conn = conectar()
    c = conn.cursor()

    # OS em aberto
    c.execute("""
        SELECT os.id, os.data, os.status,
               COUNT(itens.id) as total_itens,
               SUM(CASE WHEN itens.status = 'reparado' THEN 1 ELSE 0 END) as itens_prontos,
               SUM(CASE WHEN itens.status = 'aguardando' THEN 1 ELSE 0 END) as itens_aguardando
        FROM os
        LEFT JOIN itens ON itens.os_id = os.id
        WHERE os.cliente_id = %s AND os.status = 'aberta'
        GROUP BY os.id, os.data, os.status
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_abertas = c.fetchall()

    # OS aguardando pagamento (parciais não pagas)
    c.execute("""
        SELECT os.id, os.data, os.status,
               COALESCE(SUM(op.valor_cobrado), 0) as valor_pendente,
               COUNT(op.id) as num_parciais
        FROM os
        JOIN os_parciais op ON op.os_id = os.id
        WHERE os.cliente_id = %s AND op.pago = 0 AND os.status != 'fechada'
        GROUP BY os.id, os.data, os.status
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_aguardando_pgto = c.fetchall()

    # OS com pagamento parcial (tem parciais pagas E não pagas)
    c.execute("""
        SELECT os.id, os.data, os.status,
               COALESCE(SUM(CASE WHEN op.pago = 1 THEN op.valor_cobrado ELSE 0 END), 0) as valor_pago,
               COALESCE(SUM(CASE WHEN op.pago = 0 THEN op.valor_cobrado ELSE 0 END), 0) as valor_pendente
        FROM os
        JOIN os_parciais op ON op.os_id = os.id
        WHERE os.cliente_id = %s
        GROUP BY os.id, os.data, os.status
        HAVING SUM(CASE WHEN op.pago = 1 THEN 1 ELSE 0 END) > 0
           AND SUM(CASE WHEN op.pago = 0 THEN 1 ELSE 0 END) > 0
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_parciais = c.fetchall()

    # Total de chamados abertos
    c.execute("""
        SELECT COUNT(*) as total FROM chamados
        WHERE cliente_id = %s AND status = 'aberto'
    """, (cliente_id,))
    row = c.fetchone()
    chamados_abertos = row["total"] if row else 0

    conn.close()
    return render_template("portal_dashboard.html",
                           os_abertas=os_abertas,
                           os_aguardando_pgto=os_aguardando_pgto,
                           os_parciais=os_parciais,
                           chamados_abertos=chamados_abertos)


# ─── DETALHE DA OS (portal) ─────────────────────────────────────────────────

@portal_bp.route("/portal/os/<int:os_id>")
@portal_required
def portal_os_detalhe(os_id):
    cliente_id = session["portal_cliente_id"]
    conn = conectar()
    c = conn.cursor()

    # Verifica que a OS pertence ao cliente logado
    c.execute("SELECT * FROM os WHERE id = %s AND cliente_id = %s", (os_id, cliente_id))
    os_row = c.fetchone()
    if not os_row:
        conn.close()
        flash("OS não encontrada.", "error")
        return redirect(url_for("portal.portal_dashboard"))

    c.execute("SELECT * FROM itens WHERE os_id = %s", (os_id,))
    itens = c.fetchall()

    c.execute("SELECT * FROM os_parciais WHERE os_id = %s ORDER BY data", (os_id,))
    parciais = c.fetchall()

    conn.close()
    return render_template("portal_os_detalhe.html", os=os_row, itens=itens, parciais=parciais)


# ─── CHAMADOS ───────────────────────────────────────────────────────────────

@portal_bp.route("/portal/chamados")
@portal_required
def portal_chamados():
    cliente_id = session["portal_cliente_id"]
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM chamados WHERE cliente_id = %s ORDER BY data_abertura DESC
    """, (cliente_id,))
    chamados = c.fetchall()
    conn.close()
    return render_template("portal_chamados.html", chamados=chamados)


@portal_bp.route("/portal/chamados/novo", methods=["GET", "POST"])
@portal_required
def portal_novo_chamado():
    cliente_id = session["portal_cliente_id"]

    if request.method == "POST":
        assunto = request.form.get("assunto", "").strip()
        mensagem = request.form.get("mensagem", "").strip()
        prioridade = request.form.get("prioridade", "normal")

        if not assunto or not mensagem:
            flash("Preencha assunto e mensagem.", "error")
            return render_template("portal_novo_chamado.html")

        conn = conectar()
        c = conn.cursor()
        c.execute("""
            INSERT INTO chamados (cliente_id, assunto, mensagem, prioridade, status, data_abertura)
            VALUES (%s, %s, %s, %s, 'aberto', %s)
        """, (cliente_id, assunto, mensagem, prioridade, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        flash("Chamado aberto com sucesso! Nossa equipe entrará em contato.", "success")
        return redirect(url_for("portal.portal_chamados"))

    return render_template("portal_novo_chamado.html")


# ─── GERENCIAMENTO DE CHAMADOS (admin) ──────────────────────────────────────

@portal_bp.route("/chamados/admin")
def admin_chamados():
    from routes.auth_routes import login_required
    if not session.get("user"):
        return redirect("/login")
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT chamados.*, clientes.nome as cliente_nome
        FROM chamados
        JOIN clientes ON chamados.cliente_id = clientes.id
        ORDER BY
            CASE WHEN chamados.status = 'aberto' THEN 0 ELSE 1 END,
            CASE WHEN chamados.prioridade = 'urgente' THEN 0
                 WHEN chamados.prioridade = 'alta' THEN 1
                 ELSE 2 END,
            chamados.data_abertura DESC
    """)
    chamados = c.fetchall()
    conn.close()
    return render_template("admin_chamados.html", chamados=chamados)


@portal_bp.route("/chamados/admin/<int:chamado_id>/responder", methods=["POST"])
def admin_responder_chamado(chamado_id):
    if not session.get("user"):
        return redirect("/login")
    resposta = request.form.get("resposta", "").strip()
    status = request.form.get("status", "aberto")
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        UPDATE chamados SET resposta = %s, status = %s, data_resposta = %s WHERE id = %s
    """, (resposta, status, datetime.now().strftime("%Y-%m-%d %H:%M"), chamado_id))
    conn.commit()
    conn.close()
    flash("Chamado atualizado.", "success")
    return redirect(url_for("portal.admin_chamados"))
