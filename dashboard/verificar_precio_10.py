import sys, os
import pandas as pd
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

# 1. Todos los detalles del registro de $10 (Hostal Yaku Montañita)
sql1 = text("""
    SELECT
        f.id_hecho, d.nombre_destino, p.nombre_plataforma,
        a.nombre_alojamiento, a.tipo_alojamiento,
        f.precio_noche_usd, f.precio_min_usd, f.precio_max_usd,
        f.rating, f.num_resenas, f.ocupacion_estimada
    FROM fact_hospedaje f
    JOIN dim_destino d ON f.id_destino = d.id_destino
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE a.nombre_alojamiento = 'Hostal Yaku Montañita'
""")
with engine.connect() as conn:
    df1 = pd.read_sql(sql1, conn)
print("=== Detalle completo: Hostal Yaku Montañita ===")
print(df1.to_string(index=False))

print()
# 2. Existe algun registro cercano a $4.70 en toda la tabla?
sql2 = text("""
    SELECT
        d.nombre_destino, p.nombre_plataforma, a.nombre_alojamiento,
        f.precio_noche_usd, f.rating
    FROM fact_hospedaje f
    JOIN dim_destino d ON f.id_destino = d.id_destino
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE f.precio_noche_usd BETWEEN 4 AND 6
""")
with engine.connect() as conn:
    df2 = pd.read_sql(sql2, conn)
print("=== Registros con precio entre $4 y $6 ===")
print(df2.to_string(index=False) if not df2.empty else "(ninguno encontrado)")

print()
# 3. Distribucion de precios bajos por plataforma (para ver si $10 es normal o atipico)
sql3 = text("""
    SELECT p.nombre_plataforma,
        MIN(f.precio_noche_usd) AS min_precio,
        COUNT(*) FILTER (WHERE f.precio_noche_usd < 20) AS num_bajo_20
    FROM fact_hospedaje f
    JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
    WHERE f.precio_noche_usd IS NOT NULL
    GROUP BY p.nombre_plataforma
""")
with engine.connect() as conn:
    df3 = pd.read_sql(sql3, conn)
print("=== Precio minimo y cantidad de precios bajos (<$20) por plataforma ===")
print(df3.to_string(index=False))
