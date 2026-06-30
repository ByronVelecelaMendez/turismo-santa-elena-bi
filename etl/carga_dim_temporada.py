"""
Carga DIM_TEMPORADA con las 3 temporadas oficiales del proyecto.
La temperatura de 'baja' usa el dato REAL medido por OpenWeather
(staging_openweather). 'alta' y 'media' se documentan como estimacion,
ya que solo se realizo extraccion en un dia (22 de junio, temporada baja).
"""

import sys
import os
import glob
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.conexion import get_engine


def obtener_temperatura_baja_real():
    """Lee el ultimo staging de OpenWeather y devuelve el promedio real
    medido para la temporada baja."""
    archivos = sorted(glob.glob("data/staging/staging_openweather_*.json"))
    if not archivos:
        return None
    with open(archivos[-1], "r", encoding="utf-8") as f:
        data = json.load(f)
    for resumen in data.get("resumen_por_temporada", []):
        if resumen["temporada"] == "baja":
            return resumen["temperatura_promedio"], resumen["condicion_climatica"]
    return None, None


def main():
    temp_baja, condicion_baja = obtener_temperatura_baja_real()

    TEMPORADAS = [
        {
            "nombre_temporada": "alta",
            "meses": "Diciembre, Enero, Febrero, Julio",
            "condicion_climatica": "Estimacion sin medicion real (pendiente extraccion en estos meses)",
            "temperatura_promedio": 28.5,  # estimacion documentada, no medida
        },
        {
            "nombre_temporada": "media",
            "meses": "Marzo, Agosto",
            "condicion_climatica": "Estimacion sin medicion real (pendiente extraccion en estos meses)",
            "temperatura_promedio": 26.0,  # estimacion documentada, no medida
        },
        {
            "nombre_temporada": "baja",
            "meses": "Abril, Mayo, Junio, Septiembre, Octubre, Noviembre",
            "condicion_climatica": condicion_baja or "algo de nubes",
            "temperatura_promedio": temp_baja or 24.51,
        },
    ]

    engine = get_engine()

    with engine.begin() as conn:
        for t in TEMPORADAS:
            existe = conn.execute(
                text("SELECT 1 FROM dim_temporada WHERE nombre_temporada = :nombre"),
                {"nombre": t["nombre_temporada"]}
            ).fetchone()

            if existe:
                print(f"  [SKIP] Ya existe: {t['nombre_temporada']}")
                continue

            conn.execute(
                text("""
                    INSERT INTO dim_temporada (nombre_temporada, meses, condicion_climatica, temperatura_promedio)
                    VALUES (:nombre_temporada, :meses, :condicion_climatica, :temperatura_promedio)
                """),
                t
            )
            print(f"  [OK] Insertado: {t['nombre_temporada']} ({t['temperatura_promedio']}°C)")

    print("\nListo.")


if __name__ == "__main__":
    main()