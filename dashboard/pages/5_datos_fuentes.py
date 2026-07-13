import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
import common

common.render_encabezado_sin_filtros("Datos y Fuentes")

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
    "probabilística).\n"
    "- Se detectó un bug de extracción de precio en el scraper de "
    "Hostelworld (agarraba un valor de texto plano repetido en la "
    "página, no el precio real). Se corrigió reescribiendo el scraper "
    "para leer el precio directamente del bloque HTML etiquetado "
    "'Dormitorios desde' / 'Privadas desde' de cada tarjeta, en vez de "
    "adivinar por posición en el texto. Los 14 registros de precio de "
    "Hostelworld actualmente en el DW ya reflejan esta corrección.\n"
    "- Se detectaron y eliminaron 40 registros con nombre de alojamiento "
    "inválido (texto de interfaz capturado por error, ej. 'incluye "
    "impuestos', 'Desayuno gratis').\n"
    "- Se identificaron 66 alojamientos que aparecen listados en más de "
    "un destino simultáneamente (mismo negocio indexado por búsquedas "
    "geográficas superpuestas en Airbnb/KAYAK). Pendiente de definir "
    "una regla de negocio para deduplicarlos sin generar falsos "
    "positivos en nombres genéricos (ej. 'Apartment in Salinas')."
)
common.cerrar_seccion()