import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import common

filtro_destino = common.render_encabezado_pagina_solo_destino("Resumen General")

st.title("Resumen General — Turismo Santa Elena")
st.markdown(
    "Visión consolidada de los 6 destinos turísticos de la provincia "
    "de Santa Elena, calculada en vivo a partir de las publicaciones "
    "de hospedaje activas en 4 plataformas digitales."
)

df_precios = common.cargar_precios()
df_val = common.cargar_valoraciones()

# Promedios GLOBALES (sin filtrar) — sirven de referencia/benchmark
# para el delta de los KPIs cuando el usuario filtra un destino específico.
precio_prom_general = df_precios["precio_promedio_noche_usd"].mean()
valoracion_prom_general = df_val["valoracion_promedio"].mean()
publicaciones_prom_general = df_precios["total_publicaciones"].mean()
resenas_prom_general = df_val["total_resenas"].mean()

if filtro_destino != "Todos":
    df_precios = df_precios[df_precios["nombre_destino"] == filtro_destino]
    df_val = df_val[df_val["nombre_destino"] == filtro_destino]

# KPIs — CALCULADOS EN VIVO
total_publicaciones = int(df_precios["total_publicaciones"].sum())
precio_prom_actual = df_precios["precio_promedio_noche_usd"].mean()
valoracion_prom_actual = df_val["valoracion_promedio"].mean()
total_resenas_actual = int(df_val["total_resenas"].sum())

# Delta vs. promedio de los 6 destinos: solo tiene sentido cuando hay
# un destino específico seleccionado (comparar "Todos" contra sí mismo
# no aporta información).
hay_comparacion = filtro_destino != "Todos"
if hay_comparacion:
    delta_precio = f"{(precio_prom_actual - precio_prom_general):+.2f} USD vs. promedio"
    delta_valoracion = f"{(valoracion_prom_actual - valoracion_prom_general):+.2f} vs. promedio"
    delta_publicaciones = f"{(total_publicaciones - publicaciones_prom_general):+.0f} vs. promedio"
    delta_resenas = f"{(total_resenas_actual - resenas_prom_general):+.0f} vs. promedio"
else:
    delta_precio = delta_valoracion = delta_publicaciones = delta_resenas = None

with st.container(border=True, key="caja_kpis"):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total publicaciones", f"{total_publicaciones:,}",
        delta=delta_publicaciones, delta_color="normal",
    )
    col2.metric(
        "Precio promedio/noche", f"${precio_prom_actual:.2f}",
        delta=delta_precio, delta_color="off",
    )
    col3.metric(
        "Valoración promedio", f"{valoracion_prom_actual:.2f}/5.00",
        delta=delta_valoracion, delta_color="normal",
    )
    col4.metric(
        "Total reseñas", f"{total_resenas_actual:,}",
        delta=delta_resenas, delta_color="normal",
    )
    if hay_comparacion:
        st.caption(f"Comparado contra el promedio de los 6 destinos de la provincia.")

st.markdown("<br>", unsafe_allow_html=True)

# Datos comunes usados por el mapa y los gráficos
COORDENADAS = {
    "Salinas": (-2.2145, -80.9515),
    "La Libertad": (-2.2275, -80.9101),
    "Punta Carnero": (-2.2167, -80.9667),
    "Montañita": (-1.8333, -80.7667),
    "Ayangue": (-1.9667, -80.7500),
    "Manglaralto": (-1.8667, -80.7333),
}
df_mapa = df_precios.copy()
df_mapa["lat"] = df_mapa["nombre_destino"].map(lambda x: COORDENADAS.get(x, (0, 0))[0])
df_mapa["lon"] = df_mapa["nombre_destino"].map(lambda x: COORDENADAS.get(x, (0, 0))[1])
df_mapa = df_mapa.merge(df_val[["nombre_destino", "valoracion_promedio", "total_resenas"]], on="nombre_destino")

# ============================================================
# FILA 1: Precio por destino | Valoración por destino
# ============================================================
col_precio, col_val = st.columns(2)

with col_precio:
    common.render_seccion("Precio promedio por destino (USD/noche)")
    fig = px.bar(
        df_precios.sort_values("precio_promedio_noche_usd", ascending=True),
        x="precio_promedio_noche_usd",
        y="nombre_destino",
        orientation="h",
        color="nombre_destino",
        color_discrete_map=common.COLORES_DESTINO,
        text="precio_promedio_noche_usd",
        labels={"precio_promedio_noche_usd": "Precio promedio (USD)", "nombre_destino": "Destino"},
    )
    fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
    fig.update_layout(showlegend=False, height=340)
    st.plotly_chart(fig, use_container_width=True)
    common.cerrar_seccion()

with col_val:
    common.render_seccion("Valoración promedio por destino (1-5)")
    df_val_orden = df_val.sort_values("valoracion_promedio", ascending=True)
    # Color con propósito: rojo = por debajo del umbral de satisfacción (4.0),
    # color normal del destino = por encima del umbral.
    colores_val = [
        "#E74C3C" if v < 4.0 else common.COLORES_DESTINO.get(d, "#3A7CA5")
        for d, v in zip(df_val_orden["nombre_destino"], df_val_orden["valoracion_promedio"])
    ]
    fig2 = px.bar(
        df_val_orden,
        x="valoracion_promedio",
        y="nombre_destino",
        orientation="h",
        text="valoracion_promedio",
        labels={"valoracion_promedio": "Valoración promedio", "nombre_destino": "Destino"},
    )
    fig2.update_traces(
        marker_color=colores_val,
        texttemplate="%{text:.2f}",
        textposition="outside",
    )
    fig2.add_vline(
        x=4.0, line_dash="dot", line_color="#999999",
        annotation_text="Umbral de satisfacción (4.0)",
        annotation_position="top",
        annotation_font_size=11,
        annotation_font_color="#666666",
    )
    fig2.update_layout(showlegend=False, height=340, xaxis_range=[0, 5.7])
    st.plotly_chart(fig2, use_container_width=True)
    common.cerrar_seccion()

# ============================================================
# INSIGHT DESTACADO (storytelling: qué pasa / por qué / qué decisión)
# Solo aplica con la vista comparativa de los 6 destinos; al filtrar
# un destino específico no hay comparación posible.
# ============================================================
if filtro_destino == "Todos" and not df_val.empty:
    fila_alerta = df_val.loc[df_val["valoracion_promedio"].idxmin()]
    if fila_alerta["valoracion_promedio"] < 4.0:
        destino_alerta = fila_alerta["nombre_destino"]
        valoracion_alerta = fila_alerta["valoracion_promedio"]

        precio_fila = df_precios[df_precios["nombre_destino"] == destino_alerta]
        precio_alerta = precio_fila["precio_promedio_noche_usd"].mean() if not precio_fila.empty else None
        precio_prom_resto = df_precios[
            df_precios["nombre_destino"] != destino_alerta
        ]["precio_promedio_noche_usd"].mean()
        es_caro = precio_alerta is not None and precio_alerta > precio_prom_resto

        texto_precio = (
            f" y además su precio promedio (${precio_alerta:.2f}/noche) está por encima "
            f"del resto de destinos (${precio_prom_resto:.2f}/noche)"
            if es_caro else ""
        )

        st.markdown(
            f"""
            <div style='background:#FDEDEC; border-left:5px solid #E74C3C;
                        border-radius:8px; padding:14px 20px; margin-bottom:16px;'>
                <p style='margin:0; font-weight:700; color:#943126; font-size:13px;
                          letter-spacing:0.3px;'>ALERTA — {destino_alerta} es el destino peor valorado</p>
                <p style='margin:8px 0 0 0; color:#4A4A4A; font-size:13px; line-height:1.5;'>
                    <b>Qué pasa:</b> {destino_alerta} tiene una valoración promedio de
                    {valoracion_alerta:.2f}/5.00, la más baja de los 6 destinos{texto_precio}.<br>
                    <b>Por qué:</b> esta diferencia suele concentrarse en una plataforma
                    específica, lo que sugiere que esa fuente indexa publicaciones de
                    menor calidad para ese destino.<br>
                    <b>Qué decisión tomar:</b> revisar la oferta de hospedaje en
                    {destino_alerta} antes de promocionarlo como destino premium, y dar
                    seguimiento a la calidad percibida por plataforma.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILA 2: Mapa a todo el ancho, más grande
# ============================================================
common.render_seccion("Distribución geográfica de destinos")

lat_min, lat_max = df_mapa["lat"].min(), df_mapa["lat"].max()
lon_min, lon_max = df_mapa["lon"].min(), df_mapa["lon"].max()
lat_centro = (lat_min + lat_max) / 2
lon_centro = (lon_min + lon_max) / 2

rango_max = max(lat_max - lat_min, lon_max - lon_min, 0.01)
if rango_max > 0.35:
    zoom_mapa = 9.6
elif rango_max > 0.15:
    zoom_mapa = 10.5
else:
    zoom_mapa = 12.8

fig_mapa = px.scatter_mapbox(
    df_mapa,
    lat="lat", lon="lon",
    size="total_publicaciones",
    color="valoracion_promedio",
    hover_name="nombre_destino",
    hover_data={
        "precio_promedio_noche_usd": ":.2f",
        "valoracion_promedio": ":.2f",
        "total_resenas": ":,",
        "lat": False, "lon": False
    },
    color_continuous_scale="RdYlGn",
    size_max=34,
    mapbox_style="carto-positron",
    labels={
        "valoracion_promedio": "Valoración",
        "precio_promedio_noche_usd": "Precio/noche USD",
        "total_resenas": "Total reseñas"
    }
)
fig_mapa.update_traces(marker=dict(opacity=0.85))
fig_mapa.update_layout(
    height=520,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    dragmode=False,
    coloraxis_colorbar=dict(title="Valoración<br>(1-5)", thickness=14),
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
st.caption(
    "Color = valoración promedio (rojo: más baja, verde: más alta). "
    "Tamaño del punto = cantidad de publicaciones activas."
)
common.cerrar_seccion()