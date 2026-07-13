"""
Version optimizada de carga_fact_hospedaje.py: precarga las dimensiones
UNA sola vez en memoria en vez de consultar la base por cada registro.
Reduce ~2700 consultas de red a solo 4, mucho mas rapido en una base
remota (Render).
"""

import sys
import os
import glob
import json
from datetime import datetime

sys.path.append(os.path.abspath("."))
from sqlalchemy import text
from database.conexion import get_engine

MAPA_DESTINO_NOMBRE = {
    "salinas": "Salinas",
    "montanita": "Montañita",
    "ayangue": "Ayangue",
    "punta_carnero": "Punta Carnero",
    "manglaralto": "Manglaralto",
    "la_libertad": "La Libertad",
}
MAPA_PLATAFORMA_NOMBRE = {
    "booking": "Booking",
    "airbnb": "Airbnb",
    "kayak": "KAYAK",
    "hostelworld": "Hostelworld",
}
TEMPORADA_POR_MES = {
    12: "alta", 1: "alta", 2: "alta", 7: "alta",
    3: "media", 8: "media",
    4: "baja", 5: "baja", 6: "baja", 9: "baja", 10: "baja", 11: "baja",
}

def ultimo_archivo(patron):
    archivos = sorted(glob.glob(patron))
    return archivos[-1] if archivos else None

def main():
    archivo = ultimo_archivo("data/staging/staging_hospedaje_*.json")
    if not archivo:
        print("[ERROR] No se encontro staging_hospedaje.")
        return

    print(f"Leyendo: {archivo}")
    with open(archivo, "r", encoding="utf-8") as f:
        registros = json.load(f)
    print(f"Total registros a procesar: {len(registros)}")

    engine = get_engine()

    print("Precargando dimensiones en memoria (4 consultas, no 2700)...")
    with engine.connect() as conn:
        mapa_destino_id = {n: i for i, n in conn.execute(
            text("SELECT id_destino, nombre_destino FROM dim_destino")).fetchall()}
        mapa_plataforma_id = {n: i for i, n in conn.execute(
            text("SELECT id_plataforma, nombre_plataforma FROM dim_plataforma")).fetchall()}
        mapa_alojamiento_id = {n: i for i, n in conn.execute(
            text("SELECT id_alojamiento, nombre_alojamiento FROM dim_alojamiento")).fetchall()}
        mapa_fecha_id = {f: i for i, f in conn.execute(
            text("SELECT id_fecha, fecha_completa FROM dim_fecha")).fetchall()}
        mapa_temporada_id = {n: i for i, n in conn.execute(
            text("SELECT id_temporada, nombre_temporada FROM dim_temporada")).fetchall()}

    print("Dimensiones precargadas. Ya existen en fact_hospedaje:")
    with engine.connect() as conn:
        existentes = conn.execute(text("""
            SELECT id_destino, id_alojamiento, id_plataforma, precio_noche_usd
            FROM fact_hospedaje
        """)).fetchall()
    set_existentes = set(existentes)
    print(f"  {len(set_existentes)} combinaciones ya cargadas (para no duplicar)")

    insertados = 0
    omitidos_sin_match = 0
    omitidos_duplicado = 0
    detalle_omitidos = []

    with engine.begin() as conn:
        for r in registros:
            nombre_destino = MAPA_DESTINO_NOMBRE.get(r["destino_slug"])
            nombre_plataforma = MAPA_PLATAFORMA_NOMBRE.get(r["plataforma"])
            nombre_alojamiento = r["nombre_alojamiento"]

            id_destino = mapa_destino_id.get(nombre_destino)
            id_plataforma = mapa_plataforma_id.get(nombre_plataforma)
            id_alojamiento = mapa_alojamiento_id.get(nombre_alojamiento)

            try:
                fecha = datetime.fromisoformat(r.get("fecha_extraccion")).date()
            except (ValueError, TypeError):
                fecha = None
            id_fecha = mapa_fecha_id.get(fecha) if fecha else None
            temporada_nombre = TEMPORADA_POR_MES.get(fecha.month) if fecha else None
            id_temporada = mapa_temporada_id.get(temporada_nombre)

            faltantes = []
            if id_destino is None: faltantes.append("destino")
            if id_plataforma is None: faltantes.append("plataforma")
            if id_alojamiento is None: faltantes.append("alojamiento")
            if id_fecha is None: faltantes.append("fecha")
            if id_temporada is None: faltantes.append("temporada")
            if r.get("precio_noche_usd") is None: faltantes.append("precio")

            if faltantes:
                omitidos_sin_match += 1
                detalle_omitidos.append({"nombre_alojamiento": nombre_alojamiento, "faltantes": faltantes})
                continue

            # Evitar duplicar registros que ya existan (mismo destino+alojamiento+plataforma+precio)
            clave = (id_destino, id_alojamiento, id_plataforma, r.get("precio_noche_usd"))
            if clave in set_existentes:
                omitidos_duplicado += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO fact_hospedaje
                        (id_fecha, id_destino, id_alojamiento, id_plataforma, id_temporada,
                         precio_noche_usd, rating, ocupacion_estimada, num_resenas,
                         fuente_extraccion)
                    VALUES
                        (:id_fecha, :id_destino, :id_alojamiento, :id_plataforma, :id_temporada,
                         :precio, :rating, NULL, :num_resenas, :fuente)
                """),
                {
                    "id_fecha": id_fecha, "id_destino": id_destino,
                    "id_alojamiento": id_alojamiento, "id_plataforma": id_plataforma,
                    "id_temporada": id_temporada,
                    "precio": r.get("precio_noche_usd"),
                    "rating": r.get("rating_normalizado"),
                    "num_resenas": r.get("num_resenas") or 0,
                    "fuente": r["plataforma"],
                }
            )
            insertados += 1
            set_existentes.add(clave)

    print(f"\nInsertados en fact_hospedaje: {insertados}")
    print(f"Omitidos por FK faltante: {omitidos_sin_match}")
    print(f"Omitidos por ya existir (duplicado evitado): {omitidos_duplicado}")
    if detalle_omitidos:
        print("\nPrimeros 10 omitidos por FK faltante:")
        for d in detalle_omitidos[:10]:
            print(f"  {d['nombre_alojamiento']} -> faltan: {d['faltantes']}")
    print("\nListo.")

if __name__ == "__main__":
    main()
