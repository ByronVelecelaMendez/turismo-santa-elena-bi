import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.express as px
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Análisis de Precios")

st.title("Análisis de Precios de Hospedaje")
st.markdown("Distribución y rangos de precios por destino y tipo de alojamiento.")

df_fact = common.cargar_fact_hospedaje()

if filtro_destino != "Todos":
    df_fact = df_fact[df_fact["nombre_destino"] == filtro_destino]
if filtro_plataforma != "Todas":
    df_fact = df_fact[df_fact["nombre_plataforma"] == filtro_plataforma]

with st.container(border=True, key="caja_kpis"):
    col1, col2, col3 = st.columns(3)
    col1.metric("Precio mínimo", f"${df_fact['precio_noche_usd'].min():.2f}")
    col2.metric("Precio promedio", f"${df_fact['precio_noche_usd'].mean():.2f}")
    col3.metric("Precio máximo", f"${df_fact['precio_noche_usd'].max():.2f}")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILA 1: Distribución de precios por destino | Mapa
# ============================================================
col_a, col_b = st.columns(2)

with col_a:
    common.render_seccion("Distribución de precios por destino")
    fig = px.box(
        df_fact.dropna(subset=["precio_noche_usd"]),
        x="nombre_destino",
        y="precio_noche_usd",
        color="nombre_destino",
        color_discrete_map=common.COLORES_DESTINO,
        labels={"precio_noche_usd": "Precio/noche (USD)", "nombre_destino": "Destino"},
        points="outliers"
    )
    fig.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig, use_container_width=True)
    common.cerrar_seccion()

with col_b:
    common.render_seccion("Mapa de precios por destino")

    # Se reconstruye desde df_fact (ya filtrado por destino Y plataforma)
    # en vez de usar la vista agregada, para que el mapa SÍ responda al
    # filtro de Plataforma.
    df_mapa = (
        df_fact.dropna(subset=["precio_noche_usd"])
        .groupby("nombre_destino")
        .agg(
            precio_promedio_noche_usd=("precio_noche_usd", "mean"),
            total_publicaciones=("precio_noche_usd", "count"),
        )
        .reset_index()
    )
    df_mapa["lat"] = df_mapa["nombre_destino"].map(lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[0])
    df_mapa["lon"] = df_mapa["nombre_destino"].map(lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[1])

    if df_mapa.empty:
        st.info("No hay publicaciones con precio para esta combinación de filtros.")
    else:
        lat_min, lat_max = df_mapa["lat"].min(), df_mapa["lat"].max()
        lon_min, lon_max = df_mapa["lon"].min(), df_mapa["lon"].max()
        lat_centro = (lat_min + lat_max) / 2
        lon_centro = (lon_min + lon_max) / 2
        rango_max = max(lat_max - lat_min, lon_max - lon_min, 0.01)
        if rango_max > 0.35:
            zoom_mapa = 9.3
        elif rango_max > 0.15:
            zoom_mapa = 10.2
        else:
            zoom_mapa = 12.5

        fig_mapa = px.scatter_mapbox(
            df_mapa,
            lat="lat", lon="lon",
            size="total_publicaciones",
            color="precio_promedio_noche_usd",
            hover_name="nombre_destino",
            hover_data={
                "precio_promedio_noche_usd": ":.2f",
                "total_publicaciones": True,
                "lat": False, "lon": False
            },
            color_continuous_scale="YlOrRd",
            size_max=28,
            mapbox_style="carto-positron",
            labels={"precio_promedio_noche_usd": "Precio (USD)"},
        )
        fig_mapa.update_traces(marker=dict(opacity=0.85))
        fig_mapa.update_layout(
            height=380,
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            dragmode=False,
            coloraxis_colorbar=dict(title="Precio<br>(USD)", thickness=12),
            mapbox=dict(
                zoom=zoom_mapa,
                center=dict(lat=lat_centro, lon=lon_centro),
            ),
        )
        st.plotly_chart(
            fig_mapa,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False},
        )
    st.caption("Color = precio promedio por noche (amarillo: más bajo, rojo: más alto).")
    common.cerrar_seccion()

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILA 2: Precio por tipo de alojamiento | Precio por plataforma y destino
# ============================================================
col_c, col_d = st.columns(2)

with col_c:
    common.render_seccion("Precio por tipo de alojamiento")
    df_tipo = df_fact.dropna(subset=["precio_noche_usd", "tipo_alojamiento"])
    if df_tipo.empty:
        st.info(
            "No hay datos suficientes de 'tipo_alojamiento' para graficar "
            "(recuerda: este campo tiene ~73% de nulos documentado en el "
            "Entregable 3 — Booking y Airbnb no lo exponen)."
        )
    else:
        fig3 = px.box(
            df_tipo,
            x="tipo_alojamiento",
            y="precio_noche_usd",
            color="tipo_alojamiento",
            labels={"precio_noche_usd": "Precio/noche (USD)", "tipo_alojamiento": "Tipo de alojamiento"},
            height=380
        )
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
    common.cerrar_seccion()

with col_d:
    common.render_seccion("Precio promedio por plataforma y destino")
    df_pivot = df_fact.groupby(["nombre_destino", "nombre_plataforma"])["precio_noche_usd"].mean().reset_index()
    fig2 = px.bar(
        df_pivot,
        x="nombre_destino",
        y="precio_noche_usd",
        color="nombre_plataforma",
        barmode="group",
        labels={"precio_noche_usd": "Precio promedio (USD)", "nombre_destino": "Destino", "nombre_plataforma": "Plataforma"},
        height=380
    )
    st.plotly_chart(fig2, use_container_width=True)
    common.cerrar_seccion()