import sys, os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

# 1. Cuantas filas de dim_destino existen realmente (deberian ser 6)
destinos = pd.read_sql("SELECT id_destino, nombre_destino FROM dim_destino ORDER BY nombre_destino", engine)
print("=== Registros en dim_destino (deberian ser 6) ===")
print(destinos.to_string(index=False))

print()
# 2. Cuantas filas de fact_hospedaje estan afectadas por el bug de duplicacion
bug_sql = """
    SELECT COUNT(*) AS filas_afectadas
    FROM fact_hospedaje f
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE a.nombre_alojamiento IN (
        SELECT a2.nombre_alojamiento
        FROM fact_hospedaje f2
        JOIN dim_destino d2 ON f2.id_destino = d2.id_destino
        JOIN dim_alojamiento a2 ON f2.id_alojamiento = a2.id_alojamiento
        GROUP BY a2.nombre_alojamiento
        HAVING COUNT(DISTINCT d2.nombre_destino) > 1
    )
"""
bug_df = pd.read_sql(bug_sql, engine)
print("=== Filas de fact_hospedaje afectadas por destino duplicado ===")
print(bug_df.to_string(index=False))

print()
# 3. Cuantas filas tienen nombres de alojamiento que claramente son texto de interfaz, no alojamientos reales
basura_sql = """
    SELECT a.nombre_alojamiento, COUNT(*) AS filas
    FROM fact_hospedaje f
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    WHERE a.nombre_alojamiento IN (
        'Datos del mapa ©2026', 'incluye impuestos', 'Cancelación gratis',
        'Desayuno gratis', '36% menos de lo habitual',
        'Descuento de última hora de $663', 'Menos de $134'
    )
    GROUP BY a.nombre_alojamiento
"""
basura_df = pd.read_sql(basura_sql, engine)
print("=== Filas con nombre de alojamiento invalido (texto de interfaz) ===")
print(basura_df.to_string(index=False))
