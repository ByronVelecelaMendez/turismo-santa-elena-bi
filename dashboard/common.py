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
    }
    div[data-testid="stMainBlockContainer"] {
        padding-top: 0.5rem !important;
    }
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 0.5rem !important;
    }
    iframe {
        display: block;
    }
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

    /* ============================================================
       TARJETAS GRANDES DE NAVEGACIÓN (solo página de Inicio)
       Degradado azul a juego con el banner institucional.
       ============================================================ */
    .st-key-nav_cards div[data-testid="stPageLink"] {
        width: 100%;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a {
        width: 100%;
        min-height: 130px;
        border-radius: 16px;
        border: none !important;
        background: linear-gradient(180deg, #EAF3FF 0%, #D3E6FB 100%);
        color: #0B3B70 !important;
        text-decoration: none !important;
        box-shadow: 0 2px 10px rgba(11, 59, 112, 0.10);
        transition: all 0.2s ease-in-out;
        padding: 18px 12px;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 10px;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a:hover {
        background: linear-gradient(180deg, #DCEBFC 0%, #BFDCF7 100%);
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(11, 59, 112, 0.20);
        border: none !important;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a [data-testid="stIconMaterial"] {
        font-size: 30px !important;
        color: #0B3B70 !important;
        line-height: 1;
    }
    .st-key-nav_cards div[data-testid="stPageLink"] a p {
        margin: 0 !important;
        color: #0B3B70 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        line-height: 1.25;
        white-space: normal;
    }

    /* Tarjetas de navegación reales (st.page_link), estilo profesional
       — se usa en páginas internas que NO son la de Inicio */
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
        border-radius: 12px;
        padding: 6px 18px 2px 18px;
        border: 1px solid #DCE4EE;
    }
    .st-key-caja_filtros div[data-testid="stSelectbox"] {
        margin-bottom: -6px;
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
        font-size: 12.5px !important;
        white-space: normal;
        line-height: 1.15;
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

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ============================================================
# NAVEGACIÓN CON TARJETAS = PÁGINAS REALES (st.page_link)
# ============================================================

ICONOS_NAV = {
    "Resumen General": "bar_chart",
    "Análisis de Precios": "payments",
    "Valoraciones por Plataforma": "star",
    "Encuesta Propia": "assignment",
    "Datos y Fuentes": "database",
}


def render_nav():
    """Fila de tarjetas de navegación GRANDES (solo para la página de
    Inicio, replica la Imagen 1). Cada una es un st.page_link real:
    al hacer clic, Streamlit navega a una URL propia (p. ej.
    /Resumen_General), no solo cambia contenido en la misma página."""
    with st.container(key="nav_cards"):
        cols_nav = st.columns(len(PAGINAS) - 1)  # todas menos "Inicio"
        for col, (titulo, ruta) in zip(cols_nav, PAGINAS[1:]):
            with col:
                icono = ICONOS_NAV.get(titulo, "circle")
                st.page_link(
                    ruta,
                    label=titulo,
                    icon=f":material/{icono}:",
                    use_container_width=True,
                )

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# ============================================================
# ENCABEZADO COMPACTO (páginas de contenido, no la de Inicio)
# ============================================================

# Etiquetas cortas SOLO para el menú superior compacto (nav_slim);
# el título completo de la página y las tarjetas de Inicio no cambian.
NAV_LABELS_CORTOS = {
    "Resumen General": "Resumen General",
    "Análisis de Precios": "Análisis de Precios",
    "Valoraciones por Plataforma": "Valoraciones",
    "Encuesta Propia": "Encuesta Propia",
    "Datos y Fuentes": "Datos y Fuentes",
    "Inicio": "Inicio",
}


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
                            etiqueta = NAV_LABELS_CORTOS.get(titulo, titulo)
                            st.page_link(ruta, label=etiqueta, use_container_width=True)
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
            "<p style='font-size:11px; font-weight:700; color:#5A7089; "
            "letter-spacing:1px; margin-bottom:2px;'>BUSCAR POR</p>",
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
                "<div style='padding-top:22px; color:#5A7089; font-size:12px;'>"
                "Datos extraídos: junio 2026 · Temporada: Baja<br>"
                "Fuentes: Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · Encuesta"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    return filtro_destino, filtro_plataforma


def render_filtros_solo_destino():
    """Igual que render_filtros(), pero sin el selectbox de Plataforma.
    Usar en páginas cuyos datos vienen de vistas ya agregadas por
    destino (combinando las 4 plataformas), donde filtrar por
    plataforma no tendría ningún efecto (p. ej. Resumen General)."""
    with st.container(border=True, key="caja_filtros"):
        st.markdown(
            "<p style='font-size:11px; font-weight:700; color:#5A7089; "
            "letter-spacing:1px; margin-bottom:2px;'>BUSCAR POR</p>",
            unsafe_allow_html=True,
        )
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            filtro_destino = st.selectbox(
                "Destino", DESTINOS_DISPONIBLES, key="filtro_destino"
            )
        with col_f2:
            st.markdown(
                "<div style='padding-top:22px; color:#5A7089; font-size:12px;'>"
                "Datos extraídos: junio 2026 · Temporada: Baja<br>"
                "Fuentes: Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · Encuesta"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    return filtro_destino


def render_encabezado_pagina(pagina_activa: str = ""):
    """Llamar al inicio de cada página de CONTENIDO (no Inicio): CSS +
    encabezado compacto (con la pestaña 'pagina_activa' resaltada) +
    filtros. Devuelve (filtro_destino, filtro_plataforma)."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)
    return render_filtros()


def render_encabezado_sin_filtros(pagina_activa: str = ""):
    """Igual que render_encabezado_pagina, pero SIN la barra de filtros.
    Usar en páginas donde no aplica filtrar por destino/plataforma
    (p. ej. Datos y Fuentes, que muestra un catálogo estático)."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)


def render_encabezado_pagina_solo_destino(pagina_activa: str = ""):
    """Igual que render_encabezado_pagina, pero con SOLO el filtro de
    Destino (sin Plataforma). Usar en páginas cuyos datos vienen de
    vistas ya agregadas por destino, donde el filtro de Plataforma no
    tendría efecto (p. ej. Resumen General). Devuelve filtro_destino."""
    inject_base_css()
    render_encabezado_compacto(pagina_activa)
    return render_filtros_solo_destino()