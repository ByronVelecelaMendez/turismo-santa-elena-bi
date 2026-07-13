import sys, os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

query = """
    SELECT
        a.nombre_alojamiento,
        COUNT(DISTINCT d.nombre_destino) AS num_destinos_distintos,
        STRING_AGG(DISTINCT d.nombre_destino, ', ') AS destinos,
        COUNT(*) AS num_filas
    FROM fact_hospedaje f
    JOIN dim_destino d ON f.id_destino = d.id_destino
    JOIN dim_alojamiento a ON f.id_alojamiento = a.id_alojamiento
    GROUP BY a.nombre_alojamiento
    HAVING COUNT(DISTINCT d.nombre_destino) > 1
    ORDER BY num_filas DESC
"""
df = pd.read_sql(query, engine)
print(f"Alojamientos duplicados en mas de un destino: {len(df)}")
print(df.to_string(index=False))
