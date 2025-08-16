200
201
202
203
204
205
206
207
208
209
210
211
212
213
214
215
216
217
218
219
220
221
222
223
224
225
226
227
228
229
230
231
232
233
234
235
236
237
238
239
240
241
242
243
244
245
246
247
248
249
250
251
252
253
254
255
# app.py
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
        ["Total:", money(TOTAL)],
    ], colWidths=[120*mm, 50*mm])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LINEABOVE", (0,-1), (-1,-1), 0.5, colors.black),
    ]))
    story += [totals_tbl, Spacer(1, 6*mm)]

    # textos
    story += [Paragraph("Notas:", styles["H2X"]), Paragraph(notas.replace("
","<br/>"), styles["Normal"]), Spacer(1, 2*mm)]
    story += [Paragraph("Términos:", styles["H2X"]), Paragraph(terminos.replace("
","<br/>"), styles["Normal"])]

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# -------------------- Acciones --------------------
col_btn, _ = st.columns([1,3])
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
csv = (df.rename(columns={"descripcion":"Descripción","cantidad":"Cantidad","precio":"Precio unitario","monto":"Monto"})
          .to_csv(index=False).encode("utf-8"))
st.download_button("Descargar ítems (CSV)", data=csv, file_name=f"items_{nro}.csv", mime="text/csv")

st.info("Tip: Podés dejar la app pública para que la complete tu hermana y descargue el PDF.")
