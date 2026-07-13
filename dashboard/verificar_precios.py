import sys, os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

query = """
    SELECT
        d.nombre_destino, p.nombre_plataforma, a.nombre_alojamiento,
        f.precio_noche_usd, f.rating
    FROM fact_hospedaje f
    JOIN dim_destino d ON f.id_destino = d.id_destino
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE f.precio_noche_usd IS NOT NULL
    ORDER BY f.precio_noche_usd ASC
    LIMIT 10
"""
df = pd.read_sql(query, engine)
print("=== 10 precios MAS BAJOS en fact_hospedaje (sin filtros) ===")
print(df.to_string(index=False))

print()
resumen_sql = """
    SELECT
        COUNT(*) AS total_filas,
        MIN(precio_noche_usd) AS precio_minimo,
        ROUND(AVG(precio_noche_usd)::numeric, 2) AS precio_promedio,
        MAX(precio_noche_usd) AS precio_maximo
    FROM fact_hospedaje
    WHERE precio_noche_usd IS NOT NULL
"""
resumen = pd.read_sql(resumen_sql, engine)
print("=== Resumen general (todo fact_hospedaje, sin filtros) ===")
print(resumen.to_string(index=False))
