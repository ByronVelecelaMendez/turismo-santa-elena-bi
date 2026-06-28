import glob
import json
import os
from collections import Counter
from datetime import datetime

# IMPORTANTE: tras la reorganizacion de la Zona Raw en subcarpetas por tipo
# de fuente (ver README), OpenWeather se guarda en data/raw/api/openweather/,
# no directo en data/raw/.
ARCHIVOS_OPENWEATHER = "data/raw/api/openweather/openweather_*.json"

# Clasificacion de temporada por mes, segun la regla de negocio definida en E2:
# alta (Dic-Ene-Feb-Jul), media (Mar-Ago), baja (Abr-May-Jun-Sep-Oct-Nov).
# Esta misma regla es la que documenta la matriz de trazabilidad del E2
# para DIM_TEMPORADA.nombre_temporada.
TEMPORADA_POR_MES = {
    12: "alta", 1: "alta", 2: "alta", 7: "alta",
    3: "media", 8: "media",
    4: "baja", 5: "baja", 6: "baja", 9: "baja", 10: "baja", 11: "baja",
}


def clasificar_temporada(fecha_extraccion: str) -> str:
    """Convierte la fecha de extraccion del registro en su temporada
    correspondiente, segun el mes. Se usa la fecha de extraccion (no una
    fecha de viaje) porque OpenWeather solo expone clima actual, no
    pronostico ni historico; el dato representa el clima del momento en
    que se corrio el scraper."""
    try:
        fecha = datetime.fromisoformat(fecha_extraccion)
        return TEMPORADA_POR_MES.get(fecha.month, "sin_clasificar")
    except (ValueError, TypeError):
        return "sin_clasificar"


def cargar_archivos(patron: str) -> list:
    registros = []
    for ruta in glob.glob(patron):
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if isinstance(datos, list):
                registros.extend(datos)
            else:
                registros.append(datos)
    return registros


def main():
    crudos = cargar_archivos(ARCHIVOS_OPENWEATHER)
    print(f"Registros crudos de OpenWeather encontrados: {len(crudos)}")

    if not crudos:
        print("[ERROR] No se encontraron archivos de OpenWeather en data/raw/api/openweather/. "
              "Corre primero scraping/openweather_api.py")
        return

    registros_staging = []
    for r in crudos:
        temporada = clasificar_temporada(r.get("fecha_extraccion"))
        registros_staging.append({
            "destino": r.get("destino"),
            "temporada_clasificada": temporada,
            "temperatura_c": r.get("temperatura_c"),
            "condicion_clima": r.get("condicion_clima"),
            "humedad_pct": r.get("humedad_pct"),
            "fecha_extraccion": r.get("fecha_extraccion"),
        })

    # Agregado por temporada: promedio de temperatura y condicion mas
    # frecuente (moda). NOTA DE CALIDAD: la extraccion actual solo se hizo
    # en una fecha (22 de junio de 2026), por lo que solo existen
    # observaciones para la temporada "baja"; "alta" y "media" quedaran
    # vacias hasta que se programen extracciones recurrentes en otros
    # meses del año. Esto se documenta como limitacion conocida, no se
    # rellena con datos ficticios.
    resumen_temporada = {}
    for temporada in set(r["temporada_clasificada"] for r in registros_staging):
        filas = [r for r in registros_staging if r["temporada_clasificada"] == temporada]
        temperaturas = [r["temperatura_c"] for r in filas if r["temperatura_c"] is not None]
        condiciones = [r["condicion_clima"] for r in filas if r["condicion_clima"]]

        temperatura_promedio = round(sum(temperaturas) / len(temperaturas), 2) if temperaturas else None
        condicion_mas_comun = Counter(condiciones).most_common(1)[0][0] if condiciones else None

        resumen_temporada[temporada] = {
            "temporada": temporada,
            "temperatura_promedio": temperatura_promedio,
            "condicion_climatica": condicion_mas_comun,
            "num_observaciones": len(filas),
        }

    os.makedirs("data/staging", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = f"data/staging/staging_openweather_{timestamp}.json"

    salida = {
        "detalle_por_destino": registros_staging,
        "resumen_por_temporada": list(resumen_temporada.values()),
    }

    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print("\n=== Resumen por temporada ===")
    for temporada, datos in resumen_temporada.items():
        print(f"  {temporada}: {datos['temperatura_promedio']}°C, "
              f"'{datos['condicion_climatica']}' "
              f"({datos['num_observaciones']} observaciones)")

    print(f"\nGuardado: {archivo_salida}")


if __name__ == "__main__":
    main()