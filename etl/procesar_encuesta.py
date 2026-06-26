import os
import json
import logging
import pandas as pd
from datetime import datetime

# Configuración
RUTA_CSV = "data/csv/Experiencia_Turística_en_la_Provincia_de_Santa_Elena.csv"
RUTA_STAGING = "data/staging"
RUTA_LOGS = "logs"

os.makedirs(RUTA_STAGING, exist_ok=True)
os.makedirs(RUTA_LOGS, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(RUTA_LOGS, "pipeline.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Homologar los destinos
def homologar_destino(texto):
    if pd.isna(texto):
        return "sin_clasificar"

    t = str(texto).strip().lower()

    if "salinas" in t:
        return "salinas"

    if "montañita" in t or "montanita" in t or "monta" in t:
        return "montanita"

    if "ayangue" in t:
        return "ayangue"

    if "libertad" in t:
        return "la_libertad"

    if "manglar" in t:
        return "manglaralto"

    if "carnero" in t:
        return "punta_carnero"

    if "olón" in t or "olon" in t:
        return "olon"

    logging.warning(f"Destino no reconocido: {texto}")
    return "sin_clasificar"

# Obtener el número de la calificación
def extraer_calificacion(valor):
    if pd.isna(valor):
        return None

    try:
        return int(str(valor).split()[0])
    except:
        logging.warning(f"No se pudo convertir la calificación: {valor}")
        return None

def procesar_encuesta_staging():

    if not os.path.exists(RUTA_CSV):
        print(f"[-] No existe el archivo: {RUTA_CSV}")
        return

    print("[*] Leyendo encuesta...")

    df = pd.read_csv(RUTA_CSV, encoding="utf-8")

    registros_raw = len(df)

    # Eliminar registros duplicados
    df = df.drop_duplicates()

    duplicados = registros_raw - len(df)

    # Buscar la columna del destino
    columna_destino = [
        col for col in df.columns
        if "destino" in col.lower() or "lugar" in col.lower()
    ]

    if columna_destino:
        col_dest = columna_destino[0]
        df["destino_homologado"] = df[col_dest].apply(homologar_destino)
    else:
        df["destino_homologado"] = "sin_clasificar"
        logging.warning("No se encontró la columna del destino.")

    # Convertir la fecha
    df["Marca temporal"] = pd.to_datetime(
    df["Marca temporal"],
    errors="coerce",
    format="mixed"
)

    # Convertir las calificaciones
    columnas_calificacion = [
        col for col in df.columns
        if "1 al 5" in col.lower()
    ]

    for col in columnas_calificacion:
        df[col] = df[col].apply(extraer_calificacion)

    # Contar los valores nulos
    nulos = df.isnull().sum()

    logging.info("Valores nulos encontrados:")

    for columna, cantidad in nulos.items():
        logging.info(f"{columna}: {cantidad}")

    # Completar nulos en columnas de texto
    columnas_texto = df.select_dtypes(include=["object", "string"]).columns
    df[columnas_texto] = df[columnas_texto].fillna("Sin respuesta")

    # Guardar el JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    ruta_final = os.path.join(
        RUTA_STAGING,
        f"staging_encuesta_{timestamp}.json"
    )

    registros = df.to_dict(orient="records")

    with open(ruta_final, "w", encoding="utf-8") as f:
        json.dump(
            registros,
            f,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    # Mostrar un resumen
    completitud = (
        df.notnull().sum().sum()
        /
        (df.shape[0] * df.shape[1])
    ) * 100

    print("\n===== REPORTE =====")
    print(f"Registros Raw: {registros_raw}")
    print(f"Registros Staging: {len(df)}")
    print(f"Duplicados eliminados: {duplicados}")
    print(f"Nulos totales: {df.isnull().sum().sum()}")
    print(f"Completitud: {completitud:.2f}%")
    print(f"Archivo generado: {ruta_final}")

    logging.info("Encuesta procesada correctamente.")

if __name__ == "__main__":
    procesar_encuesta_staging()