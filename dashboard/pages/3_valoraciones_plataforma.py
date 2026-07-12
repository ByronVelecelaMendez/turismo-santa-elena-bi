import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.express as px
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Valoraciones por Plataforma")

st.title("Valoraciones por Destino y Plataforma")
st.markdown("Comparativa de la valoración de viajeros según plataforma digital de reserva.")

df_plat = common.cargar_valoracion_por_plataforma()

if filtro_destino != "Todos":
    df_plat = df_plat[df_plat["nombre_destino"] == filtro_destino]
if filtro_plataforma != "Todas":
    df_plat = df_plat[df_plat["nombre_plataforma"] == filtro_plataforma]

common.render_seccion("Heatmap: Valoración promedio por Destino × Plataforma")
df_heat = df_plat.pivot_table(
    index="nombre_destino",
    columns="nombre_plataforma",
    values="valoracion_promedio"
)
fig = px.imshow(
    df_heat,
    color_continuous_scale="RdYlGn",
    zmin=1, zmax=5,
    text_auto=".2f",
    labels={"color": "Valoración (1-5)"},
    height=320
)
fig.update_layout(
    xaxis_title="Plataforma", yaxis_title="Destino",
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)
common.cerrar_seccion()

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    common.render_seccion("Valoración promedio por plataforma")
    df_por_plat = df_plat.groupby("nombre_plataforma")["valoracion_promedio"].mean().reset_index()
    fig2 = px.bar(
        df_por_plat.sort_values("valoracion_promedio", ascending=False),
        x="nombre_plataforma",
        y="valoracion_promedio",
        color="nombre_plataforma",
        text="valoracion_promedio",
        labels={"valoracion_promedio": "Valoración promedio", "nombre_plataforma": "Plataforma"},
        height=300
    )
    fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig2.update_layout(
        showlegend=False, yaxis_range=[0, 5.5],
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)
    common.cerrar_seccion()

with col_b:
    common.render_seccion("Total de reseñas por destino")
    df_resenas = df_plat.groupby("nombre_destino")["total_resenas"].sum().reset_index()
    fig3 = px.pie(
        df_resenas,
        values="total_resenas",
        names="nombre_destino",
        color="nombre_destino",
        color_discrete_map=common.COLORES_DESTINO,
        height=300
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)
    common.cerrar_seccion()
