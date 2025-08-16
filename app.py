# app.py
from __future__ import annotations
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# PDF utils
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# -------------------- Config --------------------
st.set_page_config(
    page_title="Generador de Presupuestos",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- Helpers --------------------
CURRENCY = "ARS"

def money(x: float) -> str:
    try:
        return f"{CURRENCY} {x:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except Exception:
        return f"{CURRENCY} 0,00"

DEFAULT_ROWS = [
    {"Descripción": "Taza Lucky de porcelana eléctrica con calentador", "Cantidad": 1, "Precio unitario": 18999.0},
    {"Descripción": "Vaso térmico con sensor de temperatura digital", "Cantidad": 1, "Precio unitario": 13999.0},
]

# -------------------- UI --------------------
st.title("🧾 Generador de Presupuestos (Streamlit)")
st.caption("Completá los campos, cargá los ítems y descargá el PDF listo para enviar.")

colA, colB, colC, colD = st.columns((1,1,1,1))
with colA:
    empresa = st.text_input("Nombre de tu negocio / marca", value="Mamba Shop")
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
st.subheader("Ítems")

edited = st.data_editor(
    pd.DataFrame(DEFAULT_ROWS),
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Descripción": st.column_config.TextColumn("Descripción", width="large"),
        "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1),
        "Precio unitario": st.column_config.NumberColumn("Precio unitario", min_value=0.0, step=100.0, format="%d"),
    },
    hide_index=True,
)

# Totals
items = edited.fillna({"Cantidad": 0, "Precio unitario": 0.0})
items["Monto"] = items["Cantidad"] * items["Precio unitario"]

subtotal = float(items["Monto"].sum())
descuento = subtotal * (descuento_pct / 100.0)
base = subtotal - descuento
impuesto = base * (impuesto_pct / 100.0)
total = base + impuesto

st.markdown("### Resumen")
rs1, rs2, rs3, rs4 = st.columns(4)
rs1.metric("Subtotal", money(subtotal))
rs2.metric(f"Descuento ({descuento_pct:.1f}%)", money(descuento))
rs3.metric(f"Impuesto ({impuesto_pct:.1f}%)", money(impuesto))
rs4.metric("TOTAL", money(total))

st.markdown("---")

notas = st.text_area(
    "Notas",
    value=(
        "Este presupuesto fue elaborado según los productos y cantidades solicitadas.\n"
        "Los colores y modelos pueden variar levemente según disponibilidad de stock.\n"
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

# -------------------- PDF generation --------------------
def build_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=16*mm,
        bottomMargin=16*mm,
        title=f"Presupuesto_{nro}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="h1", fontSize=18, leading=22, spaceAfter=6))
    styles.add(ParagraphStyle(name="h2", fontSize=12, leading=15, spaceAfter=4, textColor=colors.grey))
    styles.add(ParagraphStyle(name="right", alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="small", fontSize=9, leading=12, textColor=colors.grey))

    story = []

    # Encabezado
    header_table = Table([
        [Paragraph(f"<b>Presupuesto # {nro}</b>", styles["h1"]), Paragraph(f"<b>{empresa}</b>", styles["h1"])],
        [Paragraph(f"Cotización para: <b>{cliente}</b>", styles["Normal"]), Paragraph("", styles["Normal"])],
        [Paragraph(f"Fecha: {fecha.strftime('%d/%m/%Y')}", styles["Normal"]), Paragraph(f"Vencimiento: {vencimiento.strftime('%d/%m/%Y')}", styles["right"])],
        [Paragraph(f"Condiciones de pago: {pago}", styles["Normal"]), Paragraph("", styles["right"])],
    ], colWidths=[95*mm, 75*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story += [header_table, Spacer(1, 6*mm)]

    # Tabla de items
    table_data = [["Artículo", "Cantidad", "Precio", "Monto"]]
    for _, row in items.iterrows():
        table_data.append([
            row["Descripción"],
            int(row["Cantidad"]),
            money(float(row["Precio unitario"])),
            money(float(row["Monto"]))
        ])

    tbl = Table(table_data, colWidths=[100*mm, 20*mm, 25*mm, 25*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
    ]))

    story += [tbl, Spacer(1, 4*mm)]

    # Totales
    totals_tbl = Table([
        ["Subtotal:", money(subtotal)],
        [f"Descuento ({descuento_pct:.1f}%):", money(descuento)],
        [f"Impuesto ({impuesto_pct:.1f}%):", money(impuesto)],
        ["Total:", money(total)],
    ], colWidths=[120*mm, 50*mm])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LINEABOVE", (0,-1), (-1,-1), 0.5, colors.black),
    ]))

    story += [totals_tbl, Spacer(1, 6*mm)]

    # Notas / Términos
    story += [Paragraph("Notas:", styles["h2"]), Paragraph(notas.replace("\n", "<br/>"), styles["Normal"]), Spacer(1, 2*mm)]
    story += [Paragraph("Términos:", styles["h2"]), Paragraph(terminos.replace("\n", "<br/>"), styles["Normal"])]

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# -------------------- Actions --------------------
colx, coly = st.columns([1,2])
with colx:
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

# Extra: exportar ítems a CSV
csv = items.to_csv(index=False).encode("utf-8")
st.download_button("Descargar ítems (CSV)", data=csv, file_name=f"items_{nro}.csv", mime="text/csv")

st.info("Consejo: Podés dejar la app abierta para que tu hermana complete y genere el PDF cuando quiera.")
