import json
import os
import pandas as pd
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ARCHIVOS = {
    "2023-10": "data/csv/1era-quincena-octubre-catastro-nacional-2023-banecuador-sri.xlsx",
    "2025-02": "data/csv/1era-quincena-febrero-catastro-nacional-2025-banecuador.xlsx",
}

# Solo tus 6 destinos oficiales del proyecto (DIM_DESTINO)
DESTINOS_PARROQUIA = {
    "SALINAS": "salinas",
    "GENERAL ALBERTO ENRÍQUEZ GALLO": "salinas",
    "JOSÉ LUIS TAMAYO": "salinas",
    "ANCONCITO": "salinas",
    "LA LIBERTAD": "la_libertad",
    "MANGLARALTO": "manglaralto",  # incluye Montañita y Ayangue, ver nota abajo
}


def limpiar(valor):
    """Convierte cualquier NaN/NaT de pandas a None real de Python."""
    if pd.isna(valor):
        return None
    return valor


def procesar_catastro(periodo, ruta):
    df = pd.read_excel(ruta)

    df["Provincia"] = df["Provincia"].astype(str).str.strip().str.upper()
    df["Cantón"] = df["Cantón"].astype(str).str.strip().str.upper()
    df["Parroquia"] = df["Parroquia"].astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True)

    santa_elena = df[df["Provincia"] == "SANTA ELENA"].copy()
    alojamiento = santa_elena[santa_elena["Actividad / Modalidad"] == "ALOJAMIENTO"].copy()

    # Filtrar solo parroquias que mapean a tus 6 destinos oficiales
    alojamiento = alojamiento[alojamiento["Parroquia"].isin(DESTINOS_PARROQUIA.keys())].copy()

    registros = []
    for _, fila in alojamiento.iterrows():
        parroquia = fila["Parroquia"]
        destino_aprox = DESTINOS_PARROQUIA.get(parroquia, "sin_mapear")

        registros.append({
            "fuente": "mintur_catastro",
            "periodo": periodo,
            "ruc": limpiar(fila["RUC"]),
            "nombre_establecimiento": limpiar(fila["Nombre Comercial"]),
            "fecha_registro": str(fila["Fecha de Registro"]) if pd.notna(fila["Fecha de Registro"]) else None,
            "clasificacion": limpiar(fila["Clasificación"]),
            "categoria": limpiar(fila["Categoría"]),
            "canton": limpiar(fila["Cantón"]),
            "parroquia": parroquia,
            "destino_aproximado": destino_aprox,
            "direccion": limpiar(fila["Dirección"]),
            "telefono": limpiar(fila["Teléfono Principal"]),
            "estado_registro": limpiar(fila["Estado Registro del Establecimiento"]),
            "fecha_extraccion": datetime.now().isoformat(),
        })

    return registros


def main():
    # Aseguramos que existan las carpetas de salida
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/staging", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resumen = {}
    todos_los_registros_staging = []  # Lista para unificar toda la data de MINTUR

    for periodo, ruta in ARCHIVOS.items():
        if not os.path.exists(ruta):
            logger.warning(f"No encontré el archivo: {ruta}")
            continue

        logger.info(f"Procesando catastro {periodo}...")
        registros = procesar_catastro(periodo, ruta)

        # Validar que haya registros después del filtrado
        if not registros:
            logger.warning(f"{periodo}: No hay registros después del filtrado")
            continue

        logger.info(f"  → {len(registros)} establecimientos en los 6 destinos oficiales")

        # Guardamos el respaldo individual en raw
        try:
            archivo_raw = f"data/raw/mintur_catastro_{periodo}_{timestamp}.json"
            with open(archivo_raw, "w", encoding="utf-8") as f:
                json.dump(registros, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"  → Respaldado en raw: {archivo_raw}")
        except IOError as e:
            logger.error(f"  → ERROR al guardar {archivo_raw}: {e}")
            continue

        # Acumulamos para la capa de Staging
        todos_los_registros_staging.extend(registros)
        resumen[periodo] = len(registros)

    # Validar que se procesó al menos un archivo
    if not todos_los_registros_staging:
        logger.error("No se procesó ningún archivo. Verifica las rutas en ARCHIVOS.")
        return

    # === GUARDAR EL ARCHIVO UNIFICADO EN STAGING ===
    try:
        archivo_staging = f"data/staging/staging_mintur_{timestamp}.json"
        with open(archivo_staging, "w", encoding="utf-8") as f:
            json.dump(todos_los_registros_staging, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"\n[✓] ÉXITO STAGING: Archivo unificado guardado en: {archivo_staging}")
        logger.info(f"[*] Total general de registros oficiales consolidados: {len(todos_los_registros_staging)}")
    except IOError as e:
        logger.error(f"Error al guardar archivo staging: {e}")
        return

    logger.info("\n=== Resumen comparativo ===")
    for periodo, total in resumen.items():
        logger.info(f"{periodo}: {total} alojamientos registrados")

    # Calcular crecimiento con protección contra división por cero
    if len(resumen) == 2:
        periodos = sorted(resumen.keys())
        primer_periodo_total = resumen[periodos[0]]
        
        if primer_periodo_total > 0:
            crecimiento = ((resumen[periodos[1]] - primer_periodo_total) / primer_periodo_total) * 100
            logger.info(f"\nCrecimiento {periodos[0]} → {periodos[1]}: {crecimiento:.1f}%")
        else:
            logger.warning(f"No se puede calcular crecimiento: {periodos[0]} tiene 0 registros")


if __name__ == "__main__":
    main()
