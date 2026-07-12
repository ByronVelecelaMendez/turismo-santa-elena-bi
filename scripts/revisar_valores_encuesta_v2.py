import sys, os
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.conexion import get_engine

engine = get_engine()
df = pd.read_sql("SELECT * FROM fact_encuesta", engine)

def buscar(cols, palabra):
    for c in cols:
        if palabra.lower() in c.lower():
            return c
    return None

col_precio = buscar(df.columns, "paga")
col_calidad = buscar(df.columns, "calidad")
col_recomienda = buscar(df.columns, "recomend")

print("Columna precio encontrada:", col_precio)
print("Columna calidad encontrada:", col_calidad)
print("Columna recomienda encontrada:", col_recomienda)
print()

if col_precio:
    print("Valores unicos de precio:")
    print(df[col_precio].value_counts())
    print()

if col_calidad:
    print("Valores unicos de calidad:")
    print(df[col_calidad].value_counts())
    print()

if col_recomienda:
    print("Valores unicos de recomendacion:")
    print(df[col_recomienda].value_counts())
