from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from database import conectar
from functools import wraps
from datetime import datetime
import os, base64

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
               SUM(CASE WHEN itens.status = 'reparado' THEN 1 ELSE 0 END) as itens_prontos
        FROM os
        LEFT JOIN itens ON itens.os_id = os.id
        WHERE os.cliente_id = %s AND os.status = 'aberta'
        GROUP BY os.id, os.data, os.status
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_abertas = c.fetchall()

    # OS aguardando pagamento (parciais não pagas — inclui OS fechadas)
    c.execute("""
        SELECT os.id, os.data, os.status,
               COALESCE(SUM(op.valor_cobrado), 0) as valor_pendente,
               COUNT(op.id) as num_parciais
        FROM os
        JOIN os_parciais op ON op.os_id = os.id
        WHERE os.cliente_id = %s AND op.pago = 0
        GROUP BY os.id, os.data, os.status
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_aguardando_pgto = c.fetchall()

    # OS fechadas com tudo pago
    c.execute("""
        SELECT os.id, os.data, os.status,
               COALESCE(SUM(op.valor_cobrado), 0) as valor_total
        FROM os
        LEFT JOIN os_parciais op ON op.os_id = os.id
        WHERE os.cliente_id = %s AND os.status = 'fechada'
          AND NOT EXISTS (
              SELECT 1 FROM os_parciais op2 WHERE op2.os_id = os.id AND op2.pago = 0
          )
        GROUP BY os.id, os.data, os.status
        ORDER BY os.data DESC
    """, (cliente_id,))
    os_fechadas_pagas = c.fetchall()

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
                           os_fechadas_pagas=os_fechadas_pagas,
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




# ─── NOTIFICAÇÃO DE PAGAMENTO (portal) ─────────────────────────────────────

@portal_bp.route("/portal/notificar-pagamento/<int:parcial_id>", methods=["GET", "POST"])
@portal_required
def portal_notificar_pagamento(parcial_id):
    cliente_id = session["portal_cliente_id"]
    conn = conectar()
    c = conn.cursor()

    # Verifica que a parcial pertence a uma OS deste cliente
    c.execute("""
        SELECT op.*, os.id as os_id FROM os_parciais op
        JOIN os ON os.id = op.os_id
        WHERE op.id = %s AND os.cliente_id = %s
    """, (parcial_id, cliente_id))
    parcial = c.fetchone()

    if not parcial:
        conn.close()
        flash("Parcela não encontrada.", "error")
        return redirect(url_for("portal.portal_dashboard"))

    if request.method == "POST":
        observacao = request.form.get("observacao", "").strip()
        comprovante_b64 = None

        f = request.files.get("comprovante")
        if f and f.filename:
            dados = f.read()
            comprovante_b64 = base64.b64encode(dados).decode()

        data_notif = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Salva notificação na tabela
        c.execute("""
            INSERT INTO notificacoes_pagamento (parcial_id, os_id, cliente_id, observacao, comprovante_b64, data)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (parcial_id, parcial["os_id"], cliente_id, observacao or None, comprovante_b64, data_notif))
        conn.commit()
        conn.close()
        flash("Notificação enviada com sucesso! Aguarde a confirmação da equipe.", "success")
        return redirect(url_for("portal.portal_os_detalhe", os_id=parcial["os_id"]))

    conn.close()
    return render_template("portal_notificar_pagamento.html", parcial=parcial)


# ─── ADMIN: VER NOTIFICAÇÕES DE PAGAMENTO ──────────────────────────────────

@portal_bp.route("/notificacoes-pagamento")
def admin_notificacoes_pagamento():
    if not session.get("user"):
        return redirect("/login")
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT np.*, clientes.nome as cliente_nome, op.valor_cobrado, op.descricao as parcial_desc
        FROM notificacoes_pagamento np
        JOIN clientes ON clientes.id = np.cliente_id
        JOIN os_parciais op ON op.id = np.parcial_id
        ORDER BY np.data DESC
    """)
    notificacoes = c.fetchall()
    conn.close()
    return render_template("admin_notificacoes_pagamento.html", notificacoes=notificacoes)


@portal_bp.route("/notificacoes-pagamento/<int:notif_id>/confirmar", methods=["POST"])
def admin_confirmar_pagamento(notif_id):
    if not session.get("user"):
        return redirect("/login")
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT * FROM notificacoes_pagamento WHERE id=%s", (notif_id,))
    notif = c.fetchone()
    if notif:
        c.execute("UPDATE os_parciais SET pago=1 WHERE id=%s", (notif["parcial_id"],))
        c.execute("DELETE FROM notificacoes_pagamento WHERE id=%s", (notif_id,))
        conn.commit()
        flash("Pagamento confirmado.", "success")
    conn.close()
    return redirect(url_for("portal.admin_notificacoes_pagamento"))

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
