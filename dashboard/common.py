"""
Módulo compartido por todas las páginas del dashboard.
Contiene: conexión al DW, funciones de carga de datos (cacheadas),
utilidades, estilos CSS y los componentes de navegación/filtros/KPIs
que se repiten en cada página (banner, tabs, barra de filtros compacta,
tarjetas KPI con icono).
"""

import base64
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

BASE_DIR = Path(__file__).parent

# Paleta profesional por destino — variaciones de azul/gris/teal
# derivadas del azul institucional (#0B3B70), en vez de colores
# genéricos tipo Excel. El rojo se reserva exclusivamente para alertas
# (ver render_seccion / cajas de insight), así no compite visualmente.
COLORES_DESTINO = {
    "Salinas": "#0B3B70",
    "Montañita": "#1B6FC9",
    "Ayangue": "#4A9FD8",
    "La Libertad": "#5B7C99",
    "Manglaralto": "#8FA6BC",
    "Punta Carnero": "#2E8B8B",
}

# Paleta secundaria para series que NO representan un destino
# (plataforma, tipo de alojamiento, etc.) — misma familia visual que
# COLORES_DESTINO, para que todo el dashboard se sienta parte de un
# solo sistema de diseño en vez de mezclar colores sueltos de Plotly.
PALETA_SECUNDARIA = ["#0B3B70", "#1B6FC9", "#2E8B8B", "#5B7C99", "#8FA6BC", "#C9A227"]

# Colores fijos por plataforma (los mismos en TODOS los gráficos,
# para que Airbnb/Booking/KAYAK/Hostelworld se lean igual en cada página)
COLORES_PLATAFORMA = {
    "Airbnb": "#0B3B70",
    "Booking": "#1B6FC9",
    "KAYAK": "#5B7C99",
    "Hostelworld": "#2E8B8B",
}

# Escala para valoraciones (semáforo suavizado acorde a la paleta:
# rojo solo como alerta, verde institucional en el extremo bueno)
ESCALA_VALORACION = ["#C0392B", "#E8C547", "#1E8E5A"]

# Escala para precios (monocromática de marca: claro = barato)
ESCALA_PRECIO = ["#DCEAFB", "#0B3B70"]

# Coordenadas oficiales de los 6 destinos (única fuente de verdad —
# antes estaban duplicadas y desincronizadas entre api/config.py,
# 1_resumen_general.py y 2_analisis_precios.py).
COORDENADAS_DESTINO = {
    "Salinas": (-2.2145, -80.9515),
    "La Libertad": (-2.2275, -80.9101),
    "Punta Carnero": (-2.2167, -80.9667),
    "Montañita": (-1.8333, -80.7667),
    "Ayangue": (-1.9667, -80.7500),
    "Manglaralto": (-1.8667, -80.7333),
}

DESTINOS_DISPONIBLES = ["Todos", "Salinas", "Montañita", "Ayangue",
                        "La Libertad", "Manglaralto", "Punta Carnero"]
PLATAFORMAS_DISPONIBLES = ["Todas", "Booking", "Airbnb", "KAYAK", "Hostelworld"]

# La encuesta (fact_encuesta.destino_homologado) guarda slugs sin tildes
# generados en etl/procesar_encuesta.py — no el nombre "bonito" que usan
# las demás tablas del DW. Este mapeo permite filtrar la encuesta por el
# mismo selector de Destino que usa el resto del dashboard.
DESTINO_A_SLUG_ENCUESTA = {
    "Salinas": "salinas",
    "Montañita": "montanita",
    "Ayangue": "ayangue",
    "La Libertad": "la_libertad",
    "Manglaralto": "manglaralto",
    "Punta Carnero": "punta_carnero",
}

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
    html, body, .stApp {
        margin: 0 !important;
        padding: 0 !important;
        background: #F4F6F8 !important;
        height: auto !important;
        min-height: 0 !important;
    }
    div[data-testid="stAppViewContainer"] {
        background: #F4F6F8 !important;
        padding-top: 0 !important;
        height: auto !important;
        min-height: 0 !important;
    }
    div[data-testid="stMain"] {
        height: auto !important;
        min-height: 0 !important;
    }
    div[data-testid="stMainBlockContainer"] {
        padding-top: 0.45rem !important;
        padding-bottom: 0.6rem !important;
        background: transparent !important;
        height: auto !important;
        min-height: 0 !important;
    }
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 0.45rem !important;
        padding-bottom: 0.6rem !important;
        background: transparent !important;
        height: auto !important;
        min-height: 0 !important;
    }
    iframe {
        display: block;
    }
    
                div[data-testid="stImage"] {
        margin-bottom: 0 !important;
    }
    div[data-testid="stImage"] img {
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(11, 59, 112, 0.14);
    }
                
    /* Oculta la barra superior nativa de Streamlit (Deploy, menu, la
       franja de color decorativa) y elimina TODO el espacio reservado
       arriba del contenido. Se usan varios selectores porque Streamlit
       cambia estos nombres entre versiones. */
    header[data-testid="stHeader"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }

    .main .block-container{
        padding-top: 0.1rem !important;
        padding-left: 2.6rem;
        padding-right: 2.6rem;
        max-width: 1400px;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
    }

    /* ============================================================
       JERARQUÍA TIPOGRÁFICA
       ============================================================ */
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.2rem !important;
        padding: 0 !important;
        font-size: 1.55rem !important;
        font-weight: 800 !important;
        color: #0B2E52 !important;
        letter-spacing: -0.2px;
    }
    /* Texto de subtítulo debajo del h1 (st.markdown descriptivo de cada página) */
    div[data-testid="stMarkdownContainer"] > p {
        color: #5A7089;
        font-size: 13.5px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-top: 0 !important;
        margin-bottom: 0.2rem !important;
    }
    div[data-testid="element-container"]:has(> div[data-testid="stVerticalBlockBorderWrapper"]) {
        margin-bottom: 0 !important;
    }
    hr {
        margin-top: 0.35rem !important;
        margin-bottom: 0.35rem !important;
        border-color: #D8E2EF !important;
    }

    /* ============================================================
       BARRA DE NAVEGACIÓN HORIZONTAL (solo página de Inicio)
       ============================================================ */
    .st-key-nav_cards {
        background: linear-gradient(135deg, #123F78 0%, #1B5FA8 50%, #2F7FD1 100%);
        border-radius: 18px;
        padding: 8px 10px;
        box-shadow: 0 6px 20px rgba(11, 59, 112, 0.24);
        position: relative;
        overflow: hidden;
    }
    .st-key-nav_cards::before {
        content: "";
        position: absolute;
        top: -50px;
        right: -30px;
        width: 220px;
        height: 220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0) 70%);
        pointer-events: none;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] { width: 100%; position: relative; z-index: 1; }
    .st-key-nav_cards div[data-testid="stPageLink"] a {
        width: 100%;
        min-height: 58px;
        border-radius: 13px;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        background: rgba(255, 255, 255, 0.06) !important;
        color: #EAF3FF !important;
        text-decoration: none !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        transition: all 0.22s ease-in-out;
        padding: 8px 10px;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 9px;
        border-bottom: 3px solid transparent;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a:hover {
        background: rgba(255, 255, 255, 0.13) !important;
        border-bottom: 3px solid #8FD1F5;
        border-color: rgba(255, 255, 255, 0.18) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 3px 8px rgba(0, 0, 0, 0.10) !important;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a [data-testid="stIconMaterial"] {
        font-size: 19px !important;
        color: #9FC6EE !important;
        line-height: 1;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a p {
        margin: 0 !important;
        color: #EAF3FF !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        white-space: nowrap;
    }
    .st-key-nav_cards div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:not(:last-child) {
        border-right: 1px solid rgba(255, 255, 255, 0.14);
    }

    /* Tarjetas de navegación reales (st.page_link), estilo profesional
       — se usa en páginas internas que NO son la de Inicio */
    div[data-testid="stPageLink"] { width: 100%; }
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

    /* ============================================================
       BARRA DE FILTROS — versión compacta de una sola fila
       ============================================================ */
    div[data-testid="stSelectbox"] label { display: none; }
    .st-key-caja_filtros {
        background: linear-gradient(90deg, #0B3B70 0%, #123F78 100%);
        border-radius: 10px;
        padding: 7px 18px;
        box-shadow: 0 3px 10px rgba(11, 59, 112, 0.16);
    }
    .st-key-caja_filtros label { display: none !important; }
    .st-key-caja_filtros div[data-testid="stSelectbox"] {
        margin-bottom: 0 !important;
    }
    .st-key-caja_filtros div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.96) !important;
        border-radius: 7px !important;
        border: none !important;
        min-height: 32px !important;
    }
    .st-key-caja_filtros div[data-baseweb="select"] {
        font-size: 12.5px !important;
    }

    /* ============================================================
       TARJETAS KPI CUSTOM
       ============================================================ */
    .kpi-fila {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        background: #FFFFFF;
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(11, 59, 112, 0.12), 0 2px 6px rgba(11, 59, 112, 0.06);
        margin-bottom: 4px;
    }
    .kpi-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 10px;
        border-left: 1px solid #EDF1F6;
    }
    .kpi-item:first-child {
        border-left: none;
    }
    .kpi-icono {
        width: 42px;
        height: 42px;
        min-width: 42px;
        border-radius: 12px;
        background: linear-gradient(135deg, #123F78, #2F7FD1);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .kpi-icono svg { display: block; }
    .kpi-texto { min-width: 0; }
    .kpi-etiqueta {
        color: #7A8CA0;
        font-size: 12.5px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        white-space: nowrap;
    }
    .kpi-valor {
        color: #16233A;
        font-size: 24px;
        font-weight: 800;
        line-height: 1.3;
        white-space: nowrap;
    }
    .kpi-delta {
        display: flex;
        align-items: center;
        gap: 2px;
        font-size: 11.5px;
        font-weight: 700;
        margin-top: 1px;
    }
    .kpi-delta svg { display: block; }

    /* Encabezado compacto de páginas internas (nav en formato pestaña delgada) */
    .st-key-nav_slim { margin-top: 6px; }
    .st-key-nav_slim div[data-testid="stPageLink"] a {
        min-height: 32px;
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
        font-size: 12.5px !important;
        white-space: normal;
        line-height: 1.15;
    }
    .st-key-encabezado_compacto {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 6px 20px;
        border: 1px solid #D8E2EF;
        box-shadow: 0 3px 10px rgba(11, 59, 112, 0.08);
    }

    /* ============================================================
       TARJETAS DE SECCIÓN (contenedor real con key sec_*)
       El gráfico queda DENTRO de la tarjeta blanca, junto con su
       barra de título azul.
       ============================================================ */
    div[class*="st-key-sec_"] {
        background: #FFFFFF;
        border: 1px solid #D8E2EF;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(11, 59, 112, 0.09);
        padding: 0 14px 14px 14px;
        margin-bottom: 14px;
    }
    div[class*="st-key-sec_"] .barra-seccion {
        margin: 0 -14px 10px -14px;
    }
    .barra-seccion {
        background: linear-gradient(90deg, #0B3B70 0%, #1B6FC9 100%);
        border-radius: 12px 12px 0 0;
        padding: 9px 16px;
        font-weight: 700;
        color: #FFFFFF;
        font-size: 12.5px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# BANNER (compartido por todas las páginas)
# ============================================================

def render_banner():
    hay_banner = os.path.exists(str(BASE_DIR / "assets" / "banner.png"))
    if hay_banner:
        st.markdown(
            "<div style='max-width:1100px; margin:0 auto;'>",
            unsafe_allow_html=True,
        )
        imagen_segura(BASE_DIR / "assets" / "banner.png", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
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

    st.markdown("<div style='height:0px;'></div>", unsafe_allow_html=True)


def render_banner_sin_foto():
    """Banner alternativo 100% generado en CSS/HTML, sin foto de stock."""
    hay_logo = os.path.exists(str(BASE_DIR / "assets" / "logo_upse.png"))

    st.markdown(
        """
        <style>
        .hero-banner {
            max-width: 1100px; margin: 0 auto; border-radius: 18px;
            overflow: hidden; position: relative;
            background: linear-gradient(135deg, #0B3B70 0%, #123F78 45%, #1B6FC9 100%);
            box-shadow: 0 10px 30px rgba(11, 59, 112, 0.28);
        }
        .hero-banner::after {
            content: ""; position: absolute; top: -60px; right: -60px;
            width: 320px; height: 320px; border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0) 70%);
            pointer-events: none;
        }
        .hero-topbar {
            display: flex; align-items: center; gap: 14px;
            background: rgba(255, 255, 255, 0.06); padding: 14px 40px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            position: relative; z-index: 2;
        }
        .hero-topbar-text { line-height: 1.25; }
        .hero-topbar-text .titulo { color: #FFFFFF; font-weight: 700; font-size: 16px; }
        .hero-topbar-text .subtitulo { color: #A9C7E8; font-weight: 500; font-size: 11.5px; letter-spacing: 0.6px; }
        .hero-main { padding: 40px 44px 48px 44px; position: relative; z-index: 2; }
        .hero-eyebrow { color: #8FC3F0; font-weight: 500; font-size: 12px; letter-spacing: 3.5px; text-transform: uppercase; }
        .hero-title {
            color: #FFFFFF !important; font-size: 46px !important; font-weight: 800 !important;
            margin: 12px 0 4px 0 !important; padding: 0 !important; line-height: 1.12 !important;
        }
        .hero-title .accent { color: #7EC1F2 !important; font-weight: 300 !important; }
        .hero-sub { color: #C9DEF5; font-size: 15px; font-weight: 400; margin-top: 10px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_html = ""
    if hay_logo:
        with open(BASE_DIR / "assets" / "logo_upse.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_b64}' style='width:38px;height:38px;object-fit:contain;'/>"

    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-topbar">
                {logo_html}<div class="hero-topbar-text">
                    <div class="titulo">BI TURISMO SANTA ELENA</div>
                    <div class="subtitulo">PROYECTO INTEGRADOR &middot; UPSE 2026-1</div>
                </div>
            </div>
            <div class="hero-main">
                <div class="hero-eyebrow">Panel de control BI de</div>
                <h1 class="hero-title">
                    Hospedaje y Turismo<br>
                    <span class="accent">en Santa Elena</span>
                </h1>
                <p class="hero-sub">
                    Plataforma de Inteligencia de Negocios para el sector turístico
                    de la provincia de Santa Elena, Ecuador
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ============================================================
# NAVEGACIÓN CON TABS = PÁGINAS REALES (st.page_link)
# ============================================================

ICONOS_NAV = {
    "Resumen General": "bar_chart",
    "Análisis de Precios": "payments",
    "Valoraciones por Plataforma": "star",
    "Encuesta Propia": "donut_large",
    "Datos y Fuentes": "database",
}


def render_nav():
    """Barra de navegación horizontal continua (solo página de Inicio)."""
    with st.container(key="nav_cards"):
        cols_nav = st.columns(len(PAGINAS) - 1)
        for col, (titulo, ruta) in zip(cols_nav, PAGINAS[1:]):
            with col:
                icono = ICONOS_NAV.get(titulo, "circle")
                st.page_link(
                    ruta,
                    label=titulo,
                    icon=f":material/{icono}:",
                    width="stretch",
                )

    st.markdown("<div style='height:0px;'></div>", unsafe_allow_html=True)


# ============================================================
# ENCABEZADO COMPACTO (páginas de contenido, no la de Inicio)
# ============================================================

NAV_LABELS_CORTOS = {
    "Resumen General": "Resumen General",
    "Análisis de Precios": "Análisis de Precios",
    "Valoraciones por Plataforma": "Valoraciones",
    "Encuesta Propia": "Encuesta Propia",
    "Datos y Fuentes": "Datos y Fuentes",
    "Inicio": "Inicio",
}


def render_encabezado_compacto(pagina_activa: str = ""):
    """Encabezado delgado: logo/título pequeño a la izquierda + tabs a
    la derecha (con la pestaña activa resaltada), en una sola franja."""
    with st.container(key="encabezado_compacto"):
        col_titulo, col_nav = st.columns([1.2, 3.8])
        with col_titulo:
            st.markdown(
                "<div style='padding-top:1px;'>"
                "<span style='color:#0B3B70; font-weight:800; font-size:17px;'>"
                "BI Turismo Santa Elena</span><br>"
                "<span style='color:#8697A8; font-size:10.5px; font-weight:600; "
                "letter-spacing:0.4px;'>PROYECTO INTEGRADOR · UPSE 2026-1</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col_nav:
            with st.container(key="nav_slim"):
                orden = PAGINAS[1:] + [PAGINAS[0]]
                cols_nav = st.columns(len(orden))
                slugs_activos = []
                for i, (col, (titulo, ruta)) in enumerate(zip(cols_nav, orden)):
                    slug = f"navitem_{i}"
                    with col:
                        with st.container(key=slug):
                            etiqueta = NAV_LABELS_CORTOS.get(titulo, titulo)
                            st.page_link(ruta, label=etiqueta, width="stretch")
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

    st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)


# ============================================================
# TARJETAS KPI (icono + valor grande + etiqueta + delta opcional)
# ============================================================

# Iconos SVG inline (no dependen de fuentes externas ni de que Streamlit
# permita cargar recursos de terceros — por eso se reemplazó el intento
# anterior con Material Symbols vía Google Fonts, que Streamlit bloquea).
_ICONOS_SVG = {
    "bar_chart": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="20" x2="6" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="18" y1="20" x2="18" y2="14"/></svg>',
    "payments": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>',
    "star": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="{c}"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>',
    "reviews": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "home_work": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/></svg>',
    "map": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3L3 5v16l6-2 6 2 6-2V3l-6 2-6-2z"/><line x1="9" y1="3" x2="9" y2="19"/><line x1="15" y1="5" x2="15" y2="21"/></svg>',
    "database": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/></svg>',
    "assignment_turned_in": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v3H9z"/><path d="M9 13l2 2 4-4"/></svg>',
    "thumb_up": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
    "arrow_downward": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>',
    "arrow_upward": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>',
    "trending_flat": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="14 6 20 12 14 18"/></svg>',
}


def _icono_svg(nombre: str, color: str = "#FFFFFF", size: int = 21) -> str:
    """Devuelve el markup SVG de un icono, ya coloreado y dimensionado.
    Si el nombre no existe en el set, usa un icono genérico de respaldo."""
    plantilla = _ICONOS_SVG.get(nombre, _ICONOS_SVG["bar_chart"])
    return plantilla.format(s=size, c=color)


def render_kpis(items):
    """Dibuja una fila de tarjetas KPI custom (icono + valor + etiqueta
    + delta opcional), todas dentro de una sola tarjeta contenedora.

    items: lista de dicts con:
      icono (str)  -> nombre de Material Symbol, ej. "bar_chart"
      etiqueta (str)
      valor (str)  -> ya formateado, ej. "$108.14"
      delta (str, opcional) -> ya formateado con signo, ej. "+3.20 vs. promedio"
      delta_modo (str, opcional) -> "normal" (verde/rojo según signo) o
                                     "off" (gris, sin connotación buena/mala)
    """
    html_items = []
    for it in items:
        delta = it.get("delta")
        delta_html = ""
        if delta:
            es_positivo = not str(delta).strip().startswith("-")
            modo = it.get("delta_modo", "normal")
            if modo == "off":
                color_delta = "#8697A8"
                icono_delta = "trending_flat"
            else:
                color_delta = "#1E8E5A" if es_positivo else "#C0392B"
                icono_delta = "arrow_upward" if es_positivo else "arrow_downward"
            delta_html = (
                f"<div class='kpi-delta' style='color:{color_delta};'>"
                f"{_icono_svg(icono_delta, color=color_delta, size=13)}{delta}</div>"
            )
        # HTML de cada tarjeta construido en una sola línea continua (sin
        # saltos de línea internos): si delta_html quedara vacío, una
        # línea en blanco en medio del bloque hace que el HTML se corte
        # y el resto se muestre como texto plano en vez de renderizarse.
        item_html = (
            "<div class='kpi-item'>"
            f"<div class='kpi-icono'>{_icono_svg(it['icono'], color='#FFFFFF', size=21)}</div>"
            "<div class='kpi-texto'>"
            f"<div class='kpi-etiqueta'>{it['etiqueta']}</div>"
            f"<div class='kpi-valor'>{it['valor']}</div>"
            f"{delta_html}"
            "</div>"
            "</div>"
        )
        html_items.append(item_html)

    st.markdown(
        "<div class='kpi-fila'>" + "".join(html_items) + "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# ESTILO COMPARTIDO PARA GRÁFICOS PLOTLY
# ============================================================

def estilo_grafico(fig):
    """Aplica estilo visual consistente (tipografía, fondo transparente,
    cuadrícula suave, tooltips en la paleta de marca) a cualquier figura
    de Plotly del dashboard. Llamar justo antes de st.plotly_chart().

    Nota: title_text="" elimina el título interno de Plotly (que salía
    como "undefined" cuando no estaba definido) — el título de cada
    gráfico lo lleva la barra azul de su tarjeta de sección."""
    fig.update_layout(
        title_text="",
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Arial, sans-serif", color="#1A2E44", size=12),
        title_font=dict(color="#0B3B70", size=14),
        legend=dict(
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=11, color="#3A4D63"),
        ),
        hoverlabel=dict(
            bgcolor="#0B3B70",
            font_color="#FFFFFF",
            font_size=12,
            bordercolor="#0B3B70",
        ),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor="#EAF0F8", gridwidth=1,
        zeroline=False, linecolor="#D8E2EF",
        title_font=dict(size=11, color="#5A7089"),
        tickfont=dict(size=10, color="#5A7089"),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#EAF0F8", gridwidth=1,
        zeroline=False, linecolor="#D8E2EF",
        title_font=dict(size=11, color="#5A7089"),
        tickfont=dict(size=10, color="#5A7089"),
    )
    return fig


# ============================================================
# TARJETAS DE SECCIÓN
# ============================================================

@contextmanager
def seccion(titulo: str, key: str):
    """Tarjeta de sección real: barra de título azul + contenido DENTRO
    de la misma tarjeta blanca. Reemplaza a render_seccion/cerrar_seccion,
    que no funcionaban porque Streamlit auto-cierra el HTML de cada
    st.markdown y el gráfico quedaba fuera del div (por eso se veían
    cajas blancas vacías bajo cada barra de título).

    Uso:
        with common.seccion("PRECIO PROMEDIO POR DESTINO", "precio_destino"):
            st.plotly_chart(fig, width="stretch")

    key debe ser único dentro de cada página (sin espacios ni tildes).
    """
    with st.container(key=f"sec_{key}"):
        st.markdown(f'<div class="barra-seccion">{titulo}</div>',
                    unsafe_allow_html=True)
        yield


def render_seccion(titulo: str):
    """OBSOLETA — usar `with common.seccion(titulo, key):` en su lugar.
    Se mantiene para que las páginas no migradas no se rompan mientras
    tanto: dibuja solo la cinta de título (sin caja rota debajo)."""
    st.markdown(f'<div class="barra-seccion" style="border-radius:10px;">{titulo}</div>',
                unsafe_allow_html=True)


def cerrar_seccion():
    """OBSOLETA — ya no hace nada. Usar `with common.seccion(...)`."""
    pass


# ============================================================
# BARRA DE FILTROS COMPACTA — una sola fila
# (comparte estado entre páginas vía session_state)
# ============================================================

def render_filtros():
    with st.container(key="caja_filtros"):
        col_lbl, col_f1, col_f2, col_info = st.columns([0.62, 1.05, 1.05, 3.6])
        with col_lbl:
            st.markdown(
                "<div style='padding-top:6px; color:#BFDCF7; font-size:10.5px; "
                "font-weight:700; letter-spacing:0.8px;'>BUSCAR POR</div>",
                unsafe_allow_html=True,
            )
        with col_f1:
            filtro_destino = st.selectbox(
                "Destino", DESTINOS_DISPONIBLES, key="filtro_destino",
                label_visibility="collapsed",
            )
        with col_f2:
            filtro_plataforma = st.selectbox(
                "Plataforma", PLATAFORMAS_DISPONIBLES, key="filtro_plataforma",
                label_visibility="collapsed",
            )
        with col_info:
            st.markdown(
                "<div style='padding-top:6px; color:#C9DEF5; font-size:11px; text-align:right;'>"
                "Datos: junio 2026 · Temporada Baja &nbsp;·&nbsp; "
                "8 fuentes: Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · Encuesta"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
    return filtro_destino, filtro_plataforma


def render_filtros_solo_destino():
    """Igual que render_filtros(), pero sin el selectbox de Plataforma."""
    with st.container(key="caja_filtros"):
        col_lbl, col_f1, col_info = st.columns([0.62, 1.05, 4.65])
        with col_lbl:
            st.markdown(
                "<div style='padding-top:6px; color:#BFDCF7; font-size:10.5px; "
                "font-weight:700; letter-spacing:0.8px;'>BUSCAR POR</div>",
                unsafe_allow_html=True,
            )
        with col_f1:
            filtro_destino = st.selectbox(
                "Destino", DESTINOS_DISPONIBLES, key="filtro_destino",
                label_visibility="collapsed",
            )
        with col_info:
            st.markdown(
                "<div style='padding-top:6px; color:#C9DEF5; font-size:11px; text-align:right;'>"
                "Datos: junio 2026 · Temporada Baja &nbsp;·&nbsp; "
                "8 fuentes: Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · Encuesta"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
    return filtro_destino


def render_encabezado_pagina(pagina_activa: str = ""):
    """Llamar al inicio de cada página de CONTENIDO (no Inicio): CSS +
    encabezado compacto + filtros. Devuelve (filtro_destino, filtro_plataforma)."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)
    return render_filtros()


def render_encabezado_sin_filtros(pagina_activa: str = ""):
    """Igual que render_encabezado_pagina, pero SIN la barra de filtros."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)


def render_encabezado_pagina_solo_destino(pagina_activa: str = ""):
    """Igual que render_encabezado_pagina, pero con SOLO el filtro de
    Destino. Devuelve filtro_destino."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)
    return render_filtros_solo_destino()