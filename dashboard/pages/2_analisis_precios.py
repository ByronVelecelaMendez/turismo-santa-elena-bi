import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.express as px
import pydeck as pdk
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Análisis de Precios")

st.title("Análisis de Precios de Hospedaje")
st.markdown("Distribución y rangos de precios por destino y tipo de alojamiento.")

df_fact = common.cargar_fact_hospedaje()

if filtro_destino != "Todos":
    df_fact = df_fact[df_fact["nombre_destino"] == filtro_destino]
if filtro_plataforma != "Todas":
    df_fact = df_fact[df_fact["nombre_plataforma"] == filtro_plataforma]

if df_fact["precio_noche_usd"].dropna().empty:
    st.info(
        "No hay publicaciones con precio disponibles para esta combinación "
        "de filtros. Prueba con otra combinación."
    )
else:
    common.render_kpis([
        {
            "icono": "arrow_downward",
            "etiqueta": "Precio mínimo",
            "valor": f"${df_fact['precio_noche_usd'].min():.2f}",
        },
        {
            "icono": "payments",
            "etiqueta": "Precio promedio",
            "valor": f"${df_fact['precio_noche_usd'].mean():.2f}",
        },
        {
            "icono": "arrow_upward",
            "etiqueta": "Precio máximo",
            "valor": f"${df_fact['precio_noche_usd'].max():.2f}",
        },
    ])

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# ============================================================
# FILA 1: Boxplot de precios | Mapa pydeck
# ============================================================
col_a, col_b = st.columns(2)

with col_a:
    with common.seccion("Distribución de precios por destino", "box_precios"):
        fig = px.box(
            df_fact.dropna(subset=["precio_noche_usd"]),
            x="nombre_destino",
            y="precio_noche_usd",
            color="nombre_destino",
            color_discrete_map=common.COLORES_DESTINO,
            labels={
                "precio_noche_usd": "Precio/noche (USD)",
                "nombre_destino": "Destino",
            },
            points="outliers",
        )
        fig.update_layout(showlegend=False, height=420)
        fig = common.estilo_grafico(fig)
        st.plotly_chart(fig, width="stretch")

with col_b:
    with common.seccion("Mapa de precios por destino", "mapa_precios"):

        df_mapa = (
            df_fact.dropna(subset=["precio_noche_usd"])
            .groupby("nombre_destino")
            .agg(
                precio_promedio_noche_usd=("precio_noche_usd", "mean"),
                total_publicaciones=("precio_noche_usd", "count"),
            )
            .reset_index()
        )
        df_mapa["lat"] = df_mapa["nombre_destino"].map(
            lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[0])
        df_mapa["lon"] = df_mapa["nombre_destino"].map(
            lambda x: common.COORDENADAS_DESTINO.get(x, (0, 0))[1])

        if df_mapa.empty:
            st.info("No hay publicaciones con precio para esta combinación de filtros.")
        else:
            # Conversión hex → RGB
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
                lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11,59,112])[0])
            df_deck["g"] = df_deck["nombre_destino"].map(
                lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11,59,112])[1])
            df_deck["b"] = df_deck["nombre_destino"].map(
                lambda x: _HEX_RGB.get(common.COLORES_DESTINO.get(x, "#0B3B70"), [11,59,112])[2])
            df_deck["precio_fmt"] = df_deck["precio_promedio_noche_usd"].apply(
                lambda x: f"{x:.2f}")

            # Centro fijo en la costa de Santa Elena
            lat_centro = -2.05
            lon_centro = -80.86

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

            capa_pin = pdk.Layer(
                "ScatterplotLayer",
                data=df_deck,
                get_position=["lon", "lat"],
                get_radius=120,
                get_fill_color=[255, 255, 255, 240],
                pickable=False,
                stroked=False,
                radius_min_pixels=3,
                radius_max_pixels=5,
            )

            capa_texto = pdk.Layer(
                "TextLayer",
                data=df_deck,
                get_position=["lon", "lat"],
                get_text="nombre_destino",
                get_size=12,
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
                get_padding=[3, 2, 3, 2],
                border_radius=4,
            )

            tooltip = {
                "html": """
                    <div style='
                        background:#0B3B70;color:#FFFFFF;
                        padding:10px 14px;border-radius:10px;
                        font-family:Segoe UI,Arial,sans-serif;
                        font-size:12px;line-height:1.8;
                        box-shadow:0 4px 14px rgba(0,0,0,0.25);
                    '>
                        <b style='font-size:13px;'>{nombre_destino}</b><br>
                        💰 USD <b>{precio_fmt}</b> / noche<br>
                        🏠 <b>{total_publicaciones}</b> publicaciones
                    </div>
                """,
                "style": {"background": "transparent", "border": "none"},
            }

            vista = pdk.ViewState(
                latitude=lat_centro,
                longitude=lon_centro,
                zoom=9.4,
                pitch=0,
                bearing=0,
            )

            deck = pdk.Deck(
                layers=[capa_circulo, capa_pin, capa_texto],
                initial_view_state=vista,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip=tooltip,
            )

            st.pydeck_chart(deck, height=420)

            # Leyenda chips
            _chips = "".join(
                f"<span style='display:inline-flex;align-items:center;gap:5px;"
                f"background:#FFFFFF;border:1px solid #D8E2EF;border-radius:999px;"
                f"padding:4px 10px;margin:2px 3px;font-size:11px;"
                f"font-weight:600;color:#1A2E44;'>"
                f"<span style='width:8px;height:8px;border-radius:50%;"
                f"background:{color};display:inline-block;'></span>"
                f"{destino}</span>"
                for destino, color in common.COLORES_DESTINO.items()
                if destino in df_deck["nombre_destino"].values
            )
            st.markdown(
                f"<div style='text-align:center;margin-top:6px;'>{_chips}</div>",
                unsafe_allow_html=True,
            )
            st.caption("Hover sobre un punto para ver precio y publicaciones.")

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

# ============================================================
# FILA 2: Precio por tipo de alojamiento | Precio por plataforma
# ============================================================
col_c, col_d = st.columns(2)

with col_c:
    with common.seccion("Precio por tipo de alojamiento", "box_tipo"):
        df_tipo = df_fact.dropna(subset=["precio_noche_usd", "tipo_alojamiento"])
        if df_tipo.empty:
            st.info(
                "No hay datos de 'tipo_alojamiento' para esta combinación "
                "(Booking y Airbnb no exponen este campo — ~73% de nulos "
                "documentado en el Entregable 3)."
            )
        else:
            fig3 = px.box(
                df_tipo,
                x="tipo_alojamiento",
                y="precio_noche_usd",
                color="tipo_alojamiento",
                color_discrete_sequence=common.PALETA_SECUNDARIA,
                labels={
                    "precio_noche_usd": "Precio/noche (USD)",
                    "tipo_alojamiento": "Tipo de alojamiento",
                },
                points="outliers",
            )
            fig3.update_layout(showlegend=False, height=380)
            fig3 = common.estilo_grafico(fig3)
            st.plotly_chart(fig3, width="stretch")

with col_d:
    with common.seccion("Precio promedio por plataforma y destino", "bar_plataforma"):
        df_pivot = (
            df_fact
            .groupby(["nombre_destino", "nombre_plataforma"])["precio_noche_usd"]
            .mean()
            .reset_index()
        )
        fig2 = px.bar(
            df_pivot,
            x="nombre_destino",
            y="precio_noche_usd",
            color="nombre_plataforma",
            color_discrete_map=common.COLORES_PLATAFORMA,
            barmode="group",
            labels={
                "precio_noche_usd": "Precio promedio (USD)",
                "nombre_destino": "Destino",
                "nombre_plataforma": "Plataforma",
            },
        )
        fig2.update_layout(height=380)
        fig2 = common.estilo_grafico(fig2)
        st.plotly_chart(fig2, width="stretch")