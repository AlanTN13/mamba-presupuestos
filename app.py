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
from reportlab.lib.enums import TA_RIGHT
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
  --accent:#ffcc00;    /* Amarillo hover */
  --bg:#ffffff;
  --text:#1f2430;
  --muted:#6b7280;
  --radius:14px;
  --shadow:0 6px 18px rgba(0,0,0,.08);
}

/* Fondo y tipografía */
html, body, .stApp { background: var(--bg) !important; color: var(--text) !important; }
.block-container { padding-top: 2rem !important; }

/* Títulos */
h1,h2,h3,h4,h5,h6 { color: var(--primary) !important; font-weight:800 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
  border:1.3px solid var(--primary) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  background:#fff !important;
}

/* Botones principales y de descarga */
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

/* Botones + / - del number_input */
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

/* Métricas */
[data-testid="stMetricValue"] { color: var(--primary) !important; }
</style>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
CURRENCY = "ARS"
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"

# buscamos automáticamente el logo
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
        return f"{CURRENCY} {x:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return f"{CURRENCY} 0,00"

# evitar choque con .items()
DEFAULT_ITEMS = [
    {"descripcion": "Taza Lucky de porcelana eléctrica con calentador", "cantidad": 1, "precio": 18999.0},
    {"descripcion": "Vaso térmico con sensor de temperatura digital", "cantidad": 1, "precio": 13999.0},
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
    <html>
    <head>
      <style>
        :root {{
          --primary:#000033;
          --text:#1f2430;
          --radius:14px;
          --shadow:0 6px 18px rgba(0,0,0,.08);
        }}
        body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color:var(--text); }}
        .table-wrap {{
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          overflow: hidden;
          border: 1px solid #e9edf3;
          margin: 2px;
        }}
        table.presu {{
          width: 100%;
          border-collapse: collapse;
          background: #fff;
        }}
        table.presu thead th {{
          background: var(--primary);
          color: #fff;
          text-align: left;
          padding: 12px 14px;
          font-weight: 700;
        }}
        table.presu tbody td {{
          padding: 10px 14px;
          border-bottom: 1px solid #eef1f6;
        }}
        table.presu tbody tr:last-child td {{ border-bottom: 0; }}
        td.num {{ text-align:right; white-space: nowrap; }}
        td.empty {{ text-align:center; color:#888; padding:14px; }}
      </style>
    </head>
    <body>
      <div class="table-wrap">
        <table class="presu">
          <thead>
            <tr>
              <th>Descripción</th>
              <th>Cantidad</th>
              <th>Precio unitario</th>
              <th>Monto</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </body>
    </html>
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

# -------------------- PDF --------------------
def build_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Presupuesto_{nro}",
    )

    styles = getSampleStyleSheet()
    if "H1X" not in styles:
        styles.add(ParagraphStyle(name="H1X", fontSize=18, leading=22, spaceAfter=6, textColor=colors.HexColor("#000033")))
    if "H2X" not in styles:
        styles.add(ParagraphStyle(name="H2X", fontSize=12, leading=15, textColor=colors.grey))
    if "RightX" not in styles:
        styles.add(ParagraphStyle(name="RightX", alignment=TA_RIGHT))
    if "TitleBadge" not in styles:
        styles.add(ParagraphStyle(name="TitleBadge", fontSize=28, leading=30,
                                  backColor=colors.HexColor("#000033"), textColor=colors.white,
                                  alignment=TA_RIGHT, spaceAfter=6))
    if "HashNum" not in styles:
        styles.add(ParagraphStyle(name="HashNum", fontSize=12, textColor=colors.grey, alignment=TA_RIGHT))
    if "TotalBox" not in styles:
        styles.add(ParagraphStyle(name="TotalBox", fontSize=14, alignment=TA_RIGHT))

    story = []

    # fila superior: logo izq + título a la derecha
    left_cells = []
    logo_path = find_logo_path()
    if logo_path:
        with open(logo_path, "rb") as f:
            left_cells.append(Image(io.BytesIO(f.read()), width=60 * mm, height=60 * mm))
    else:
        left_cells.append(Paragraph(f"<b>{empresa}</b>", styles["H1X"]))

    right_cells = [
        Paragraph("Presupuesto", styles["TitleBadge"]),
        Paragraph(f"# {nro}", styles["HashNum"]),
        Spacer(1, 2 * mm),
    ]

    header_top = Table([[Table([[x] for x in left_cells], colWidths=[80 * mm]),
                         Table([[x] for x in right_cells], colWidths=[80 * mm])]],
                       colWidths=[95 * mm, 75 * mm])
    header_top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [header_top, Spacer(1, 4 * mm)]

    # empresa/cliente + datos
    left_info = [
        Paragraph(f"<b>{empresa}</b>", styles["H1X"]),
        Spacer(1, 1 * mm),
        Paragraph("Cotización para:", styles["H2X"]),
        Paragraph(f"<b>{cliente}</b>", styles["Normal"]),
    ]
    right_info = [
        Paragraph(f"Fecha: {fecha.strftime('%d/%m/%Y')}", styles["RightX"]),
        Paragraph(f"Condiciones de pago: {pago}", styles["RightX"]),
        Paragraph(f"Fecha de vencimiento: {vencimiento.strftime('%d/%m/%Y')}", styles["RightX"]),
    ]
    header_mid = Table([[Table([[x] for x in left_info], colWidths=[90 * mm]),
                         Table([[x] for x in right_info], colWidths=[80 * mm])]],
                       colWidths=[95 * mm, 75 * mm])
    header_mid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [header_mid, Spacer(1, 3 * mm)]

    # Total destacado
    total_tbl = Table(
        [[Paragraph("TOTAL", styles["H2X"]), Paragraph(money(TOTAL), styles["TotalBox"])]],
        colWidths=[20 * mm, 60 * mm]
    )
    total_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), colors.whitesmoke),
        ("BOX", (0, 0), (1, 0), 0.5, colors.lightgrey),
        ("RIGHTPADDING", (1, 0), (1, 0), 6),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    total_row = Table([[Spacer(1, 0), total_tbl]], colWidths=[100 * mm, 70 * mm])
    story += [total_row, Spacer(1, 6 * mm)]

    # tabla de ítems
    table_data = [["Artículo", "Cantidad", "Precio", "Monto"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row.get("descripcion", "")),
            int(row.get("cantidad", 0)),
            money(float(row.get("precio", 0.0))),
            money(float(row.get("monto", 0.0))),
        ])

    items_tbl = Table(table_data, colWidths=[100 * mm, 20 * mm, 25 * mm, 25 * mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000033")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
    ]))
    story += [items_tbl, Spacer(1, 6 * mm)]

    # totales
    totals_tbl = Table([
        ["Subtotal:", money(subtotal)],
        [f"Descuento ({descuento_pct:.1f}%):", money(descuento)],
        [f"Impuesto ({impuesto_pct:.1f}%):", money(impuesto)],
        ["Total:", money(TOTAL)],
    ], colWidths=[120 * mm, 50 * mm])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    totals_row = Table([[Spacer(1, 0), totals_tbl]], colWidths=[95 * mm, 75 * mm])
    story += [totals_row, Spacer(1, 6 * mm)]

    # notas / términos
    story += [Paragraph("Notas:", styles["H2X"]), Paragraph(notas.replace("\n", "<br/>"), styles["Normal"]), Spacer(1, 2 * mm)]
    story += [Paragraph("Términos:", styles["H2X"]), Paragraph(terminos.replace("\n", "<br/>"), styles["Normal"])]

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
