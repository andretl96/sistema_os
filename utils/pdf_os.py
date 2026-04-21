from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime

EMPRESA_NOME   = "TERRATECH 🌐"
EMPRESA_END    = "Rua São Vicente, 587 — Centro"
EMPRESA_TEL    = "(35) 99822-6258"
EMPRESA_EMAIL  = "terratech.comercial@gmail.com"

COR_PRIMARIA   = colors.HexColor("#f59e0b")
COR_ESCURA     = colors.HexColor("#1a1a1a")
COR_TEXTO      = colors.HexColor("#1f2937")
COR_CINZA      = colors.HexColor("#6b7280")
COR_LINHA      = colors.HexColor("#e5e7eb")
COR_VERDE      = colors.HexColor("#16a34a")
COR_VERMELHO   = colors.HexColor("#dc2626")
COR_ROXO       = colors.HexColor("#7c3aed")
COR_LARANJA    = colors.HexColor("#ea580c")


def _fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _get(row, key, default="—"):
    try:
        val = row[key]
        return val if val is not None else default
    except Exception:
        return default


def _secao_equipamentos(story, titulo, itens_grupo, estilo_normal, estilo_bold, estilo_cabec, secao_titulo, cor_titulo, W):
    if not itens_grupo:
        return

    story.append(Paragraph(titulo, ParagraphStyle(
        "sec_grupo", fontName="Helvetica-Bold", fontSize=9,
        textColor=cor_titulo, spaceBefore=10, spaceAfter=3
    )))

    cab = [
        Paragraph("Equipamento",    estilo_cabec),
        Paragraph("MAC/Série",      estilo_cabec),
        Paragraph("Defeito",        estilo_cabec),
        Paragraph("Serviço / Obs.", estilo_cabec),
        Paragraph("Garantia",       estilo_cabec),
        Paragraph("Valor (R$)",     estilo_cabec),
    ]
    rows = [cab]

    for item in itens_grupo:
        equipamento = str(_get(item, "equipamento"))
        mac_val     = str(_get(item, "mac", ""))
        defeito     = str(_get(item, "defeito"))
        solucao     = str(_get(item, "solucao"))
        garantia    = _get(item, "garantia", 0)
        tipo_nome   = str(_get(item, "tipo_nome"))
        valor       = _get(item, "valor_cobrado", 0.0)
        if valor == "—": valor = 0.0
        if mac_val == "—": mac_val = ""

        eh_garantia = (garantia == 1 or garantia == "1")
        valor_txt = "Garantia" if eh_garantia else _fmt_brl(float(valor))
        cor_val = COR_VERDE if eh_garantia else COR_TEXTO

        obs_parts = []
        if solucao and solucao != "—": obs_parts.append(solucao)
        if tipo_nome and tipo_nome != "—": obs_parts.append(f"[{tipo_nome}]")
        obs_txt = " ".join(obs_parts) if obs_parts else "—"

        mac_display = mac_val if mac_val else "—"
        mac_color   = "#1e40af" if mac_val else "#9ca3af"  # azul se tem, cinza se não tem

        rows.append([
            Paragraph(equipamento, estilo_normal),
            Paragraph(f'<font color="{mac_color}">{mac_display}</font>',
                      ParagraphStyle("mac", fontName="Helvetica", fontSize=8,
                                     textColor=colors.HexColor(mac_color))),
            Paragraph(defeito,     estilo_normal),
            Paragraph(obs_txt,     estilo_normal),
            Paragraph("Sim" if eh_garantia else "Não", estilo_normal),
            Paragraph(f'<font color="#{("16a34a" if eh_garantia else "1f2937")}">{valor_txt}</font>',
                      ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=9, textColor=cor_val)),
        ])

    ti = Table(rows, colWidths=[28*mm, 26*mm, 26*mm, 38*mm, 16*mm, 22*mm])
    ti.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  COR_ESCURA),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
        ("BOX",           (0,0), (-1,-1), 0.5, COR_LINHA),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, COR_LINHA),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ALIGN",         (5,0), (5,-1),  "RIGHT"),
    ]))
    story.append(ti)


def gerar_pdf_os(os_data, itens, parciais=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    estilo_normal = ParagraphStyle("normal", fontName="Helvetica",      fontSize=9,  textColor=COR_TEXTO, leading=13)
    estilo_bold   = ParagraphStyle("bold",   fontName="Helvetica-Bold", fontSize=9,  textColor=COR_TEXTO, leading=13)
    estilo_titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=20, textColor=COR_PRIMARIA)
    estilo_sub    = ParagraphStyle("sub",    fontName="Helvetica",      fontSize=8,  textColor=COR_CINZA)
    estilo_cabec  = ParagraphStyle("cabec",  fontName="Helvetica-Bold", fontSize=8,  textColor=colors.white)
    secao_titulo  = ParagraphStyle("sec",    fontName="Helvetica-Bold", fontSize=9,  textColor=COR_PRIMARIA, spaceBefore=4, spaceAfter=2)

    story = []
    W = 170*mm

    # CABECALHO
    header_data = [[
        Paragraph(f"⚡ {EMPRESA_NOME}", estilo_titulo),
        Paragraph(
            f"{EMPRESA_END}<br/>Tel: {EMPRESA_TEL} &nbsp;·&nbsp; {EMPRESA_EMAIL}",
            ParagraphStyle("emp", fontName="Helvetica", fontSize=8, textColor=COR_CINZA, alignment=TA_RIGHT)
        )
    ]]
    t = Table(header_data, colWidths=[W*0.5, W*0.5])
    t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(t)
    story.append(HRFlowable(width=W, color=COR_PRIMARIA, thickness=2, spaceAfter=6))

    # FAIXA OS
    os_id       = _get(os_data, "id", "?")
    os_data_str = _get(os_data, "data", datetime.now().strftime("%Y-%m-%d %H:%M"))

    faixa = Table([[
        Paragraph(f"ORDEM DE SERVICO  #{os_id}", ParagraphStyle("os", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white)),
        Paragraph(f"Emitida em: {os_data_str}", ParagraphStyle("dt", fontName="Helvetica", fontSize=8, textColor=colors.white, alignment=TA_RIGHT))
    ]], colWidths=[W*0.6, W*0.4])
    faixa.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), COR_ESCURA),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (0,-1),  12),
        ("RIGHTPADDING",  (-1,0), (-1,-1), 12),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(faixa)
    story.append(Spacer(1, 8))

    # DADOS DO CLIENTE
    nome_cli  = str(_get(os_data, "nome"))
    tel_cli   = str(_get(os_data, "telefone"))
    cpf_cli   = str(_get(os_data, "cpf_cnpj"))
    email_cli = str(_get(os_data, "email"))
    rua    = _get(os_data, "rua",    ""); rua    = "" if rua    == "—" else str(rua)
    numero = _get(os_data, "numero", ""); numero = "" if numero == "—" else str(numero)
    bairro = _get(os_data, "bairro", ""); bairro = "" if bairro == "—" else str(bairro)
    cidade = _get(os_data, "cidade", ""); cidade = "" if cidade == "—" else str(cidade)
    cep    = _get(os_data, "cep",    ""); cep    = "" if cep    == "—" else str(cep)

    endereco   = f"{rua}{', '+numero if numero else ''}{', '+bairro if bairro else ''}"
    cidade_cep = f"{cidade}{' — CEP '+cep if cep else ''}"

    story.append(Paragraph("DADOS DO CLIENTE", secao_titulo))
    cli_data = [
        [Paragraph("<b>Nome:</b>",     estilo_bold), Paragraph(nome_cli,         estilo_normal),
         Paragraph("<b>CPF/CNPJ:</b>", estilo_bold), Paragraph(cpf_cli,          estilo_normal)],
        [Paragraph("<b>Telefone:</b>", estilo_bold), Paragraph(tel_cli,          estilo_normal),
         Paragraph("<b>E-mail:</b>",   estilo_bold), Paragraph(email_cli,        estilo_normal)],
        [Paragraph("<b>Endereco:</b>", estilo_bold), Paragraph(endereco or "—",  estilo_normal),
         Paragraph("<b>Cidade:</b>",   estilo_bold), Paragraph(cidade_cep or "—",estilo_normal)],
    ]
    tc = Table(cli_data, colWidths=[22*mm, W*0.35, 22*mm, W*0.30])
    tc.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f9fafb")),
        ("BOX",           (0,0), (-1,-1), 0.5, COR_LINHA),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, COR_LINHA),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tc)
    story.append(Spacer(1, 10))

    # EQUIPAMENTOS POR GRUPO
    grupos = {"reparado": [], "aguardando_componente": [], "nao_passivel": [], "aguardando": []}
    for item in itens:
        status = _get(item, "status", "aguardando")
        if status == "—": status = "aguardando"
        grupos.setdefault(status if status in grupos else "aguardando", []).append(item)

    config_grupos = [
        ("reparado",              "REPARADOS",              COR_VERDE),
        ("aguardando_componente", "AGUARDANDO COMPONENTE",  COR_ROXO),
        ("nao_passivel",          "NAO PASSIVEL DE REPARO", COR_VERMELHO),
        ("aguardando",            "AGUARDANDO REPARO",      COR_LARANJA),
    ]

    story.append(Paragraph("EQUIPAMENTOS / SERVICOS", secao_titulo))
    algum_grupo = False
    for chave, label, cor in config_grupos:
        if grupos.get(chave):
            algum_grupo = True
            _secao_equipamentos(story, label, grupos[chave],
                                estilo_normal, estilo_bold, estilo_cabec, secao_titulo, cor, W)
    if not algum_grupo:
        story.append(Paragraph("Nenhum equipamento registrado.", estilo_normal))
    story.append(Spacer(1, 10))

    # TOTAIS
    total_geral = 0.0
    for item in itens:
        garantia = _get(item, "garantia", 0)
        if not (garantia == 1 or garantia == "1"):
            val = _get(item, "valor_cobrado", 0.0)
            try: total_geral += float(val) if val != "—" else 0.0
            except: pass

    total_parciais_pagas     = 0.0
    total_parciais_nao_pagas = 0.0
    if parciais:
        for p in parciais:
            try:
                val  = float(_get(p, "valor_cobrado", 0.0))
                pago = _get(p, "pago", 0)
                if pago: total_parciais_pagas += val
                else:    total_parciais_nao_pagas += val
            except: pass

    total_a_cobrar = max(0.0, total_geral - total_parciais_pagas)

    total_rows = [[
        Paragraph("TOTAL DOS SERVICOS:", ParagraphStyle("vt", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph(_fmt_brl(total_geral),  ParagraphStyle("vtv", fontName="Helvetica-Bold", fontSize=13, textColor=COR_PRIMARIA, alignment=TA_RIGHT))
    ]]
    if total_parciais_pagas > 0:
        total_rows.append([
            Paragraph("Parciais ja recebidas:", ParagraphStyle("vp", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#86efac"), alignment=TA_RIGHT)),
            Paragraph(f"- {_fmt_brl(total_parciais_pagas)}", ParagraphStyle("vpv", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#86efac"), alignment=TA_RIGHT))
        ])
    if total_parciais_nao_pagas > 0:
        total_rows.append([
            Paragraph("Parciais entregues (pagto pendente):", ParagraphStyle("vpn", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#fbbf24"), alignment=TA_RIGHT)),
            Paragraph(_fmt_brl(total_parciais_nao_pagas), ParagraphStyle("vpnv", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#fbbf24"), alignment=TA_RIGHT))
        ])
    total_rows.append([
        Paragraph("VALOR A COBRAR AGORA:", ParagraphStyle("vfin", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph(_fmt_brl(total_a_cobrar), ParagraphStyle("vfinv", fontName="Helvetica-Bold", fontSize=15, textColor=COR_PRIMARIA, alignment=TA_RIGHT))
    ])

    total_tab = Table(total_rows, colWidths=[W*0.7, W*0.3])
    total_tab.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), COR_ESCURA),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(total_tab)
    story.append(Spacer(1, 12))

    # HISTORICO DE PARCIAIS
    if parciais:
        story.append(Paragraph("HISTORICO DE ENTREGAS PARCIAIS", secao_titulo))
        parc_rows = [[
            Paragraph("Data",      estilo_cabec),
            Paragraph("Descricao", estilo_cabec),
            Paragraph("Valor",     estilo_cabec),
            Paragraph("Situacao",  estilo_cabec),
        ]]
        for p in parciais:
            try:
                data_p = str(_get(p, "data"))
                val_p  = float(_get(p, "valor_cobrado", 0.0))
                pago_p = _get(p, "pago", 0)
                desc_p = str(_get(p, "descricao"))
            except: continue
            situacao = "Pago" if pago_p else "Pendente"
            cor_sit  = "#16a34a" if pago_p else "#f59e0b"
            parc_rows.append([
                Paragraph(data_p, estilo_normal),
                Paragraph(desc_p, estilo_normal),
                Paragraph(_fmt_brl(val_p), ParagraphStyle("pv", fontName="Helvetica-Bold", fontSize=9, textColor=COR_TEXTO)),
                Paragraph(f'<font color="{cor_sit}">{situacao}</font>', estilo_normal),
            ])
        tp = Table(parc_rows, colWidths=[32*mm, 80*mm, 28*mm, 30*mm])
        tp.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  COR_ESCURA),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
            ("BOX",           (0,0), (-1,-1), 0.5, COR_LINHA),
            ("INNERGRID",     (0,0), (-1,-1), 0.3, COR_LINHA),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tp)
        story.append(Spacer(1, 12))

    # ASSINATURA
    ass = Table([[
        Table([[Paragraph("_" * 40, estilo_normal)],
               [Paragraph("Assinatura do Cliente", estilo_sub)]], colWidths=[W*0.45]),
        Table([[Paragraph("_" * 40, estilo_normal)],
               [Paragraph("Responsavel Tecnico", estilo_sub)]], colWidths=[W*0.45]),
    ]], colWidths=[W*0.5, W*0.5])
    story.append(ass)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width=W, color=COR_LINHA, thickness=0.5))
    story.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')} — {EMPRESA_NOME}",
        ParagraphStyle("rodape", fontName="Helvetica", fontSize=7, textColor=COR_CINZA, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
