import sys, os
import pandas as pd
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.conexion import get_engine

engine = get_engine()

sql = text("""
    SELECT p.nombre_plataforma, COUNT(f.id_hecho) AS num_registros
    FROM dim_plataforma p
    LEFT JOIN fact_hospedaje f ON f.id_plataforma = p.id_plataforma
    GROUP BY p.nombre_plataforma
    ORDER BY num_registros DESC
""")
with engine.connect() as conn:
    df = pd.read_sql(sql, conn)
print("=== Registros en fact_hospedaje por plataforma ===")
print(df.to_string(index=False))
