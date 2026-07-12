import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Encuesta Propia")

st.title("Encuesta Propia vs Plataformas Digitales")
st.markdown(
    "Comparativa entre la percepción de los viajeros (encuesta) y las "
    "valoraciones reales publicadas en plataformas digitales."
)

df_enc = common.cargar_encuesta()
df_fact_precio = common.cargar_fact_hospedaje()

if df_enc.empty:
    st.warning(
        "No se encontró la tabla 'fact_encuesta' en el Data Warehouse. "
        "Corre primero: python cargar_encuesta_a_dw.py"
    )
else:
    col_calidad = common.buscar_columna(df_enc, "calidad")
    col_recomienda = common.buscar_columna(df_enc, "recomend")
    col_mejora = common.buscar_columna(df_enc, "mejorar")
    col_temporada = common.buscar_columna(df_enc, "temporada")
    col_precio = common.buscar_columna(df_enc, "paga") or common.buscar_columna(df_enc, "precio")
    col_plataforma_enc = common.buscar_columna(df_enc, "plataforma")
    col_tipo_enc = common.buscar_columna(df_enc, "tipo de alojamiento") or common.buscar_columna(df_enc, "alojamiento")

    respuestas_totales = len(df_enc)

    rating_calidad_txt = "N/D"
    if col_calidad and pd.api.types.is_numeric_dtype(df_enc[col_calidad]):
        rating_calidad_txt = f"{df_enc[col_calidad].mean():.2f}/5.00"

    recomienda_txt = "N/D"
    if col_recomienda:
        serie = df_enc[col_recomienda].astype(str).str.strip().str.lower()
        positivos = serie.str.contains("sí", na=False).sum()
        recomienda_txt = f"{(positivos / respuestas_totales) * 100:.1f}%"

    with st.container(border=True, key="caja_kpis"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Respuestas recolectadas", f"{respuestas_totales}")
        col2.metric("Rating precio-calidad (encuesta)", rating_calidad_txt)
        col3.metric("Recomendarían visitar", recomienda_txt)

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        common.render_seccion("Aspectos a mejorar (encuesta)")
        if col_mejora:
            mejoras = df_enc[col_mejora].value_counts().reset_index()
            mejoras.columns = ["aspecto", "cantidad"]
            fig = px.bar(
                mejoras, x="cantidad", y="aspecto", orientation="h",
                color="cantidad", color_continuous_scale="Reds",
                labels={"cantidad": "Respuestas", "aspecto": "Aspecto"}, height=350
            )
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontró la columna de 'aspecto a mejorar' en fact_encuesta.")
        common.cerrar_seccion()

    with col_b:
        common.render_seccion("Temporada preferida para visitar")
        if col_temporada:
            temp = df_enc[col_temporada].value_counts().reset_index()
            temp.columns = ["temporada", "cantidad"]
            fig2 = px.pie(
                temp, values="cantidad", names="temporada", height=350,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No se encontró la columna de 'temporada preferida' en fact_encuesta.")
        common.cerrar_seccion()

    st.markdown("<br>", unsafe_allow_html=True)

    common.render_seccion("Brecha: Precio esperado (encuesta) vs Precio real (plataformas)")

    precio_real_promedio = df_fact_precio["precio_noche_usd"].mean()

    precios_enc_rangos = {
        "Menos de $30": 15, "$30 a $60": 45,
        "$61 a $100": 80, "Más de $100": 120
    }

    if col_precio:
        df_enc["precio_estimado"] = df_enc[col_precio].map(precios_enc_rangos)
        precio_enc_promedio = df_enc["precio_estimado"].mean()

        if pd.notna(precio_enc_promedio):
            df_brecha = pd.DataFrame({
                "Fuente": ["Expectativa (encuesta)", "Precio real (plataformas)"],
                "Precio USD/noche": [precio_enc_promedio, precio_real_promedio]
            })
            fig3 = px.bar(
                df_brecha, x="Fuente", y="Precio USD/noche", color="Fuente",
                text="Precio USD/noche",
                color_discrete_sequence=["#2ca02c", "#1f77b4"], height=350,
                labels={"Precio USD/noche": "Precio promedio (USD/noche)"}
            )
            fig3.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
            fig3.update_layout(showlegend=False,
                               yaxis_range=[0, max(precio_real_promedio, precio_enc_promedio) * 1.3])
            st.plotly_chart(fig3, use_container_width=True)

            brecha = precio_real_promedio - precio_enc_promedio
            pct = (brecha / precio_enc_promedio) * 100 if precio_enc_promedio else 0
            st.info(
                f"**Hallazgo:** Los viajeros encuestados esperan pagar en promedio "
                f"**${precio_enc_promedio:.2f}/noche**, mientras que el precio promedio "
                f"real en plataformas digitales (calculado en vivo desde el DW) es "
                f"**${precio_real_promedio:.2f}/noche** — una brecha de "
                f"**${brecha:.2f} ({pct:+.0f}%)**."
            )
        else:
            st.info("No se pudo mapear las respuestas de rango de precio de la encuesta.")
    else:
        st.info("No se encontró la columna de 'precio pagado' en fact_encuesta.")
    common.cerrar_seccion()

    st.markdown("<br>", unsafe_allow_html=True)

    col_c, col_d = st.columns(2)

    with col_c:
        common.render_seccion("Plataforma usada para reservar")
        if col_plataforma_enc:
            plats = df_enc[col_plataforma_enc].value_counts().reset_index()
            plats.columns = ["plataforma", "cantidad"]
            fig4 = px.pie(
                plats, values="cantidad", names="plataforma", height=350,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig4.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No se encontró la columna de 'plataforma de reserva' en fact_encuesta.")
        common.cerrar_seccion()

    with col_d:
        common.render_seccion("Tipo de alojamiento preferido")
        if col_tipo_enc:
            tipos = df_enc[col_tipo_enc].value_counts().reset_index()
            tipos.columns = ["tipo", "cantidad"]
            fig5 = px.bar(
                tipos, x="tipo", y="cantidad", color="tipo", text="cantidad",
                height=350, labels={"cantidad": "Respuestas", "tipo": "Tipo de alojamiento"}
            )
            fig5.update_traces(textposition="outside")
            fig5.update_layout(showlegend=False)
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No se encontró la columna de 'tipo de alojamiento preferido' en fact_encuesta.")
        common.cerrar_seccion()
