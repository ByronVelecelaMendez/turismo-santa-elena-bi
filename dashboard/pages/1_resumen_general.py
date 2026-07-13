import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
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

precio_prom_general = df_precios["precio_promedio_noche_usd"].mean()
valoracion_prom_general = df_val["valoracion_promedio"].mean()
publicaciones_prom_general = df_precios["total_publicaciones"].mean()
resenas_prom_general = df_val["total_resenas"].mean()

if filtro_destino != "Todos":
    df_precios = df_precios[df_precios["nombre_destino"] == filtro_destino]
    df_val = df_val[df_val["nombre_destino"] == filtro_destino]

total_publicaciones = int(df_precios["total_publicaciones"].sum())
precio_prom_actual = df_precios["precio_promedio_noche_usd"].mean()
valoracion_prom_actual = df_val["valoracion_promedio"].mean()
total_resenas_actual = int(df_val["total_resenas"].sum())

hay_comparacion = filtro_destino != "Todos"
if hay_comparacion:
    delta_precio        = f"{(precio_prom_actual - precio_prom_general):+.2f} USD vs. promedio"
    delta_valoracion    = f"{(valoracion_prom_actual - valoracion_prom_general):+.2f} vs. promedio"
    delta_publicaciones = f"{(total_publicaciones - publicaciones_prom_general):+.0f} vs. promedio"
    delta_resenas       = f"{(total_resenas_actual - resenas_prom_general):+.0f} vs. promedio"
else:
    delta_precio = delta_valoracion = delta_publicaciones = delta_resenas = None

common.render_kpis([
    {
        "icono": "home_work", "etiqueta": "Total publicaciones",
        "valor": f"{total_publicaciones:,}",
        "delta": delta_publicaciones, "delta_modo": "normal",
    },
    {
        "icono": "payments", "etiqueta": "Precio promedio/noche",
        "valor": f"${precio_prom_actual:.2f}",
        "delta": delta_precio, "delta_modo": "off",
    },
    {
        "icono": "star", "etiqueta": "Valoración promedio",
        "valor": f"{valoracion_prom_actual:.2f}/5.00",
        "delta": delta_valoracion, "delta_modo": "normal",
    },
    {
        "icono": "reviews", "etiqueta": "Total reseñas",
        "valor": f"{total_resenas_actual:,}",
        "delta": delta_resenas, "delta_modo": "normal",
    },
])
if hay_comparacion:
    st.caption("Comparado contra el promedio de los 6 destinos de la provincia.")

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# Datos para mapa y gráficos
df_mapa = df_precios.copy()
df_mapa["lat"] = df_mapa["nombre_destino"].map(
    lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[0])
df_mapa["lon"] = df_mapa["nombre_destino"].map(
    lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[1])
df_mapa = df_mapa.merge(
    df_val[["nombre_destino", "valoracion_promedio", "total_resenas"]],
    on="nombre_destino")

# ============================================================
# FILA 1: Precio | Valoración
# ============================================================
col_precio, col_val = st.columns(2)

with col_precio:
    with common.seccion("Precio promedio por destino (USD/noche)", "precio_destino"):
        fig = px.bar(
            df_precios.sort_values("precio_promedio_noche_usd", ascending=True),
            x="precio_promedio_noche_usd",
            y="nombre_destino",
            orientation="h",
            color="nombre_destino",
            color_discrete_map=common.COLORES_DESTINO,
            text="precio_promedio_noche_usd",
            labels={
                "precio_promedio_noche_usd": "Precio promedio (USD)",
                "nombre_destino": "Destino",
            },
        )
        fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig.update_layout(showlegend=False, height=340)
        fig = common.estilo_grafico(fig)
        st.plotly_chart(fig, width="stretch")

with col_val:
    with common.seccion("Valoración promedio por destino (1-5)", "valoracion_destino"):
        df_val_orden = df_val.sort_values("valoracion_promedio", ascending=True)
        colores_val = [
            "#C0392B" if v < 4.0 else common.COLORES_DESTINO.get(d, "#0B3B70")
            for d, v in zip(
                df_val_orden["nombre_destino"],
                df_val_orden["valoracion_promedio"],
            )
        ]
        fig2 = px.bar(
            df_val_orden,
            x="valoracion_promedio",
            y="nombre_destino",
            orientation="h",
            text="valoracion_promedio",
            labels={
                "valoracion_promedio": "Valoración promedio",
                "nombre_destino": "Destino",
            },
        )
        fig2.update_traces(
            marker_color=colores_val,
            texttemplate="%{text:.2f}",
            textposition="outside",
        )
        fig2.add_vline(
            x=4.0, line_dash="dot", line_color="#8FA6BC",
            annotation_text="Umbral de satisfacción (4.0)",
            annotation_position="top",
            annotation_font_size=11,
            annotation_font_color="#5B7C99",
        )
        fig2.update_layout(showlegend=False, height=340, xaxis_range=[0, 5.7])
        fig2 = common.estilo_grafico(fig2)
        st.plotly_chart(fig2, width="stretch")

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

# ============================================================
# FILA 2: Mapa interactivo pydeck
# ============================================================

_HEX_RGB = {
    "#0B3B70": [11,  59, 112],
    "#1B6FC9": [27, 111, 201],
    "#4A9FD8": [74, 159, 216],
    "#5B7C99": [91, 124, 153],
    "#8FA6BC": [143, 166, 188],
    "#2E8B8B": [46, 139, 139],
}

df_deck = df_mapa.copy()
df_deck["r"] = df_deck["nombre_destino"].map(
    lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11, 59, 112])[0])
df_deck["g"] = df_deck["nombre_destino"].map(
    lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11, 59, 112])[1])
df_deck["b"] = df_deck["nombre_destino"].map(
    lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11, 59, 112])[2])

df_deck["precio_fmt"]  = df_deck["precio_promedio_noche_usd"].apply(lambda x: f"{x:.2f}")
df_deck["val_fmt"]     = df_deck["valoracion_promedio"].apply(lambda x: f"{x:.2f}")
df_deck["resenas_fmt"] = df_deck["total_resenas"].apply(lambda x: f"{int(x):,}")

lat_centro = df_deck["lat"].mean()
lon_centro = df_deck["lon"].mean()

with common.seccion("Distribución geográfica de destinos", "mapa_destinos"):

    # Círculo fijo pequeño — auto_highlight=False para que NO se agrande al hover
    capa_circulo = pdk.Layer(
        "ScatterplotLayer",
        data=df_deck,
        get_position=["lon", "lat"],
        get_radius=400,
        get_fill_color=["r", "g", "b", 230],
        get_line_color=[255, 255, 255, 255],
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=False,
        stroked=True,
        radius_min_pixels=8,
        radius_max_pixels=18,
    )

    # Punto blanco interior (efecto pin)
    capa_pin = pdk.Layer(
        "ScatterplotLayer",
        data=df_deck,
        get_position=["lon", "lat"],
        get_radius=120,
        get_fill_color=[255, 255, 255, 240],
        get_line_color=[255, 255, 255, 0],
        pickable=False,
        stroked=False,
        radius_min_pixels=3,
        radius_max_pixels=5,
    )

    # Etiquetas con fondo blanco semitransparente
    capa_texto = pdk.Layer(
        "TextLayer",
        data=df_deck,
        get_position=["lon", "lat"],
        get_text="nombre_destino",
        get_size=13,
        get_color=[11, 46, 82, 255],
        get_anchor="'middle'",
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -18],
        font_family="Segoe UI, Arial, sans-serif",
        font_weight="bold",
        background=True,
        get_background_color=[255, 255, 255, 210],
        get_border_color=[216, 226, 239, 255],
        border_width=1,
        get_padding=[4, 2, 4, 2],
        border_radius=4,
    )

    vista = pdk.ViewState(
        latitude=lat_centro,
        longitude=lon_centro,
        zoom=9.8,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": """
            <div style='
                background:#0B3B70;
                color:#FFFFFF;
                padding:12px 16px;
                border-radius:12px;
                font-family:Segoe UI,Arial,sans-serif;
                font-size:12px;
                line-height:1.8;
                box-shadow:0 6px 20px rgba(0,0,0,0.30);
                min-width:180px;
            '>
                <div style='font-size:14px;font-weight:800;
                    border-bottom:1px solid rgba(255,255,255,0.2);
                    padding-bottom:6px;margin-bottom:8px;'>
                    {nombre_destino}
                </div>
                🏠 &nbsp;<b>{total_publicaciones}</b> publicaciones<br>
                💰 &nbsp;USD <b>{precio_fmt}</b> / noche<br>
                ⭐ &nbsp;<b>{val_fmt}</b> / 5.00 valoración<br>
                💬 &nbsp;<b>{resenas_fmt}</b> reseñas
            </div>
        """,
        "style": {"background": "transparent", "border": "none", "padding": "0"},
    }

    deck = pdk.Deck(
        layers=[capa_circulo, capa_pin, capa_texto],
        initial_view_state=vista,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip=tooltip,
    )

    st.pydeck_chart(deck, height=460)

    # Leyenda de colores por destino
    _chips = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:6px;"
        f"background:#FFFFFF;border:1px solid #D8E2EF;border-radius:999px;"
        f"padding:5px 14px;margin:3px 4px;font-size:11.5px;"
        f"font-weight:600;color:#1A2E44;'>"
        f"<span style='width:10px;height:10px;border-radius:50%;"
        f"background:{color};display:inline-block;flex-shrink:0;'></span>"
        f"{destino}</span>"
        for destino, color in common.COLORES_DESTINO.items()
    )
    st.markdown(
        f"<div style='text-align:center;margin-top:10px;'>{_chips}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Mapa interactivo · Arrastra para mover · Scroll para hacer zoom · "
        "Hover sobre un punto para ver sus indicadores."
    )