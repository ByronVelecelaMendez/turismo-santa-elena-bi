# Script de instalacion completo - Dashboard multipagina Turismo Santa Elena
# Correr desde DENTRO de la carpeta dashboard/

New-Item -ItemType Directory -Force -Path "pages" | Out-Null

@'
"""
Punto de entrada del dashboard. Usa st.navigation + st.Page (API nativa de
Streamlit para apps multipágina) para que cada sección tenga una URL propia
de verdad (ej. /Resumen_General, /Analisis_de_Precios), en vez de solo
mostrar contenido distinto en una única página.

La navegación por defecto de Streamlit (sidebar) queda oculta
(position="hidden") porque construimos nuestra propia barra de tarjetas
de navegación dentro de cada página (ver common.render_nav()).
"""

import streamlit as st

st.set_page_config(
    page_title="BI Turismo Santa Elena",
    layout="wide",
    initial_sidebar_state="collapsed",
)

paginas = [
    st.Page("pages/0_inicio.py", title="Inicio", default=True),
    st.Page("pages/1_resumen_general.py", title="Resumen General"),
    st.Page("pages/2_analisis_precios.py", title="Análisis de Precios"),
    st.Page("pages/3_valoraciones_plataforma.py", title="Valoraciones por Plataforma"),
    st.Page("pages/4_encuesta_propia.py", title="Encuesta Propia"),
    st.Page("pages/5_datos_fuentes.py", title="Datos y Fuentes"),
]

pg = st.navigation(paginas, position="hidden")
pg.run()
'@ | Out-File -Encoding utf8 "app.py"

@'
"""
Módulo compartido por todas las páginas del dashboard.
Contiene: conexión al DW, funciones de carga de datos (cacheadas),
utilidades, estilos CSS y los componentes de navegación/filtros que se
repiten en cada página (banner, tarjetas de navegación con URL propia,
barra de filtros).
"""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

BASE_DIR = Path(__file__).parent

# Colores oficiales del proyecto
COLORES_DESTINO = {
    "Salinas": "#1f77b4",
    "Montañita": "#2ca02c",
    "Ayangue": "#ff7f0e",
    "La Libertad": "#9467bd",
    "Manglaralto": "#8c564b",
    "Punta Carnero": "#e377c2",
}

DESTINOS_DISPONIBLES = ["Todos", "Salinas", "Montañita", "Ayangue",
                        "La Libertad", "Manglaralto", "Punta Carnero"]
PLATAFORMAS_DISPONIBLES = ["Todas", "Booking", "Airbnb", "KAYAK", "Hostelworld"]

# Páginas del dashboard: (título mostrado, ruta relativa al archivo de entrada app.py)
PAGINAS = [
    ("Inicio", "pages/0_inicio.py"),
    ("Resumen General", "pages/1_resumen_general.py"),
    ("Análisis de Precios", "pages/2_analisis_precios.py"),
    ("Valoraciones por Plataforma", "pages/3_valoraciones_plataforma.py"),
    ("Encuesta Propia", "pages/4_encuesta_propia.py"),
    ("Datos y Fuentes", "pages/5_datos_fuentes.py"),
]


# ============================================================
# UTILIDADES
# ============================================================

def buscar_columna(df: pd.DataFrame, palabra_clave: str):
    """Busca una columna de la encuesta por palabra clave (sin depender
    de escribir el texto exacto de cada pregunta, que viene de Google Forms)."""
    for col in df.columns:
        if palabra_clave.lower() in col.lower():
            return col
    return None


def imagen_segura(ruta, **kwargs):
    """Carga una imagen sin romper la app si el archivo no existe."""
    try:
        if os.path.exists(str(ruta)):
            st.image(str(ruta), **kwargs)
        else:
            st.info(f"(imagen no encontrada: {os.path.basename(str(ruta))})")
    except Exception as e:
        st.info(f"(no se pudo cargar la imagen: {e})")


# ============================================================
# CARGA DE DATOS (todo en vivo desde el Data Warehouse)
# ============================================================

@st.cache_data(ttl=300)
def cargar_precios():
    engine = get_engine()
    return pd.read_sql("SELECT * FROM vw_kpi_precio_promedio_destino", engine)


@st.cache_data(ttl=300)
def cargar_valoraciones():
    engine = get_engine()
    return pd.read_sql("SELECT * FROM vw_kpi_valoracion_promedio_destino", engine)


@st.cache_data(ttl=300)
def cargar_disponibilidad():
    engine = get_engine()
    return pd.read_sql("SELECT * FROM vw_kpi_disponibilidad_turistica", engine)


@st.cache_data(ttl=300)
def cargar_valoracion_por_plataforma():
    engine = get_engine()
    query = """
        SELECT
            d.nombre_destino,
            p.nombre_plataforma,
            ROUND(AVG(f.rating), 2) AS valoracion_promedio,
            COUNT(f.id_hecho) AS publicaciones,
            SUM(f.num_resenas) AS total_resenas
        FROM fact_hospedaje f
        JOIN dim_destino d ON f.id_destino = d.id_destino
        JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
        WHERE f.rating IS NOT NULL
        GROUP BY d.nombre_destino, p.nombre_plataforma
        ORDER BY d.nombre_destino, valoracion_promedio DESC
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=300)
def cargar_encuesta():
    """Lee la tabla fact_encuesta del DW (cargada con cargar_encuesta_a_dw.py).
    Cumple con "consumo directo desde el DW, prohibido usar archivos planos"."""
    engine = get_engine()
    try:
        return pd.read_sql("SELECT * FROM fact_encuesta", engine)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_fact_hospedaje():
    engine = get_engine()
    query = """
        SELECT
            d.nombre_destino, p.nombre_plataforma,
            f.precio_noche_usd, f.rating, f.num_resenas,
            a.tipo_alojamiento
        FROM fact_hospedaje f
        JOIN dim_destino d ON f.id_destino = d.id_destino
        JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
        JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    """
    return pd.read_sql(query, engine)


# ============================================================
# ESTILOS BASE (se inyectan en cada página)
# ============================================================

def inject_base_css():
    st.markdown("""
    <style>
    /* Oculta la barra superior nativa de Streamlit (Deploy, menu, la
       franja de color decorativa) y elimina TODO el espacio reservado
       arriba del contenido. Se usan varios selectores porque Streamlit
       cambia estos nombres entre versiones. */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    div[data-testid="stDecoration"] {
        display: none !important;
    }
    div[data-testid="stToolbar"] {
        display: none !important;
    }
    #MainMenu {
        display: none !important;
    }
    footer {
        display: none !important;
    }
    div[data-testid="stAppViewContainer"] {
        padding-top: 0 !important;
    }
    .main .block-container{
        padding-top:0.3rem !important;
        padding-left:3rem;
        padding-right:3rem;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
        margin-bottom: 0.1rem;
    }
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.3rem !important;
        padding-bottom: 0 !important;
        padding-top: 0 !important;
        font-size: 1.7rem !important;
    }
    /* Streamlit agrega más espacio alrededor de los contenedores con
       borde (st.container(border=True)) que alrededor de elementos
       normales; se recorta ese espacio extra aquí. */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-top: 0 !important;
        margin-bottom: 0.2rem !important;
    }
    div[data-testid="element-container"]:has(> div[data-testid="stVerticalBlockBorderWrapper"]) {
        margin-bottom: 0 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
    }
    hr {
        margin-top: 0.4rem !important;
        margin-bottom: 0.4rem !important;
    }
    div[data-testid="stMetric"] {
        background: #F6FAFF;
        border-radius: 12px;
        padding: 10px 14px;
        border: 1px solid #E3ECF7;
    }
    /* Tarjetas de navegación reales (st.page_link), estilo profesional */
    div[data-testid="stPageLink"] {
        width: 100%;
    }
    div[data-testid="stPageLink"] a {
        width: 100%;
        min-height: 64px;
        border-radius: 10px;
        border: 1px solid #DCE4EE;
        border-top: 3px solid #0B3B70;
        background: #FFFFFF;
        font-weight: 600;
        font-size: 15px;
        color: #1A2E44 !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        text-decoration: none !important;
        box-shadow: 0 1px 3px rgba(11, 59, 112, 0.06);
        transition: all 0.15s ease-in-out;
        padding: 10px 12px;
    }
    div[data-testid="stPageLink"] a:hover {
        border-top: 3px solid #33A1FF;
        background: #F6FAFF;
        box-shadow: 0 3px 10px rgba(11, 59, 112, 0.12);
    }
    div[data-testid="stPageLink"] a p {
        font-size: 15px !important;
        font-weight: 600 !important;
        text-align: center;
    }
    div[data-testid="stSelectbox"] label {
        font-weight: 600;
        color: #0B3B70;
    }
    /* Caja de filtros con fondo agrupado (usa el key="caja_filtros" del container) */
    .st-key-caja_filtros {
        background: #EEF3FA;
        border-radius: 14px;
        padding: 10px 20px 4px 20px;
        border: 1px solid #DCE4EE;
    }
    /* Caja de KPIs agrupados (usa key="caja_kpis" en cada página) */
    .st-key-caja_kpis {
        background: #FFFFFF;
        border-radius: 14px;
        padding: 6px 10px;
        border: 1px solid #E3ECF7;
        box-shadow: 0 2px 10px rgba(11, 59, 112, 0.05);
    }
    /* Encabezado compacto de páginas internas (nav en formato pestaña delgada) */
    .st-key-nav_slim {
        margin-top: 6px;
    }
    .st-key-nav_slim div[data-testid="stPageLink"] a {
        min-height: 34px;
        border-radius: 8px;
        border: none;
        border-bottom: 2px solid transparent;
        background: transparent;
        box-shadow: none;
        font-size: 13px;
        font-weight: 600;
        color: #3A4D63 !important;
        padding: 4px 6px;
    }
    .st-key-nav_slim div[data-testid="stPageLink"] a:hover {
        border-bottom: 2px solid #33A1FF;
        background: transparent;
        box-shadow: none;
        color: #0B3B70 !important;
    }
    .st-key-nav_slim div[data-testid="stPageLink"] a p {
        font-size: 13px !important;
    }
    .st-key-encabezado_compacto {
        background: #FFFFFF;
        border-radius: 14px;
        padding: 8px 20px;
        border: 1px solid #E3ECF7;
        box-shadow: 0 2px 10px rgba(11, 59, 112, 0.05);
    }
    /* Barra de título para secciones de gráficos (estilo "Mapa de destinos") */
    .barra-seccion {
        background: #DCE6F5;
        border-radius: 10px 10px 0 0;
        padding: 8px 16px;
        font-weight: 700;
        color: #0B3B70;
        font-size: 13px;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        margin-bottom: 0;
    }
    .caja-seccion {
        border: 1px solid #E3ECF7;
        border-top: none;
        border-radius: 0 0 10px 10px;
        padding: 8px 12px 10px 12px;
        margin-bottom: 8px;
        background: #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# BANNER (compartido por todas las páginas)
# ============================================================

def render_banner():
    hay_banner = os.path.exists(str(BASE_DIR / "assets" / "banner.png"))
    if hay_banner:
        imagen_segura(BASE_DIR / "assets" / "banner.png", use_container_width=True)
    else:
        col_logo, col_titulo = st.columns([1, 4])
        with col_logo:
            imagen_segura(BASE_DIR / "assets" / "logo_upse.png", width=700)
        with col_titulo:
            st.markdown("""
            <div style="padding-top:10px">
                <h1 style="color:#0B3B70; margin-bottom:0; font-size:42px; font-weight:700;">
                    BI Turismo Santa Elena
                </h1>
                <p style="color:#666; font-size:18px; margin-top:0;">
                    Proyecto Integrador • UPSE 2026-1
                </p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ============================================================
# NAVEGACIÓN CON TARJETAS = PÁGINAS REALES (st.page_link)
# ============================================================

def render_nav():
    """Fila de tarjetas de navegación GRANDES (solo para la página de
    Inicio, replica la Imagen 1). Cada una es un st.page_link real:
    al hacer clic, Streamlit navega a una URL propia (p. ej.
    /Resumen_General), no solo cambia contenido en la misma página."""
    with st.container(key="nav_cards"):
        cols_nav = st.columns(len(PAGINAS) - 1)  # todas menos "Inicio"
        for col, (titulo, ruta) in zip(cols_nav, PAGINAS[1:]):
            with col:
                st.page_link(ruta, label=titulo, use_container_width=True)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ============================================================
# ENCABEZADO COMPACTO (páginas de contenido, no la de Inicio)
# ============================================================

def render_encabezado_compacto(pagina_activa: str = ""):
    """Encabezado delgado para páginas de contenido: logo/título pequeño
    a la izquierda + pestañas de navegación a la derecha (con la pestaña
    activa resaltada en forma de píldora), todo en una sola franja."""
    with st.container(key="encabezado_compacto"):
        col_titulo, col_nav = st.columns([1.3, 3.7])
        with col_titulo:
            st.markdown(
                "<div style='padding-top:2px;'>"
                "<span style='color:#0B3B70; font-weight:800; font-size:19px;'>"
                "BI Turismo Santa Elena</span><br>"
                "<span style='color:#5A7089; font-size:11px; font-weight:600; "
                "letter-spacing:0.5px;'>PROYECTO INTEGRADOR · UPSE 2026-1</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col_nav:
            with st.container(key="nav_slim"):
                # "Inicio" se muestra al final, como el ícono de casa de la referencia
                orden = PAGINAS[1:] + [PAGINAS[0]]
                cols_nav = st.columns(len(orden))
                slugs_activos = []
                for i, (col, (titulo, ruta)) in enumerate(zip(cols_nav, orden)):
                    slug = f"navitem_{i}"
                    with col:
                        with st.container(key=slug):
                            st.page_link(ruta, label=titulo, use_container_width=True)
                    if titulo == pagina_activa:
                        slugs_activos.append(slug)

                for slug in slugs_activos:
                    st.markdown(f"""
                    <style>
                    .st-key-{slug} div[data-testid="stPageLink"] a {{
                        background: #DCEAFB !important;
                        border-radius: 999px !important;
                        color: #0B3B70 !important;
                        font-weight: 700 !important;
                        border-bottom: 2px solid transparent !important;
                    }}
                    </style>
                    """, unsafe_allow_html=True)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


def render_seccion(titulo: str):
    """Dibuja la barra de título tipo tarjeta (fondo celeste) usada para
    encabezar cada sección de gráfico, imitando el estilo 'Mapa de
    destinos turísticos' de la referencia. Debe cerrarse llamando a
    cerrar_seccion() después de dibujar el contenido."""
    st.markdown(f'<div class="barra-seccion">{titulo}</div>', unsafe_allow_html=True)
    st.markdown('<div class="caja-seccion">', unsafe_allow_html=True)


def cerrar_seccion():
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# BARRA DE FILTROS (comparte estado entre páginas vía session_state)
# ============================================================

def render_filtros():
    with st.container(border=True, key="caja_filtros"):
        st.markdown(
            "<p style='font-size:12px; font-weight:700; color:#5A7089; "
            "letter-spacing:1px; margin-bottom:6px;'>BUSCAR POR</p>",
            unsafe_allow_html=True,
        )
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            filtro_destino = st.selectbox(
                "Destino", DESTINOS_DISPONIBLES, key="filtro_destino"
            )
        with col_f2:
            filtro_plataforma = st.selectbox(
                "Plataforma", PLATAFORMAS_DISPONIBLES, key="filtro_plataforma"
            )
        with col_f3:
            st.markdown(
                "<div style='padding-top:28px; color:#5A7089; font-size:13px;'>"
                "Datos extraídos: junio 2026 · Temporada: Baja<br>"
                "Fuentes: Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · Encuesta"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    return filtro_destino, filtro_plataforma


def render_encabezado_pagina(pagina_activa: str = ""):
    """Llamar al inicio de cada página de CONTENIDO (no Inicio): CSS +
    encabezado compacto (con la pestaña 'pagina_activa' resaltada) +
    filtros. Devuelve (filtro_destino, filtro_plataforma)."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)
    return render_filtros()
'@ | Out-File -Encoding utf8 "common.py"

@'
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import common

common.inject_base_css()
common.render_banner()
common.render_nav()
'@ | Out-File -Encoding utf8 "pages\0_inicio.py"

@'
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import plotly.express as px
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Resumen General")

st.title("Resumen General — Turismo Santa Elena")
st.markdown(
    "Visión consolidada de los 6 destinos turísticos de la provincia "
    "de Santa Elena, calculada en vivo a partir de las publicaciones "
    "de hospedaje activas en 4 plataformas digitales."
)

df_precios = common.cargar_precios()
df_val = common.cargar_valoraciones()

if filtro_destino != "Todos":
    df_precios = df_precios[df_precios["nombre_destino"] == filtro_destino]
    df_val = df_val[df_val["nombre_destino"] == filtro_destino]

# KPIs globales — CALCULADOS EN VIVO
total_publicaciones = int(df_precios["total_publicaciones"].sum())

with st.container(border=True, key="caja_kpis"):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total publicaciones", f"{total_publicaciones:,}")
    col2.metric("Precio promedio/noche", f"${df_precios['precio_promedio_noche_usd'].mean():.2f}")
    col3.metric("Valoración promedio", f"{df_val['valoracion_promedio'].mean():.2f}/5.00")
    col4.metric("Total reseñas", f"{int(df_val['total_resenas'].sum()):,}")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILA ÚNICA DE 3 COLUMNAS: Mapa | Precio por destino | Valoración por destino
# ============================================================
col_mapa, col_precio, col_val = st.columns(3)

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

with col_mapa:
    common.render_seccion("Distribución geográfica de destinos")
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
        size_max=26,
        mapbox_style="open-street-map",
        labels={
            "valoracion_promedio": "Valoración",
            "precio_promedio_noche_usd": "Precio/noche USD",
            "total_resenas": "Total reseñas"
        }
    )
    fig_mapa.update_layout(
        height=380,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="Valoración<br>(1-5)", thickness=12),
        mapbox=dict(
            zoom=11.3 if len(df_mapa) == 1 else 9.6,
            center=dict(lat=df_mapa["lat"].mean(), lon=df_mapa["lon"].mean()),
        ),
    )
    st.plotly_chart(fig_mapa, use_container_width=True)
    st.caption(
        "Color = valoración promedio (rojo: más baja, verde: más alta). "
        "Tamaño del punto = cantidad de publicaciones activas."
    )
    common.cerrar_seccion()

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
    fig.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig, use_container_width=True)
    common.cerrar_seccion()

with col_val:
    common.render_seccion("Valoración promedio por destino (1-5)")
    fig2 = px.bar(
        df_val.sort_values("valoracion_promedio", ascending=True),
        x="valoracion_promedio",
        y="nombre_destino",
        orientation="h",
        color="nombre_destino",
        color_discrete_map=common.COLORES_DESTINO,
        text="valoracion_promedio",
        labels={"valoracion_promedio": "Valoración promedio", "nombre_destino": "Destino"},
    )
    fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig2.update_layout(showlegend=False, height=380, xaxis_range=[0, 5.7])
    st.plotly_chart(fig2, use_container_width=True)
    common.cerrar_seccion()
'@ | Out-File -Encoding utf8 "pages\1_resumen_general.py"

@'
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
df_precios = common.cargar_precios()

if filtro_destino != "Todos":
    df_fact = df_fact[df_fact["nombre_destino"] == filtro_destino]
    df_precios = df_precios[df_precios["nombre_destino"] == filtro_destino]
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
        size_max=26,
        mapbox_style="open-street-map",
        labels={"precio_promedio_noche_usd": "Precio (USD)"},
    )
    fig_mapa.update_layout(
        height=380,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="Precio<br>(USD)", thickness=12),
        mapbox=dict(
            zoom=11.3 if len(df_mapa) == 1 else 9.6,
            center=dict(lat=df_mapa["lat"].mean(), lon=df_mapa["lon"].mean()),
        ),
    )
    st.plotly_chart(fig_mapa, use_container_width=True)
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
'@ | Out-File -Encoding utf8 "pages\2_analisis_precios.py"

@'
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
'@ | Out-File -Encoding utf8 "pages\3_valoraciones_plataforma.py"

@'
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
'@ | Out-File -Encoding utf8 "pages\4_encuesta_propia.py"

@'
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import common

filtro_destino, filtro_plataforma = common.render_encabezado_pagina("Datos y Fuentes")

st.title("Datos y Fuentes del Proyecto")
st.markdown(
    "Arquitectura de datos y procedencia de la información consumida "
    "por este dashboard, en cumplimiento con la documentación exigida "
    "para el Entregable 5."
)

common.render_seccion("8 fuentes heterogéneas integradas")
fuentes = pd.DataFrame([
    {"Fuente": "Booking.com", "Tipo": "Web Scraping", "Dato extraído": "Precios, ratings, reseñas"},
    {"Fuente": "Airbnb", "Tipo": "Web Scraping", "Dato extraído": "Precios, tipo de alojamiento"},
    {"Fuente": "KAYAK", "Tipo": "Web Scraping", "Dato extraído": "Precios, rating (0-10 normalizado)"},
    {"Fuente": "Hostelworld", "Tipo": "Web Scraping", "Dato extraído": "Precios, rating, reseñas"},
    {"Fuente": "OpenWeather API", "Tipo": "API Pública", "Dato extraído": "Temperatura, clima por destino"},
    {"Fuente": "MINTUR Ecuador", "Tipo": "Archivo CSV/XLSX", "Dato extraído": "Catastro turístico oficial"},
    {"Fuente": "Google Trends", "Tipo": "API Pública", "Dato extraído": "Tendencias de búsqueda"},
    {"Fuente": "Encuesta propia", "Tipo": "Fuente propia", "Dato extraído": "Percepción de 111 viajeros"},
])
st.dataframe(fuentes, use_container_width=True, hide_index=True)
common.cerrar_seccion()

st.markdown("<br>", unsafe_allow_html=True)

common.render_seccion("Arquitectura del pipeline (capas)")
st.markdown("""
```
Fuentes externas (scraping + APIs + CSV + encuesta)
        ↓
Zona Raw (JSON/CSV originales, inmutables, con timestamp)
        ↓
Zona Staging (limpieza, homologación, deduplicación)
        ↓
Data Warehouse — PostgreSQL (Star Schema)
   FACT_HOSPEDAJE + 5 dimensiones
        ↓
Este Dashboard (Streamlit) — consumo 100% en vivo vía SQL
```
""")
common.cerrar_seccion()

st.markdown("<br>", unsafe_allow_html=True)

common.render_seccion("Modelo dimensional (Star Schema)")
st.markdown(
    "- **Tabla de hechos:** `fact_hospedaje` (precio, rating, ocupación, reseñas)\n"
    "- **Dimensiones:** `dim_destino`, `dim_alojamiento`, `dim_plataforma`, "
    "`dim_temporada`, `dim_fecha`\n"
    "- **Registros actuales en el DW:** consultados en vivo abajo"
)

try:
    conteos_sql = """
        SELECT 'fact_hospedaje' AS tabla, COUNT(*) AS registros FROM fact_hospedaje
        UNION ALL SELECT 'dim_destino', COUNT(*) FROM dim_destino
        UNION ALL SELECT 'dim_alojamiento', COUNT(*) FROM dim_alojamiento
        UNION ALL SELECT 'dim_plataforma', COUNT(*) FROM dim_plataforma
        UNION ALL SELECT 'dim_temporada', COUNT(*) FROM dim_temporada
        UNION ALL SELECT 'dim_fecha', COUNT(*) FROM dim_fecha
        UNION ALL SELECT 'fact_encuesta', COUNT(*) FROM fact_encuesta
    """
    engine = common.get_engine()
    conteos_df = pd.read_sql(conteos_sql, engine)
    st.dataframe(conteos_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(f"No se pudo consultar el conteo de tablas en vivo: {e}")
common.cerrar_seccion()

st.markdown("<br>", unsafe_allow_html=True)

common.render_seccion("Limitaciones documentadas")
st.markdown(
    "- Cobertura temporal única: todas las extracciones de hospedaje "
    "corresponden a temporada baja (junio 2026).\n"
    "- Campos `categoria_estrellas` y `capacidad` sin poblar en "
    "`dim_alojamiento` (ninguna de las 4 plataformas de scraping los expone).\n"
    "- Hostelworld tiene cobertura parcial: no posee listados propios "
    "para Punta Carnero y La Libertad.\n"
    "- La encuesta usa muestra de conveniencia (111 respuestas, no "
    "probabilística)."
)
common.cerrar_seccion()
'@ | Out-File -Encoding utf8 "pages\5_datos_fuentes.py"

Write-Host "Listo: CSS reforzado con mas selectores e !important."