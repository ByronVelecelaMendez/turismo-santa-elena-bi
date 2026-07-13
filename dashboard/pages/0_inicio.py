import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import common

common.inject_base_css()
common.render_banner()
common.render_nav()

# ============================================================
# VITRINA DE KPIs GLOBALES
# Da contexto del alcance del proyecto antes de que el usuario navegue
# a una sección específica, y aprovecha el espacio vacío bajo las
# tarjetas. Se calcula en vivo desde el Data Warehouse.
# ============================================================
df_precios = common.cargar_precios()
df_val = common.cargar_valoraciones()

total_publicaciones = int(df_precios["total_publicaciones"].sum())
total_resenas = int(df_val["total_resenas"].sum())

st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

common.render_kpis([
    {"icono": "home_work", "etiqueta": "Publicaciones analizadas", "valor": f"{total_publicaciones:,}"},
    {"icono": "map", "etiqueta": "Destinos cubiertos", "valor": "6"},
    {"icono": "database", "etiqueta": "Fuentes de datos integradas", "valor": "8"},
    {"icono": "reviews", "etiqueta": "Reseñas totales", "valor": f"{total_resenas:,}"},
])

st.markdown(
    "<p style='text-align:center; color:#8697A8; font-size:12px; margin-top:12px;'>"
    "Datos consolidados en vivo desde el Data Warehouse (PostgreSQL) · "
    "Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · "
    "Google Trends · Encuesta propia"
    "</p>",
    unsafe_allow_html=True,
)