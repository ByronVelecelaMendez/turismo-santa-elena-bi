import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import common

common.inject_base_css()
common.render_banner()

# ============================================================
# NAVEGACIÓN PRINCIPAL
# ============================================================
st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)

common.render_nav()

# ============================================================
# VITRINA DE KPIs GLOBALES
# Da contexto del alcance del proyecto antes de que el usuario navegue
# a una sección específica. Se calcula en vivo desde el Data Warehouse.
# ============================================================
df_precios = common.cargar_precios()
df_val = common.cargar_valoraciones()

total_publicaciones = int(df_precios["total_publicaciones"].sum())
total_resenas = int(df_val["total_resenas"].sum())

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

common.render_kpis([
    {"icono": "home_work", "etiqueta": "Publicaciones analizadas", "valor": f"{total_publicaciones:,}"},
    {"icono": "map", "etiqueta": "Destinos cubiertos", "valor": "6"},
    {"icono": "database", "etiqueta": "Fuentes de datos integradas", "valor": "8"},
    {"icono": "reviews", "etiqueta": "Reseñas totales", "valor": f"{total_resenas:,}"},
])

# ============================================================
# PIE: FUENTES DE DATOS (chips) + CRÉDITOS
# ============================================================
st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

_FUENTES = ["Booking", "Airbnb", "KAYAK", "Hostelworld",
            "OpenWeather", "MINTUR", "Google Trends", "Encuesta propia"]
_chips = "".join(
    f"<span style='display:inline-block; background:#FFFFFF; color:#3A4D63; "
    f"border:1px solid #D8E2EF; border-radius:999px; padding:5px 14px; "
    f"margin:3px 4px; font-size:11.5px; font-weight:600;'>{f}</span>"
    for f in _FUENTES
)

st.markdown(
    "<div style='text-align:center; padding:6px 0 4px 0;'>"
    "<div style='color:#7A8CA0; font-size:11px; font-weight:700; "
    "text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>"
    "Fuentes de datos integradas</div>"
    f"<div>{_chips}</div>"
    "<div style='color:#98A4B3; font-size:11px; margin-top:12px;'>"
    "Datos consolidados en vivo desde el Data Warehouse (PostgreSQL) · "
    "Proyecto Integrador · Facultad de Sistemas y Telecomunicaciones · UPSE 2026-1"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)