# app.py
from __future__ import annotations
import io
from datetime import date, timedelta

import streamlit as st
import pandas as pd

# PDF (ReportLab)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# -------------------- Config --------------------
st.set_page_config(
    page_title="Generador de Presupuestos",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------- Helpers ----------------
CURRENCY = "ARS"

def money(x: float) -> str:
    try:
        return f"{CURRENCY} {x:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return f"{CURRENCY} 0,00"

# Estado inicial de ítems (evitar choque con .items())
DEFAULT_ITEMS = [
    {"descripcion": "Taza Lucky de porcelana eléctrica con calentador", "cantidad": 1, "precio": 18999.0},
    {"descripcion": "Vaso térmico con sensor de temperatura digital", "cantidad": 1, "precio": 13999.0},
]
if "line_items" not in st.session_state:
    st.session_state["line_items"] = DEFAULT_ITEMS.copy()

# -------------------- Encabezado --------------------
st.title("🧾 Generador de Presupuestos")
st.caption("Completá, cargá los ítems y descargá el PDF listo para enviar.")

colA, colB, colC, colD = st.columns((1, 1, 1, 1))
with colA:
    empresa = st.text_input("Tu negocio / marca", value="Mamba Shop")
    nro = st.text_input("N° de presupuesto", value="101")
with colB:
    cliente = st.text_input("Cotización para (cliente)", value="Milena")
    fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
with colC:
    vencimiento = st.date_input("Vencimiento", value=date.today() + timedelta(days=7), format="DD/MM/YYYY")
    pago = st.text_input("Condiciones de pago", value="Transferencia Bancaria, Mercado Pago o Efectivo")
with colD:
    descuento_pct = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
    impuesto_pct = st.number_input("Impuesto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

st.markdown("---")

# -------------------- Ítems (UI estilo GlobalTrip) --------------------
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

# Tabla resumen solo-lectura para ver totales
if st.session_state["line_items"]:
    df = pd.DataFrame(st.session_state["line_items"]).fillna({"cantidad": 0, "precio": 0.0})
    df["monto"] = df["cantidad"] * df["precio"]
else:
    df = pd.DataFrame(columns=["descripcion", "cantidad", "precio", "monto"])

st.markdown("\n")
st.dataframe(
    df.rename(columns={"descripcion": "Descripción", "cantidad": "Cantidad", "precio": "Precio unitario", "monto": "Monto"}),
    use_container_width=True,
    hide_index=True,
)

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

# -------------------- Generación de PDF --------------------
def build_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Presupuesto_{nro}",
    )

    styles = getSampleStyleSheet()
    # Estilos con nombres únicos para evitar KeyError por duplicados
    for (name, kwargs) in [
        ("H1X", dict(fontSize=18, leading=22, spaceAfter=6)),
        ("H2X", dict(fontSize=12, leading=15, spaceAfter=4, textColor=colors.grey)),
        ("RightX", dict(alignment=TA_RIGHT)),
        ("SmallX", dict(fontSize=9, leading=12, textColor=colors.grey)),
    ]:
        if name not in styles:
            styles.add(ParagraphStyle(name=name, **kwargs))

    story = []

    header = Table(
        [
            [Paragraph(f"<b>Presupuesto # {nro}</b>", styles["H1X"]), Paragraph(f"<b>{empresa}</b>", styles["H1X"])],
            [Paragraph(f"Cotización para: <b>{cliente}</b>", styles["Normal"]), Paragraph("", styles["Normal"])],
            [Paragraph(f"Fecha: {fecha.strftime('%d/%m/%Y')}", styles["Normal"]), Paragraph(f"Vencimiento: {vencimiento.strftime('%d/%m/%Y')}", styles["RightX"])],
            [Paragraph(f"Condiciones de pago: {pago}", styles["Normal"]), Paragraph("", styles["RightX"])],
        ],
        colWidths=[95 * mm, 75 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [header, Spacer(1, 6 * mm)]

    # Items
    table_data = [["Artículo", "Cantidad", "Precio", "Monto"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row.get("descripcion", "")),
            int(row.get("cantidad", 0)),
            money(float(row.get("precio", 0.0))),
            money(float(row.get("monto", 0.0))),
        ])

    tbl = Table(table_data, colWidths=[100 * mm, 20 * mm, 25 * mm, 25 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    story += [tbl, Spacer(1, 4 * mm)]

    # Totales
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
    story += [totals_tbl, Spacer(1, 6 * mm)]

    # Notas / Términos
    story += [Paragraph("Notas:", styles["H2X"]), Paragraph(notas.replace("\n", "<br/>"), styles["Normal"]), Spacer(1, 2 * mm)]
    story += [Paragraph("Términos:", styles["H2X"]), Paragraph(terminos.replace("\n", "<br/>"), styles["Normal"])]

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

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

# CSV de ítems
csv = (
    df.rename(columns={"descripcion": "Descripción", "cantidad": "Cantidad", "precio": "Precio unitario", "monto": "Monto"})
      .to_csv(index=False).encode("utf-8")
)
st.download_button("Descargar ítems (CSV)", data=csv, file_name=f"items_{nro}.csv", mime="text/csv")

st.info("Tip: Podés dejar la app pública para que la complete tu hermana y descargue el PDF.")
