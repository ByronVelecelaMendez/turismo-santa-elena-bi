import glob
import json
import os
from datetime import datetime, date

from utils_staging import (
    homologar_destino,
    extraer_precio_usd,
    precio_total_a_por_noche,
    normalizar_rating,
    extraer_num_resenas,
)


def calcular_noches(checkin: str, checkout: str) -> int:
    try:
        d1 = date.fromisoformat(checkin)
        d2 = date.fromisoformat(checkout)
        return max((d2 - d1).days, 1)
    except (TypeError, ValueError):
        return 2


def procesar_booking(registro: dict) -> dict:
    noches = calcular_noches(registro.get("checkin"), registro.get("checkout"))
    precio_total = extraer_precio_usd(registro.get("precio_raw"))
    precio_noche = precio_total_a_por_noche(precio_total, noches)

    destino_info = homologar_destino(registro.get("destino"))

    return {
        "plataforma": "booking",
        "destino_slug": destino_info["destino_slug"],
        "dentro_alcance": destino_info["dentro_alcance"],
        "nombre_alojamiento": registro.get("nombre"),
        "precio_noche_usd": precio_noche,
        "rating_normalizado": normalizar_rating(registro.get("rating_raw"), "booking"),
        "num_resenas": extraer_num_resenas(registro.get("rating_raw")),
        "tipo_alojamiento": None,
        "categoria_estrellas": None,
        "fecha_extraccion": registro.get("fecha_extraccion"),
    }


def procesar_airbnb(registro: dict) -> dict:
    noches = calcular_noches(registro.get("checkin"), registro.get("checkout"))
    precio_total = extraer_precio_usd(registro.get("precio_raw"))
    precio_noche = precio_total_a_por_noche(precio_total, noches)

    destino_info = homologar_destino(registro.get("destino"))

    return {
        "plataforma": "airbnb",
        "destino_slug": destino_info["destino_slug"],
        "dentro_alcance": destino_info["dentro_alcance"],
        "nombre_alojamiento": registro.get("nombre"),
        "precio_noche_usd": precio_noche,
        "rating_normalizado": normalizar_rating(registro.get("rating_raw"), "airbnb"),
        "num_resenas": extraer_num_resenas(registro.get("rating_raw")),
        "tipo_alojamiento": None,
        "categoria_estrellas": None,
        "fecha_extraccion": registro.get("fecha_extraccion"),
    }


def procesar_kayak(registro: dict) -> dict:
    precio_noche = extraer_precio_usd(registro.get("precio_raw"))

    destino_info = homologar_destino(registro.get("destino"))

    return {
        "plataforma": "kayak",
        "destino_slug": destino_info["destino_slug"],
        "dentro_alcance": destino_info["dentro_alcance"],
        "nombre_alojamiento": registro.get("nombre"),
        "precio_noche_usd": precio_noche,
        "rating_normalizado": normalizar_rating(registro.get("rating_raw"), "kayak"),
        "num_resenas": int(registro["num_resenas"]) if registro.get("num_resenas") else None,
        "tipo_alojamiento": registro.get("tipo_alojamiento_raw"),
        "categoria_estrellas": None,
        "fecha_extraccion": registro.get("fecha_extraccion"),
    }


def procesar_hostelworld(registro: dict) -> dict:
    destino_info = homologar_destino(registro.get("destino"))

    precio_noche = registro.get("precio_min_usd_raw")
    try:
        precio_noche = float(precio_noche) if precio_noche is not None else None
    except (TypeError, ValueError):
        precio_noche = None

    return {
        "plataforma": "hostelworld",
        "destino_slug": destino_info["destino_slug"],
        "dentro_alcance": destino_info["dentro_alcance"],
        "nombre_alojamiento": registro.get("nombre_alojamiento") or registro.get("nombre"),
        "precio_noche_usd": precio_noche,
        "rating_normalizado": normalizar_rating(registro.get("rating_raw"), "hostelworld"),
        "num_resenas": int(registro["num_resenas"]) if registro.get("num_resenas") else None,
        "tipo_alojamiento": registro.get("tipo_alojamiento"),
        "categoria_estrellas": None,
        "fecha_extraccion": registro.get("fecha_extraccion"),
    }


PROCESADORES = {
    "booking": procesar_booking,
    "airbnb": procesar_airbnb,
    "kayak": procesar_kayak,
    "hostelworld": procesar_hostelworld,
}


def cargar_archivos_fuente(patron: str) -> list:
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
    patrones = {
        "booking": "data/raw/booking_*.json",
        "airbnb": "data/raw/airbnb_*.json",
        "kayak": "data/raw/kayak_*.json",
        "hostelworld": "data/raw/hostelworld_*.json",
    }

    staging_final = []
    resumen = {}
    sin_clasificar_total = 0

    for plataforma, patron in patrones.items():
        crudos = cargar_archivos_fuente(patron)

        print(f"{plataforma}: {len(crudos)} registros crudos encontrados")

        procesador = PROCESADORES[plataforma]
        procesados = [procesador(r) for r in crudos]

        # DEBUG
        for r, p in zip(crudos, procesados):
            if p["destino_slug"] == "sin_clasificar":
                print(
                    f"[SIN CLASIFICAR] "
                    f"plataforma={plataforma} | "
                    f"destino={r.get('destino')} | "
                    f"nombre={r.get('nombre')}"
                )

        sin_clasificar = [
            p for p in procesados
            if p["destino_slug"] == "sin_clasificar"
        ]

        sin_clasificar_total += len(sin_clasificar)

        staging_final.extend(procesados)
        resumen[plataforma] = len(procesados)

    os.makedirs("data/staging", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = f"data/staging/staging_hospedaje_{timestamp}.json"

    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(staging_final, f, ensure_ascii=False, indent=2)

    print("\n=== Resumen ===")

    for plataforma, total in resumen.items():
        print(f"  {plataforma}: {total} registros")

    print(f"Total unificado: {len(staging_final)}")
    print(f"Sin clasificar (destino no reconocido): {sin_clasificar_total}")
    print(f"\nGuardado: {archivo_salida}")


if __name__ == "__main__":
    main()