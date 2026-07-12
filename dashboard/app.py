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
