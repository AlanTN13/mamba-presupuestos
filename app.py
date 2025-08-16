# app.py
from __future__ import annotations
import io
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)

# -------------------- Config --------------------
st.set_page_config(
    page_title="Generador de Presupuestos",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- Estilos (azul único + hover amarillo) --------------------
st.markdown("""
<style>
:root{
  --primary:#000033;   /* Único azul */
  --accent:#ffcc00;    /* Hover amarillo */
  --bg:#ffffff;
  --text:#1f2430;
  --muted:#6b7280;
  --radius:14px;
  --shadow:0 6px 18px rgba(0,0,0,.08);
}
html, body, .stApp { background: var(--bg) !important; color: var(--text) !important; }
.block-container { padding-top: 2rem !important; }
h1,h2,h3,h4,h5,h6 { color: var(--primary) !important; font-weight:800 !important; }

.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
  border:1.3px solid var(--primary) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  background:#fff !important;
}

.stButton>button, .stDownloadButton>button {
  background: var(--primary) !important;
  color: #fff !important;
  font-weight: 700 !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  border: 0 !important;
}
.stButton>button:hover, .stDownloadButton>button:hover {
  background: var(--accent) !important;
  color: var(--primary) !important;
}

div[data-testid="stNumberInput"] button {
  background: var(--primary) !important;
  color: #fff !important;
  border: 0 !important;
  border-radius: 10px !important;
}
div[data-testid="stNumberInput"] button:hover {
  background: var(--accent) !important;
  color: var(--primary) !important;
}
[data-testid="stMetricValue"] { color: var(--primary) !important; }
</style>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
CURRENCY = "$"  # estilo Word

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"

LOGO_CANDIDATES = [
    ASSETS_DIR / "logo.png",
    ASSETS_DIR / "logo.jpg",
    ASSETS_DIR / "logo.jpeg",
    BASE_DIR / "logo.png",
    BASE_DIR / "logo.jpg",
    BASE_DIR / "Imagen 1.jpg",
]

def find_logo_path() -> Path | None:
    for p in LOGO_CANDIDATES:
        if p.exists():
            return p
    return None

def money(x: float) -> str:
    try:
        return f"{CURRENCY} {x:,.2f}"  # 1,234,567.89
    except Exception:
        return f"{CURRENCY} 0.00"

def fecha_larga(d: date) -> str:
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    return f"{meses[d.month-1].capitalize()} {d.day}, {d.year}"

# evitar choque con .items()
DEFAULT_ITEMS = [
    {"descripcion": "Taza Lucky de porcelana eléctrica con calentador", "cantidad": 20, "precio": 18999.0},
    {"descripcion": "Vaso térmico con sensor de temperatura digital", "cantidad": 20, "precio": 13999.0},
]
if "line_items" not in st.session_state:
    st.session_state["line_items"] = DEFAULT_ITEMS.copy()

# -------------------- Encabezado --------------------
st.title("🧾 Generador de Presupuestos")
st.caption("Completar → revisar → generar PDF")

colA, colB, colC, colD = st.columns((1, 1, 1, 1))
with colA:
    empresa = st.text_input("Tu negocio / marca", value="Mamba Shop")
    nro = st.text_input("N° de presupuesto", value="101")
with colB:
    cliente = st.text_input("Cotización para (cliente)", value="Milena")
    fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
with colC:
    vencimiento = st.date_input("Fecha de vencimiento", value=date.today() + timedelta(days=7), format="DD/MM/YYYY")
    pago = st.text_input("Condiciones de pago", value="Transferencia Bancaria, Mercado Pago o Efectivo")
with colD:
    descuento_pct = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
    impuesto_pct = st.number_input("Impuesto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

st.markdown("---")

# -------------------- Ítems --------------------
st.subheader("Ítems")

def render_item(i: int, item: dict):
    st.markdown(f"**Ítem {i+1}**")
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        item["descripcion"] = st.text_input("Descripción", value=item.get("descripcion", ""), key=f"desc_{i}")
    with c2:
        item["cantidad"] = st.number_input("Cantidad", min_value=0, value=int(item.get("cantidad", 0)), step=1, key=f"cant_{i}")
    with c3:
        item["precio"] = st.number_input("Precio unitario", min_value=0.0, value=float(item.get("precio", 0.0)), step=100.0, key=f"prec_{i}")
    if st.button("🗑️ Eliminar ítem", key=f"del_{i}"):
        st.session_state["line_items"].pop(i)
        st.rerun()

for idx in range(len(st.session_state["line_items"])):
    try:
        card = st.container(border=True)
    except TypeError:
        card = st.container()
    with card:
        render_item(idx, st.session_state["line_items"][idx])

c_add, c_clear = st.columns(2)
with c_add:
    if st.button("➕ Agregar ítem", type="secondary", use_container_width=True):
        st.session_state["line_items"].append({"descripcion": "", "cantidad": 1, "precio": 0.0})
        st.rerun()
with c_clear:
    if st.button("🧹 Vaciar ítems", use_container_width=True):
        st.session_state["line_items"] = []
        st.rerun()

# -------------------- Resumen (tabla HTML con components) --------------------
if st.session_state["line_items"]:
    df = pd.DataFrame(st.session_state["line_items"]).fillna({"cantidad": 0, "precio": 0.0})
    df["monto"] = df["cantidad"] * df["precio"]
else:
    df = pd.DataFrame(columns=["descripcion", "cantidad", "precio", "monto"])

def render_summary_table(df: pd.DataFrame):
    rows_html = ""
    for _, r in df.iterrows():
        rows_html += f"""
          <tr>
            <td>{str(r.get('descripcion',''))}</td>
            <td class="num">{int(r.get('cantidad',0))}</td>
            <td class="num">{money(float(r.get('precio',0.0)))}</td>
            <td class="num">{money(float(r.get('monto',0.0)))}</td>
          </tr>
        """
    if not rows_html:
        rows_html = '<tr><td colspan="4" class="empty">Sin ítems</td></tr>'

    html = f"""
    <html><head><style>
      :root {{ --primary:#000033; --text:#1f2430; --radius:14px; --shadow:0 6px 18px rgba(0,0,0,.08); }}
      body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color:var(--text); }}
      .table-wrap {{ border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; border: 1px solid #e9edf3; margin: 2px; }}
      table.presu {{ width: 100%; border-collapse: collapse; background: #fff; }}
      thead th {{ background:#000033; color:#fff; text-align: left; padding: 12px 14px; font-weight:700; }}
      tbody td {{ padding: 10px 14px; border-bottom: 1px solid #eef1f6; }}
      tbody tr:last-child td {{ border-bottom: 0; }}
      td.num {{ text-align:right; white-space: nowrap; }}
      td.empty {{ text-align:center; color:#888; padding:14px; }}
    </style></head>
    <body><div class="table-wrap">
      <table class="presu">
        <thead><tr><th>Descripción</th><th>Cantidad</th><th>Precio unitario</th><th>Monto</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table></div></body></html>
    """
    height = 120 + max(1, len(df)) * 44
    components.html(html, height=height, scrolling=False)

render_summary_table(df)

# -------------------- Totales --------------------
subtotal = float(df["monto"].sum()) if not df.empty else 0.0
descuento = subtotal * (descuento_pct / 100.0)
base = subtotal - descuento
impuesto = base * (impuesto_pct / 100.0)
TOTAL = base + impuesto

r1, r2, r3, r4 = st.columns(4)
r1.metric("Subtotal", money(subtotal))
r2.metric(f"Descuento ({descuento_pct:.1f}%)", money(descuento))
r3.metric(f"Impuesto ({impuesto_pct:.1f}%)", money(impuesto))
r4.metric("TOTAL", money(TOTAL))

st.markdown("---")

notas = st.text_area(
    "Notas",
    value=(
        "Este presupuesto fue elaborado según los productos y cantidades solicitadas.\n"
        "Los colores y modelos pueden variar según disponibilidad de stock.\n"
        "Los precios informados no incluyen IVA."
    ),
    height=120,
)
terminos = st.text_area(
    "Términos",
    value=(
        "Formas de pago: Transferencia, Mercado Pago o efectivo.\n"
        "Entrega: dentro de 5 días hábiles desde la confirmación del pago.\n"
        "Validez: 7 días desde la emisión."
    ),
    height=120,
)

# -------------------- PDF (ajustes visuales) --------------------
def build_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title=f"Presupuesto_{nro}",
    )

    styles = getSampleStyleSheet()

    azul = colors.HexColor("#000033")
    gris_h1 = colors.HexColor("#333333")
    gris_txt = colors.HexColor("#666666")
    gris_header = colors.HexColor("#6e6e6e")
    gris_rowline = colors.HexColor("#e6e6e6")
    gris_box = colors.whitesmoke

    # Estilos
    if "TitleMain" not in styles:
        styles.add(ParagraphStyle("TitleMain", fontName="Helvetica-Bold",
                                  fontSize=28, leading=32, textColor=gris_h1,
                                  alignment=TA_CENTER, spaceAfter=6))
    if "MetaRight" not in styles:
        styles.add(ParagraphStyle("MetaRight", fontName="Helvetica",
                                  fontSize=10.5, leading=14, textColor=gris_txt,
                                  alignment=TA_RIGHT))
    if "MetaKVLabel" not in styles:
        styles.add(ParagraphStyle("MetaKVLabel", fontName="Helvetica-Bold",
                                  fontSize=10.5, leading=14, textColor=gris_txt,
                                  alignment=TA_RIGHT))
    if "MetaKVValue" not in styles:
        styles.add(ParagraphStyle("MetaKVValue", fontName="Helvetica",
                                  fontSize=10.5, leading=14, textColor=gris_h1,
                                  alignment=TA_LEFT))
    if "LabelLeft" not in styles:
        styles.add(ParagraphStyle("LabelLeft", fontName="Helvetica",
                                  fontSize=11, leading=14, textColor=gris_txt))
    if "LabelBold" not in styles:
        styles.add(ParagraphStyle("LabelBold", fontName="Helvetica-Bold",
                                  fontSize=11, leading=14, textColor=gris_h1))
    if "H2Muted" not in styles:
        styles.add(ParagraphStyle("H2Muted", fontName="Helvetica-Bold",
                                  fontSize=11, leading=14, textColor=gris_txt))
    if "TotalsLabel" not in styles:
        styles.add(ParagraphStyle("TotalsLabel", fontName="Helvetica",
                                  fontSize=11, leading=14, textColor=gris_txt, alignment=TA_RIGHT))
    if "TotalsValue" not in styles:
        styles.add(ParagraphStyle("TotalsValue", fontName="Helvetica",
                                  fontSize=11, leading=14, alignment=TA_RIGHT))
    if "TotalsGrand" not in styles:
        styles.add(ParagraphStyle("TotalsGrand", fontName="Helvetica-Bold",
                                  fontSize=12.5, leading=16, alignment=TA_RIGHT))

    story = []

    # -------- Cabecera: Logo + bloque derecho en caja + TOTAL destacado -------
    title_par = Paragraph(f"Presupuesto: #{nro}", styles["TitleMain"])

    # Mini-caja con metadatos prolija
    meta_table = Table([
        [Paragraph("Fecha:", styles["MetaKVLabel"]),        Paragraph(fecha_larga(fecha), styles["MetaKVValue"])],
        [Paragraph("Condiciones de pago:", styles["MetaKVLabel"]), Paragraph(pago, styles["MetaKVValue"])],
        [Paragraph("Vencimiento:", styles["MetaKVLabel"]),  Paragraph(fecha_larga(vencimiento), styles["MetaKVValue"])],
    ], colWidths=[42*mm, 73*mm])
    meta_card = Table([[meta_table]], colWidths=[115*mm])
    meta_card.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, gris_rowline),
        ("BACKGROUND", (0,0), (-1,-1), gris_box),
        ("INNERGRID", (0,0), (-1,-1), 0.5, gris_rowline),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))

    # Badge de TOTAL grande arriba a la derecha
    total_badge = Table(
        [[Paragraph("TOTAL", styles["H2Muted"]), Paragraph(money(TOTAL), styles["TotalsGrand"])]],
        colWidths=[22*mm, 44*mm]
    )
    total_badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("BOX", (0,0), (-1,-1), 0.6, gris_rowline),
        ("RIGHTPADDING", (1,0), (1,0), 6),
        ("LEFTPADDING", (0,0), (0,0), 6),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    right_block = Table([[title_par], [meta_card], [Spacer(1, 4*mm)], [total_badge]], colWidths=[115*mm])
    right_block.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "RIGHT")]))

    # Logo (más chico)
    logo_path = find_logo_path()
    if logo_path:
        with open(logo_path, "rb") as f:
            logo = Image(io.BytesIO(f.read()), width=45*mm, height=45*mm)
    else:
        logo = Paragraph(f"<font color='{azul}'><b>{empresa}</b></font>", styles["LabelBold"])

    header_tbl = Table([[logo, right_block]], colWidths=[60*mm, None])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [header_tbl, Spacer(1, 8*mm)]

    # -------- Cotización para --------
    story += [
        Paragraph("Cotización para:", styles["LabelLeft"]),
        Paragraph(f"<b>{cliente}</b>", styles["LabelBold"]),
        Spacer(1, 6*mm)
    ]

    # -------- Tabla de productos "más linda" --------
    table_data = [["Artículos", "Cantidad", "Valor unitario", "Monto total"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row.get("descripcion", "")),
            int(row.get("cantidad", 0)),
            money(float(row.get("precio", 0.0))),
            money(float(row.get("monto", 0.0))),
        ])

    items_tbl = Table(table_data, colWidths=[95*mm, 25*mm, 35*mm, 35*mm])
    items_tbl.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), gris_header),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (1, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),

        # Zebra rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fb")]),

        # Tipografía & alineación cuerpo
        ("FONTSIZE", (0, 1), (-1, -1), 10.5),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),

        # Bordes suaves + caja exterior
        ("GRID", (0, 1), (-1, -1), 0.25, gris_rowline),
        ("LINEBELOW", (0, 0), (-1, 0), 0.25, gris_rowline),
        ("BOX", (0, 0), (-1, -1), 0.5, gris_rowline),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    story += [items_tbl, Spacer(1, 10*mm)]

    # -------- Totales (final) --------
    sb = float(df["monto"].sum()) if not df.empty else 0.0
    disc = sb * (descuento_pct / 100.0)
    base_local = sb - disc
    tax = base_local * (impuesto_pct / 100.0)
    total_local = base_local + tax

    totals_tbl = Table([
        [Paragraph("Subtotal:", styles["TotalsLabel"]), Paragraph(money(sb), styles["TotalsValue"])],
        [Paragraph(f"Descuento ({descuento_pct:.1f}%):", styles["TotalsLabel"]), Paragraph(money(disc), styles["TotalsValue"])],
        [Paragraph(f"Impuesto ({impuesto_pct:.1f}%):", styles["TotalsLabel"]), Paragraph(money(tax), styles["TotalsValue"])],
        [Paragraph("Total:", styles["TotalsLabel"]), Paragraph(money(total_local), styles["TotalsGrand"])],
    ], colWidths=[120*mm, 35*mm])

    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [Table([[Spacer(1,0), totals_tbl]], colWidths=[110*mm, 45*mm]), Spacer(1, 10*mm)]

    # -------- Notas y Términos --------
    story += [
        Paragraph("Notas:", styles["H2Muted"]),
        Paragraph(notas.replace("\n", "<br/>"), styles["LabelLeft"]),
        Spacer(1, 4*mm),
        Paragraph("Términos:", styles["H2Muted"]),
        Paragraph(terminos.replace("\n", "<br/>"), styles["LabelLeft"]),
    ]

    doc.build(story)
    out = buffer.getvalue()
    buffer.close()
    return out

# -------------------- Acciones --------------------
col_btn, _ = st.columns([1, 3])
with col_btn:
    if st.button("📄 Generar PDF", type="primary"):
        pdf = build_pdf()
        st.session_state["_last_pdf"] = pdf
        st.success("¡PDF generado!")

if "_last_pdf" in st.session_state:
    st.download_button(
        label=f"⬇️ Descargar Presupuesto #{nro}.pdf",
        data=st.session_state["_last_pdf"],
        file_name=f"Presupuesto_{nro}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

# CSV
csv = (
    df.rename(columns={"descripcion": "Descripción", "cantidad": "Cantidad", "precio": "Precio unitario", "monto": "Monto"})
      .to_csv(index=False).encode("utf-8")
)
st.download_button("Descargar ítems (CSV)", data=csv, file_name=f"items_{nro}.csv", mime="text/csv")
