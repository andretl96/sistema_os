from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import conectar
from routes.auth_routes import login_required, admin_required
from datetime import datetime

os_bp = Blueprint("os", __name__)


@os_bp.route("/nova_os/<int:cliente_id>")
@login_required
def nova_os(cliente_id):
    conn = conectar()
    c = conn.cursor()
    c.execute(
        "INSERT INTO os (cliente_id, data, status) VALUES (%s, NOW()::text, 'aberta') RETURNING id",
        (cliente_id,)
    )
    os_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return redirect(f"/itens/{os_id}")


@os_bp.route("/itens/<int:os_id>", methods=["GET", "POST"])
@login_required
def itens(os_id):
    conn = conectar()
    c = conn.cursor()

    if request.method == "POST":
        garantia = 1 if request.form.get("garantia") == "sim" else 0
        c.execute("""
        INSERT INTO itens (os_id, equipamento, defeito, garantia, status)
        VALUES (%s, %s, %s, %s, 'aguardando')
        """, (os_id, request.form["equipamento"], request.form["defeito"], garantia))
        conn.commit()

    c.execute("SELECT * FROM itens WHERE os_id=%s", (os_id,))
    itens_lista = c.fetchall()

    c.execute("SELECT status FROM os WHERE id=%s", (os_id,))
    os_row = c.fetchone()
    os_status = os_row["status"] if os_row else "aberta"

    is_admin = session.get("nivel") == "admin"
    conn.close()
    return render_template("itens.html", itens=itens_lista, os_id=os_id,
                           os_status=os_status, is_admin=is_admin)


@os_bp.route("/lista_os")
@login_required
def lista_os():
    conn = conectar()
    c = conn.cursor()
    is_admin = session.get("nivel") == "admin"

    if is_admin:
        c.execute("""
            SELECT os.id, os.data, clientes.nome,
                   COALESCE(SUM(CASE WHEN itens.garantia = 0 THEN itens.valor_cobrado ELSE 0 END), 0) as total,
                   os.status
            FROM os
            JOIN clientes ON os.cliente_id = clientes.id
            LEFT JOIN itens ON itens.os_id = os.id
            GROUP BY os.id, os.data, clientes.nome, os.status
            ORDER BY os.data DESC
        """)
    else:
        c.execute("""
            SELECT os.id, os.data, clientes.nome, NULL as total, os.status
            FROM os
            JOIN clientes ON os.cliente_id = clientes.id
            ORDER BY os.data DESC
        """)

    todas_os = c.fetchall()
    conn.close()
    return render_template("lista_os.html", ordens=todas_os, is_admin=is_admin)


@os_bp.route("/itens/<int:item_id>/editar", methods=["POST"])
@admin_required
def editar_item(item_id):
    conn = conectar()
    c = conn.cursor()
    garantia = 1 if request.form.get("garantia") == "sim" else 0
    mac = request.form.get("mac", "").strip()
    solucao = request.form.get("solucao", "").strip()

    # valor_cobrado: zera se garantia, caso contrário usa o enviado
    if garantia:
        valor_cobrado = 0.0
    else:
        valor_str = request.form.get("valor_cobrado", "0").replace(",", ".")
        try:
            valor_cobrado = float(valor_str)
        except ValueError:
            valor_cobrado = 0.0

    c.execute("""
        UPDATE itens SET equipamento=%s, defeito=%s, mac=%s, garantia=%s,
                         solucao=%s, valor_cobrado=%s
        WHERE id=%s
    """, (
        request.form.get("equipamento", "").strip(),
        request.form.get("defeito", "").strip(),
        mac or None,
        garantia,
        solucao or None,
        valor_cobrado,
        item_id
    ))
    # busca os_id para redirecionar
    c.execute("SELECT os_id FROM itens WHERE id=%s", (item_id,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    flash("Equipamento atualizado.", "success")
    return redirect(url_for("os.itens", os_id=row["os_id"]) if row else url_for("os.lista_os"))


@os_bp.route("/itens/<int:item_id>/deletar", methods=["POST"])
@admin_required
def deletar_item(item_id):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT os_id FROM itens WHERE id=%s", (item_id,))
    row = c.fetchone()
    c.execute("DELETE FROM itens WHERE id=%s", (item_id,))
    conn.commit()
    conn.close()
    flash("Equipamento removido.", "success")
    return redirect(url_for("os.itens", os_id=row["os_id"]) if row else url_for("os.lista_os"))


@os_bp.route("/fechar_os/<int:os_id>", methods=["POST"])
@admin_required
def fechar_os(os_id):
    conn = conectar()
    c = conn.cursor()
    c.execute("UPDATE os SET status='fechada' WHERE id=%s", (os_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("os.lista_os"))


@os_bp.route("/fechar_parcial/<int:os_id>", methods=["GET", "POST"])
@admin_required
def fechar_parcial(os_id):
    conn = conectar()
    c = conn.cursor()

    if request.method == "POST":
        valor = request.form.get("valor_parcial", "0").replace(",", ".")
        try:
            valor = float(valor)
        except ValueError:
            valor = 0.0
        descricao  = request.form.get("descricao", "")
        data_agora = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("""
            INSERT INTO os_parciais (os_id, data, valor_cobrado, pago, descricao)
            VALUES (%s, %s, %s, 0, %s)
        """, (os_id, data_agora, valor, descricao))
        conn.commit()
        conn.close()
        return redirect(url_for("os.itens", os_id=os_id))

    c.execute("SELECT * FROM itens WHERE os_id=%s AND status='reparado'", (os_id,))
    itens_prontos = c.fetchall()

    c.execute("""
        SELECT COALESCE(SUM(CASE WHEN garantia=0 THEN valor_cobrado ELSE 0 END), 0)
        FROM itens WHERE os_id=%s AND status='reparado'
    """, (os_id,))
    row = c.fetchone()
    total_prontos = list(row.values())[0] if row else 0.0

    conn.close()
    return render_template("fechar_parcial.html", os_id=os_id,
                           itens_prontos=itens_prontos, total_prontos=total_prontos)


@os_bp.route("/fechar_os_final/<int:os_id>", methods=["GET", "POST"])
@admin_required
def fechar_os_final(os_id):
    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT * FROM os_parciais WHERE os_id=%s ORDER BY data", (os_id,))
    parciais = c.fetchall()

    total_parciais_nao_pagas = sum(p["valor_cobrado"] for p in parciais if not p["pago"])
    total_parciais_pagas     = sum(p["valor_cobrado"] for p in parciais if p["pago"])

    if request.method == "POST":
        for pid in request.form.getlist("parcial_paga"):
            c.execute("UPDATE os_parciais SET pago=1 WHERE id=%s", (pid,))
        c.execute("UPDATE os SET status='fechada' WHERE id=%s", (os_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("os.lista_os"))

    c.execute("""
        SELECT COALESCE(SUM(CASE WHEN garantia=0 THEN valor_cobrado ELSE 0 END), 0)
        FROM itens WHERE os_id=%s
    """, (os_id,))
    row = c.fetchone()
    total_itens = list(row.values())[0] if row else 0.0

    conn.close()
    return render_template("fechar_os_final.html", os_id=os_id, parciais=parciais,
                           total_itens=total_itens,
                           total_parciais_nao_pagas=total_parciais_nao_pagas,
                           total_parciais_pagas=total_parciais_pagas)
