import json
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.conexion import get_engine

RUTA_JSON = "temp_staging/staging/staging_encuesta_20260628_222616.json"

if not os.path.exists(RUTA_JSON):
    print("No se encontro el archivo:", RUTA_JSON)
    print("Verifica la ruta correcta con: dir temp_staging\staging")
else:
    with open(RUTA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print("Leidos", len(df), "registros del JSON de staging.")
    print("Columnas:", list(df.columns))

    engine = get_engine()
    df.to_sql("fact_encuesta", engine, if_exists="replace", index=False)
    print("Tabla fact_encuesta creada en el Data Warehouse con", len(df), "registros.")
