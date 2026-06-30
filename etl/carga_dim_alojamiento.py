"""
Carga DIM_ALOJAMIENTO a partir de staging_hospedaje (454 registros).
Cada alojamiento unico (por nombre + plataforma) se inserta una sola vez.
tipo_alojamiento se mapea desde los valores libres del staging hacia las
4 categorias controladas del esquema (hotel/hostal/cabana/apartamento).
categoria_estrellas queda NULL: ninguna de las 4 plataformas de scraping
expone esa informacion de forma confiable en el staging actual.
"""

import sys
import os
import glob
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.conexion import get_engine


# Mapeo de tipo_alojamiento libre -> 4 categorias controladas del esquema
MAPA_TIPO_ALOJAMIENTO = {
    "Hotel": "hotel",
    "Hotel boutique": "hotel",
    "Resort": "hotel",
    "Hostal": "hostal",
    "Hostel": "hostal",
    "Bed and breakfast": "hostal",
    "Cabaña": "cabana",
    "Lodge": "cabana",
    "Eco-lodge": "cabana",
    "Glamping": "cabana",
    "Hacienda": "cabana",
    "Casa": "apartamento",
    "Apartamento": "apartamento",
    "Departamento": "apartamento",
    "Villa": "apartamento",
    "Casa de huéspedes": "apartamento",
}


def mapear_tipo(tipo_raw):
    if not tipo_raw:
        return "apartamento"  # categoria por defecto, documentado en E3 (control de nulos)
    return MAPA_TIPO_ALOJAMIENTO.get(tipo_raw, "apartamento")


def ultimo_archivo(patron):
    archivos = sorted(glob.glob(patron))
    return archivos[-1] if archivos else None


def main():
    archivo = ultimo_archivo("data/staging/staging_hospedaje_*.json")
    if not archivo:
        print("[ERROR] No se encontro staging_hospedaje. Corre primero etl/staging_hospedaje.py")
        return

    print(f"Leyendo: {archivo}")
    with open(archivo, "r", encoding="utf-8") as f:
        registros = json.load(f)

    # Deduplicar alojamientos unicos: misma combinacion plataforma+nombre
    # debe insertarse una sola vez en DIM_ALOJAMIENTO
    vistos = set()
    alojamientos_unicos = []

    for r in registros:
        clave = (r["plataforma"], r["nombre_alojamiento"])
        if clave in vistos:
            continue
        vistos.add(clave)
        alojamientos_unicos.append(r)

    print(f"Alojamientos unicos a insertar: {len(alojamientos_unicos)} (de {len(registros)} registros totales)")

    engine = get_engine()
    insertados = 0
    omitidos = 0

    with engine.begin() as conn:
        for r in alojamientos_unicos:
            nombre = r["nombre_alojamiento"]
            tipo = mapear_tipo(r.get("tipo_alojamiento"))

            existe = conn.execute(
                text("SELECT 1 FROM dim_alojamiento WHERE nombre_alojamiento = :nombre"),
                {"nombre": nombre}
            ).fetchone()

            if existe:
                omitidos += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO dim_alojamiento (nombre_alojamiento, tipo_alojamiento, categoria_estrellas, capacidad)
                    VALUES (:nombre_alojamiento, :tipo_alojamiento, NULL, NULL)
                """),
                {"nombre_alojamiento": nombre, "tipo_alojamiento": tipo}
            )
            insertados += 1

    print(f"\nInsertados: {insertados}")
    print(f"Omitidos (ya existian): {omitidos}")
    print("Listo.")


if __name__ == "__main__":
    main()