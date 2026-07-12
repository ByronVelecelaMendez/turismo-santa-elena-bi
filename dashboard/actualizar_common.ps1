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
    .main .block-container{
        padding-top:1rem;
        padding-left:3rem;
        padding-right:3rem;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
        margin-bottom: 0.15rem;
    }
    hr {
        margin-top: 0.6rem !important;
        margin-bottom: 0.6rem !important;
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
        padding: 16px 20px 6px 20px;
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

    st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# NAVEGACIÓN CON TARJETAS = PÁGINAS REALES (st.page_link)
# ============================================================

def render_nav():
    """Fila de tarjetas de navegación. Cada una es un st.page_link real:
    al hacer clic, Streamlit navega a una URL propia (p. ej.
    /Resumen_General), no solo cambia contenido en la misma página."""
    cols_nav = st.columns(len(PAGINAS) - 1)  # todas menos "Inicio"
    for col, (titulo, ruta) in zip(cols_nav, PAGINAS[1:]):
        with col:
            st.page_link(ruta, label=titulo, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)


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

    st.markdown("<br>", unsafe_allow_html=True)
    return filtro_destino, filtro_plataforma


def render_encabezado_pagina():
    """Llamar al inicio de cada página de contenido: CSS + banner + nav + filtros.
    Devuelve (filtro_destino, filtro_plataforma)."""
    inject_base_css()
    render_banner()
    render_nav()
    return render_filtros()
'@ | Out-File -Encoding utf8 "common.py"
Write-Host "common.py actualizado"