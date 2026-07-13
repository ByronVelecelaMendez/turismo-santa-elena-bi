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

st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

with st.container(border=True, key="caja_kpis"):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Publicaciones analizadas", f"{total_publicaciones:,}")
    col2.metric("Destinos cubiertos", "6")
    col3.metric("Fuentes de datos integradas", "8")
    col4.metric("Reseñas totales", f"{total_resenas:,}")

st.markdown(
    "<p style='text-align:center; color:#8697A8; font-size:12px; margin-top:12px;'>"
    "Datos consolidados en vivo desde el Data Warehouse (PostgreSQL) · "
    "Booking · Airbnb · KAYAK · Hostelworld · OpenWeather · MINTUR · "
    "Google Trends · Encuesta propia"
    "</p>",
    unsafe_allow_html=True,
)