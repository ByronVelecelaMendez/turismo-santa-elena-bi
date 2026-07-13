import sys, os
import pandas as pd
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

basura_sql = text("""
    SELECT a.nombre_alojamiento, COUNT(*) AS filas
    FROM fact_hospedaje f
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE a.nombre_alojamiento IN (
        'Datos del mapa (c)2026', 'incluye impuestos', 'Cancelacion gratis',
        'Desayuno gratis', '36% menos de lo habitual',
        'Descuento de ultima hora de $663', 'Menos de $134'
    )
    GROUP BY a.nombre_alojamiento
""")

with engine.connect() as conn:
    basura_df = pd.read_sql(basura_sql, conn)

print("=== Filas con nombre de alojamiento invalido (texto de interfaz) ===")
print(basura_df.to_string(index=False))

# Busqueda mas amplia: cualquier nombre que contenga palabras clave de interfaz
amplia_sql = text("""
    SELECT a.nombre_alojamiento, COUNT(*) AS filas
    FROM fact_hospedaje f
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE a.nombre_alojamiento ILIKE '%gratis%'
       OR a.nombre_alojamiento ILIKE '%impuesto%'
       OR a.nombre_alojamiento ILIKE '%descuento%'
       OR a.nombre_alojamiento ILIKE '%menos de%'
       OR a.nombre_alojamiento ILIKE '%mapa%'
    GROUP BY a.nombre_alojamiento
    ORDER BY filas DESC
""")
with engine.connect() as conn:
    amplia_df = pd.read_sql(amplia_sql, conn)

print()
print("=== Busqueda amplia de posible texto de interfaz (palabras clave) ===")
print(amplia_df.to_string(index=False))
