from flask import Blueprint, render_template, request, redirect, send_file, session
from database import conectar
from routes.auth_routes import login_required, admin_required
import io

reparo_bp = Blueprint("reparo", __name__)

@reparo_bp.route("/reparo/<int:item_id>", methods=["GET", "POST"])
@login_required
def reparo(item_id):
    conn = conectar()
    c = conn.cursor()
    is_admin = session.get("nivel") == "admin"

    if request.method == "POST":
        solucao       = request.form.get("solucao", "")
        componente_id = request.form.get("componente")
        tipo_id       = request.form.get("tipo_reparo_id")
        qtd_str       = request.form.get("quantidade", "0")
        qtd           = int(qtd_str) if qtd_str.isdigit() else 0
        novo_status   = request.form.get("status_reparo", "reparado")

        c.execute("SELECT garantia FROM itens WHERE id=%s", (item_id,))
        row = c.fetchone()
        eh_garantia = row and (row["garantia"] == 1 or row["garantia"] == "1")

        if eh_garantia or not is_admin:
            valor_cobrado = 0.0
        else:
            valor_str = request.form.get("valor_cobrado", "0").replace(",", ".")
            try:
                valor_cobrado = float(valor_str)
            except ValueError:
                valor_cobrado = 0.0

        c.execute("""
            UPDATE itens SET status=%s, solucao=%s, tipo_reparo_id=%s, valor_cobrado=%s, mac=%s
            WHERE id=%s
        """, (novo_status, solucao, tipo_id or None, valor_cobrado,
              request.form.get("mac", "").strip() or None, item_id))

        if componente_id and qtd > 0 and novo_status == "reparado":
            c.execute("UPDATE componentes SET quantidade = quantidade - %s WHERE id = %s",
                      (qtd, componente_id))

        conn.commit()
        c.execute("SELECT os_id FROM itens WHERE id=%s", (item_id,))
        row = c.fetchone()
        os_id = row["os_id"] if row else None
        conn.close()
        return redirect(f"/itens/{os_id}" if os_id else "/lista_os")

    c.execute("SELECT * FROM itens WHERE id=%s", (item_id,))
    item = c.fetchone()

    c.execute("SELECT * FROM componentes ORDER BY nome")
    componentes = c.fetchall()

    c.execute("SELECT * FROM tipos_reparo ORDER BY nome")
    tipos = c.fetchall()

    conn.close()
    return render_template("reparo.html", componentes=componentes, tipos=tipos,
                           item_id=item_id, item=item, is_admin=is_admin)


@reparo_bp.route("/gerar_pdf_os/<int:os_id>")
@admin_required
def pdf_os(os_id):
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        SELECT os.id, os.data, clientes.nome, clientes.telefone,
               clientes.cpf_cnpj, clientes.email,
               clientes.rua, clientes.numero, clientes.bairro,
               clientes.cidade, clientes.cep
        FROM os JOIN clientes ON os.cliente_id = clientes.id
        WHERE os.id=%s
    """, (os_id,))
    os_data = c.fetchone()

    c.execute("""
        SELECT itens.equipamento, itens.defeito, itens.solucao,
               itens.status, itens.garantia, itens.mac,
               tipos_reparo.nome as tipo_nome, itens.valor_cobrado
        FROM itens
        LEFT JOIN tipos_reparo ON itens.tipo_reparo_id = tipos_reparo.id
        WHERE itens.os_id=%s
    """, (os_id,))
    itens = c.fetchall()

    c.execute("SELECT * FROM os_parciais WHERE os_id=%s ORDER BY data", (os_id,))
    parciais = c.fetchall()
    conn.close()

    from utils.pdf_os import gerar_pdf_os
    pdf_bytes = gerar_pdf_os(os_data, itens, parciais)
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=f"OS_{os_id}.pdf")
