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
    # Ubicar columnas relevantes ANTES de filtrar, para poder aplicar
    # los filtros de Destino y Plataforma sobre la encuesta.
    col_calidad = common.buscar_columna(df_enc, "calidad")
    col_recomienda = common.buscar_columna(df_enc, "recomend")
    col_mejora = common.buscar_columna(df_enc, "mejorar")
    col_temporada = common.buscar_columna(df_enc, "temporada")
    col_precio = common.buscar_columna(df_enc, "paga") or common.buscar_columna(df_enc, "precio")
    col_plataforma_enc = common.buscar_columna(df_enc, "plataforma")
    col_tipo_enc = common.buscar_columna(df_enc, "tipo de alojamiento") or common.buscar_columna(df_enc, "alojamiento")
    col_destino_enc = common.buscar_columna(df_enc, "destino_homologado")

    # ============================================================
    # FILTROS (aplicados de verdad sobre la encuesta)
    # ============================================================
    if filtro_destino != "Todos" and col_destino_enc:
        slug = common.DESTINO_A_SLUG_ENCUESTA.get(filtro_destino)
        if slug:
            df_enc = df_enc[df_enc[col_destino_enc] == slug]

    if filtro_plataforma != "Todas" and col_plataforma_enc:
        df_enc = df_enc[
            df_enc[col_plataforma_enc].astype(str).str.contains(
                filtro_plataforma, case=False, na=False
            )
        ]

    if df_enc.empty:
        st.info(
            "No hay respuestas de la encuesta para esta combinación de "
            "filtros (Destino / Plataforma)."
        )
    else:
        respuestas_totales = len(df_enc)

        rating_calidad_txt = "N/D"
        if col_calidad and pd.api.types.is_numeric_dtype(df_enc[col_calidad]):
            rating_calidad_txt = f"{df_enc[col_calidad].mean():.2f}/5.00"

        recomienda_txt = "N/D"
        if col_recomienda:
            serie = df_enc[col_recomienda].astype(str).str.strip().str.lower()
            positivos = serie.str.contains("sí", na=False).sum()
            recomienda_txt = f"{(positivos / respuestas_totales) * 100:.1f}%"

        common.render_kpis([
            {"icono": "assignment_turned_in", "etiqueta": "Respuestas recolectadas", "valor": f"{respuestas_totales}"},
            {"icono": "star", "etiqueta": "Rating precio-calidad (encuesta)", "valor": rating_calidad_txt},
            {"icono": "thumb_up", "etiqueta": "Recomendarían visitar", "valor": recomienda_txt},
        ])

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            common.render_seccion("Aspectos a mejorar (encuesta)")
            if col_mejora:
                mejoras = df_enc[col_mejora].value_counts().reset_index()
                mejoras.columns = ["aspecto", "cantidad"]
                fig = px.bar(
                    mejoras, x="cantidad", y="aspecto", orientation="h",
                    color="aspecto", color_discrete_sequence=common.PALETA_SECUNDARIA,
                    labels={"cantidad": "Respuestas", "aspecto": "Aspecto"}, height=370
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False)
                fig = common.estilo_grafico(fig)
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
                    temp, values="cantidad", names="temporada", height=370,
                    hole=0.55,
                    color_discrete_sequence=common.PALETA_SECUNDARIA
                )
                fig2.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    textfont=dict(size=13, color="#FFFFFF", family="Segoe UI"),
                    insidetextorientation="horizontal",
                    marker=dict(line=dict(color="#FFFFFF", width=2)),
                    hovertemplate="%{label}<br>%{value} respuestas (%{percent})<extra></extra>",
                )
                fig2.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle", y=0.5,
                        xanchor="left", x=1.02,
                        font=dict(size=11, color="#3A4D63"),
                    ),
                )
                fig2 = common.estilo_grafico(fig2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No se encontró la columna de 'temporada preferida' en fact_encuesta.")
            common.cerrar_seccion()

        st.markdown("<br>", unsafe_allow_html=True)

        common.render_seccion("Brecha: Precio esperado (encuesta) vs Precio real (plataformas)")

        # El precio real de plataformas se filtra igual que en el resto
        # del dashboard (por destino y plataforma), para comparar
        # manzanas con manzanas contra la encuesta ya filtrada arriba.
        df_fact_filtrado = df_fact_precio.copy()
        if filtro_destino != "Todos":
            df_fact_filtrado = df_fact_filtrado[df_fact_filtrado["nombre_destino"] == filtro_destino]
        if filtro_plataforma != "Todas":
            df_fact_filtrado = df_fact_filtrado[df_fact_filtrado["nombre_plataforma"] == filtro_plataforma]

        precio_real_promedio = df_fact_filtrado["precio_noche_usd"].mean()

        precios_enc_rangos = {
            "Menos de $30": 15, "$30 a $60": 45,
            "$61 a $100": 80, "Más de $100": 120
        }

        if col_precio and pd.notna(precio_real_promedio):
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
                    color_discrete_sequence=["#8FA6BC", "#0B3B70"], height=370,
                    labels={"Precio USD/noche": "Precio promedio (USD/noche)"}
                )
                fig3.update_traces(
                    texttemplate="$%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=13, color="#1A2E44"),
                    width=0.28,
                )
                fig3.update_layout(
                    showlegend=False,
                    bargap=0.6,
                    yaxis_range=[0, max(precio_real_promedio, precio_enc_promedio) * 1.3],
                    xaxis=dict(range=[-0.9, 1.9]),
                )
                fig3 = common.estilo_grafico(fig3)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No se pudo mapear las respuestas de rango de precio de la encuesta.")
        else:
            st.info(
                "No hay datos suficientes de precio (encuesta o plataformas) "
                "para esta combinación de filtros."
            )
        common.cerrar_seccion()

        st.markdown("<br>", unsafe_allow_html=True)

        col_c, col_d = st.columns(2)

        with col_c:
            common.render_seccion("Plataforma usada para reservar")
            if col_plataforma_enc:
                plats = df_enc[col_plataforma_enc].value_counts().reset_index()
                plats.columns = ["plataforma", "cantidad"]
                fig4 = px.pie(
                    plats, values="cantidad", names="plataforma", height=370,
                    hole=0.55,
                    color_discrete_sequence=common.PALETA_SECUNDARIA
                )
                fig4.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    textfont=dict(size=13, color="#FFFFFF", family="Segoe UI"),
                    insidetextorientation="horizontal",
                    marker=dict(line=dict(color="#FFFFFF", width=2)),
                    hovertemplate="%{label}<br>%{value} respuestas (%{percent})<extra></extra>",
                )
                fig4.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle", y=0.5,
                        xanchor="left", x=1.02,
                        font=dict(size=11, color="#3A4D63"),
                    ),
                )
                fig4 = common.estilo_grafico(fig4)
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
                    color_discrete_sequence=common.PALETA_SECUNDARIA,
                    height=370, labels={"cantidad": "Respuestas", "tipo": "Tipo de alojamiento"}
                )
                fig5.update_traces(textposition="outside")
                fig5.update_layout(showlegend=False)
                fig5 = common.estilo_grafico(fig5)
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("No se encontró la columna de 'tipo de alojamiento preferido' en fact_encuesta.")
            common.cerrar_seccion()