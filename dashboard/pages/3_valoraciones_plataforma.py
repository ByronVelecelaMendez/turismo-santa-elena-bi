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

# ============================================================
# FILA 1: Heatmap a todo el ancho
# ============================================================
with common.seccion("Valoración promedio por Destino × Plataforma", "heatmap_val"):
    df_heat = df_plat.pivot_table(
        index="nombre_destino",
        columns="nombre_plataforma",
        values="valoracion_promedio",
    )
    fig = px.imshow(
        df_heat,
        color_continuous_scale=[
            [0.0, "#DCEAFB"],
            [0.3, "#8FA6BC"],
            [0.6, "#1B6FC9"],
            [1.0, "#0B3B70"],
        ],
        zmin=1,
        zmax=5,
        text_auto=".2f",
        labels={"color": "Valoración (1-5)"},
        height=300,
        aspect="auto",
    )
    fig.update_traces(
        textfont=dict(size=16, color="#FFFFFF",
                      family="Segoe UI, Arial, sans-serif"),
    )
    fig.update_layout(
        xaxis_title="Plataforma",
        yaxis_title="Destino",
        xaxis=dict(
            side="bottom",
            tickfont=dict(size=13, color="#1A2E44"),
            tickangle=0,
        ),
        yaxis=dict(
            tickfont=dict(size=13, color="#1A2E44"),
        ),
        coloraxis_colorbar=dict(
            title=dict(
                text="Valoración<br>(1-5)",
                font=dict(size=11, color="#5A7089"),
            ),
            thickness=14,
            tickfont=dict(size=10, color="#5A7089"),
            len=0.9,
        ),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    
    fig = common.estilo_grafico(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Azul oscuro = valoración alta · "
        "Azul claro = valoración baja · "
        "Blanco = sin datos para esa combinación."
    )

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

# ============================================================
# FILA 2: Barras por plataforma | Pie de reseñas
# Ambas columnas iguales [1, 1] para altura y ancho simétricos
# ============================================================
col_a, col_b = st.columns(2)

with col_a:
    with common.seccion("Valoración promedio por plataforma", "bar_val_plataforma"):
        df_por_plat = (
            df_plat
            .groupby("nombre_plataforma")["valoracion_promedio"]
            .mean()
            .reset_index()
        )
        fig2 = px.bar(
            df_por_plat.sort_values("valoracion_promedio", ascending=True),
            x="valoracion_promedio",
            y="nombre_plataforma",
            orientation="h",
            color="nombre_plataforma",
            color_discrete_map=common.COLORES_PLATAFORMA,
            text="valoracion_promedio",
            labels={
                "valoracion_promedio": "Valoración promedio",
                "nombre_plataforma": "Plataforma",
            },
            height=300,
        )
        fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig2.update_layout(showlegend=False, xaxis_range=[0, 5.5])
        fig2 = common.estilo_grafico(fig2)
        st.plotly_chart(fig2, width="stretch")

with col_b:
    with common.seccion("Total de reseñas por destino", "pie_resenas"):
        df_resenas = (
            df_plat
            .groupby("nombre_destino")["total_resenas"]
            .sum()
            .reset_index()
            .sort_values("total_resenas", ascending=False)
        )
        fig3 = px.pie(
            df_resenas,
            values="total_resenas",
            names="nombre_destino",
            color="nombre_destino",
            color_discrete_map=common.COLORES_DESTINO,
            hole=0.38,
            height=300,
        )
        fig3.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont=dict(size=11, color="#FFFFFF"),
            marker=dict(line=dict(color="#FFFFFF", width=2)),
            pull=[0.03] * len(df_resenas),
        )
        fig3.update_layout(
            showlegend=False,
            annotations=[dict(
                text="Reseñas",
                x=0.5, y=0.5,
                font=dict(size=12, color="#5A7089",
                          family="Segoe UI, Arial"),
                showarrow=False,
            )],
        )
        fig3 = common.estilo_grafico(fig3)
        st.plotly_chart(fig3, width="stretch")