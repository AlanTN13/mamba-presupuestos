# app.py
from __future__ import annotations
import io
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
import pandas as pd

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

# -------------------- Estilos Azul/Amarillo (Boca) --------------------
st.markdown("""
<style>
:root{
  --primary:#0d47a1;   /* Azul */
  --accent:#ffca28;    /* Amarillo */
  --bg:#ffffff;        /* Blanco */
  --text:#0d47a1;      /* Texto principal azul */
  --muted:#5f6368;     /* Gris */
  --radius:14px;
  --shadow:0 6px 18px rgba(0,0,0,.08);
}

/* Fondo y tipografía */
html, body, .stApp { background: var(--bg) !important; color: var(--text) !important; }

/* Separadores */
hr { border:0; height:1px; background: #e6e8eb; }

/* Títulos */
h1,h2,h3,h4,h5,h6 {
  color: var(--primary) !important;
  font-weight: 800 !important;
}

/* Contenedores con borde (fallback si no hay border=True) */
.block-container { padding-top: 2rem !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
  border:1.2px solid var(--primary) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  background: #fff !important;
}

/* Botones */
.stButton>button {
  background: var(--primary) !important;
  color: #fff !important;
  font-weight: 700 !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  border: 0 !important;
}
.stButton>button:hover { background: var(--accent) !important; color: var(--primary) !important; }

/* Métricas */
[data-testid="stMetricValue"] { color: var(--primary) !important; }

/* Dataframe */
[data-testid="stDataFrame"] div[data-testid="StyledTable"] {
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
CURRENCY = "ARS"
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"

# buscamos automáticamente el logo en varias rutas habituales
LOGO_CANDIDATES = [
    ASSETS_DIR / "logo.png",
    ASSETS_DIR / "logo.jpg",
    ASSETS_DIR / "logo.jpeg",
    BASE_DIR / "logo.png",
    BASE_DIR / "logo.jpg",
    BASE_DIR / "Imagen 1.jpg",  # tu archivo actual
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
    {"descripcion": "Taza Lucky de porcelana eléctrica con calentador", "cantidad": 20, "precio": 18999.0},
    {"descripcion": "Vaso térmico con sensor de temperatura digital", "cantidad": 20, "precio": 13999.0},
    {"descripcion": "Espejo de maquillaje con luz LED", "cantidad": 20, "precio": 9500.0},
]
if "line_items" not in st.session_state:
    st.session_state["line_items"] = DEFAULT_ITEMS.copy()

# -------------------- Encabezado (UI) --------------------
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

# -------------------- Ítems (UI tipo tarjetas + resumen) --------------------
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

# Resumen para totales
if st.session_state["line_items"]:
    df = pd.DataFrame(st.session_state["line_items"]).fillna({"cantidad": 0, "precio": 0.0})
    df["monto"] = df["cantidad"] * df["precio"]
else:
    df = pd.DataFrame(columns=["descripcion", "cantidad", "precio", "monto"])

st.dataframe(
    df.rename(columns={"descripcion": "Descripción", "cantidad": "Cantidad", "precio": "Precio unitario", "monto": "Monto"}),
    use_container_width=True,
    hide_index=True,
)

# -------------------- Totales (UI) --------------------
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

# -------------------- PDF: estilo similar a tu Word --------------------
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
    # estilos únicos
    if "H1X" not in styles:
        styles.add(ParagraphStyle(name="H1X", fontSize=18, leading=22, spaceAfter=6))
    if "H2X" not in styles:
        styles.add(ParagraphStyle(name="H2X", fontSize=12, leading=15, textColor=colors.grey))
    if "RightX" not in styles:
        styles.add(ParagraphStyle(name="RightX", alignment=TA_RIGHT))
    if "TitleBadge" not in styles:
        styles.add(ParagraphStyle(name="TitleBadge", fontSize=28, leading=30,
                                  backColor=colors.yellow, textColor=colors.black,
                                  alignment=TA_RIGHT, spaceAfter=6))
    if "HashNum" not in styles:
        styles.add(ParagraphStyle(name="HashNum", fontSize=12, textColor=colors.grey, alignment=TA_RIGHT))
    if "TotalBox" not in styles:
        styles.add(ParagraphStyle(name="TotalBox", fontSize=14, alignment=TA_RIGHT))

    story = []

    # fila superior: logo izq + título resaltado der
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

    # bloque empresa/cliente a la izq + datos a la derecha
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

    # badge TOTAL (caja gris claro) alineada a la derecha
    total_tbl = Table(
        [[Paragraph(":", styles["H2X"]), Paragraph(money(TOTAL), styles["TotalBox"])]],
        colWidths=[10 * mm, 60 * mm]
    )
    total_tbl.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), colors.whitesmoke),
        ("BOX", (1, 0), (1, 0), 0.5, colors.lightgrey),
        ("RIGHTPADDING", (1, 0), (1, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    total_row = Table([[Spacer(1, 0), total_tbl]], colWidths=[110 * mm, 60 * mm])
    story += [total_row, Spacer(1, 6 * mm)]

    # tabla de items (encabezado oscuro)
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
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.25, 0.25, 0.25)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
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

    # notas/terminos
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
