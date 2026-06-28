import glob
import json
import os
import logging
from datetime import datetime, date

from utils_staging import (
    homologar_destino,
    extraer_precio_usd,
    precio_total_a_por_noche,
    normalizar_rating,
    extraer_num_resenas,
    normalizar_texto,
    extraer_tipo_alojamiento,
    extraer_tipo_alojamiento_url,
)

# LOG
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)



def cargar_archivos_fuente(patron: str):
    registros = []

    for ruta in glob.glob(patron):
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                registros.extend(data)
            else:
                registros.append(data)

    return registros


def obtener_tipo_alojamiento(plataforma: str, r: dict):
    """
    Cada plataforma expone el tipo de alojamiento de forma distinta
    (o no lo expone). Se resuelve caso por caso:
      - kayak: viene embebido en el texto crudo completo ("raw")
      - hostelworld: se infiere de la categoria en la URL del listado
      - booking / airbnb: no exponen este dato en el scraper actual
    """
    if plataforma == "kayak":
        return extraer_tipo_alojamiento(r.get("raw"))
    if plataforma == "hostelworld":
        return extraer_tipo_alojamiento_url(r.get("url_detalle"))
    return None


def obtener_num_resenas(plataforma: str, r: dict):
    """
    Booking y Airbnb traen el numero de resenas embebido dentro del
    texto de rating_raw (ej. '1.170 comentarios', '5.0 (6)').
    KAYAK y Hostelworld ya lo exponen en un campo separado y limpio.
    """
    if plataforma in ("kayak",):
        valor = r.get("num_resenas")
    elif plataforma == "hostelworld":
        valor = r.get("numero_resenas")
    else:
        valor = None

    if valor is not None:
        try:
            return int(str(valor).replace(",", "").replace(".", ""))
        except (TypeError, ValueError):
            pass

    # Fallback: intentar extraerlo del texto de rating si el campo directo fallo
    return extraer_num_resenas(r.get("rating_raw"))


def main():

    patrones = {
        "booking": "data/raw/scraping/booking/booking_*.json",
        "airbnb": "data/raw/scraping/airbnb/airbnb_*.json",
        "kayak": "data/raw/scraping/kayak/kayak_*.json",
        "hostelworld": "data/raw/scraping/hostelworld/hostelworld_*.json",
    }

    staging = []
    resumen = {}

    for plataforma, patron in patrones.items():

        crudos = cargar_archivos_fuente(patron)

        print(f"{plataforma}: {len(crudos)}")

        procesados = []

        for r in crudos:

            destino_info = homologar_destino(
                normalizar_texto(r.get("destino"))
            )

            nombre = r.get("nombre") or "Sin nombre"

            procesados.append({
                "plataforma": plataforma,
                "destino_slug": destino_info["destino_slug"],
                "dentro_alcance": destino_info["dentro_alcance"],
                "nombre_alojamiento": nombre,
                "precio_noche_usd": extraer_precio_usd(r.get("precio_raw")),
                "rating_normalizado": normalizar_rating(r.get("rating_raw"), plataforma),
                "num_resenas": obtener_num_resenas(plataforma, r),
                "tipo_alojamiento": obtener_tipo_alojamiento(plataforma, r),
                "fecha_extraccion": r.get("fecha_extraccion"),
                "_precio_raw": r.get("precio_raw"),
                "_rating_raw": r.get("rating_raw"),
            })

        staging.extend(procesados)
        resumen[plataforma] = len(procesados)



    vistos = set()
    final = []

    for r in staging:

        clave = (
            r["plataforma"],
            r["destino_slug"],
            r["nombre_alojamiento"],
            r["_precio_raw"],
            r["_rating_raw"],
        )

        if clave not in vistos:
            vistos.add(clave)
            final.append(r)



    os.makedirs("data/staging", exist_ok=True)

    output = f"data/staging/staging_hospedaje_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print("\n===== REPORTE =====")
    print("Total staging:", len(final))
    print("Archivo:", output)

    print("\n===== POR PLATAFORMA (en archivo final) =====")
    from collections import Counter
    print(Counter(r["plataforma"] for r in final))

    con_tipo = sum(1 for r in final if r["tipo_alojamiento"] is not None)
    print(f"\nCon tipo_alojamiento detectado: {con_tipo}/{len(final)}")


if __name__ == "__main__":
    main()