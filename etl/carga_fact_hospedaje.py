"""
Carga FACT_HOSPEDAJE desde staging_hospedaje (454 registros).

Por cada registro de staging, resuelve las 5 llaves foraneas hacia las
dimensiones ya pobladas (DIM_DESTINO, DIM_ALOJAMIENTO, DIM_PLATAFORMA,
DIM_TEMPORADA, DIM_FECHA) y construye la fila de hechos.

LIMITACION DOCUMENTADA: la extraccion de las 4 fuentes de scraping se
realizo durante junio 2026 (temporada baja segun la regla de negocio del
E2), por lo que el 100% de los registros de fact_hospedaje quedaran
asociados a id_temporada = 'baja'. No existe visibilidad de temporada
alta/media en los datos reales cargados.
"""

import sys
import os
import glob
import json
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.conexion import get_engine


# Mismo mapeo usado en dim_alojamiento, para resolver tipo_alojamiento
# de forma consistente al momento de buscar el id_alojamiento.
MAPA_TIPO_ALOJAMIENTO = {
    "Hotel": "hotel", "Hotel boutique": "hotel", "Resort": "hotel",
    "Hostal": "hostal", "Hostel": "hostal", "Bed and breakfast": "hostal",
    "Cabaña": "cabana", "Lodge": "cabana", "Eco-lodge": "cabana",
    "Glamping": "cabana", "Hacienda": "cabana",
    "Casa": "apartamento", "Apartamento": "apartamento",
    "Departamento": "apartamento", "Villa": "apartamento",
    "Casa de huéspedes": "apartamento",
}

# Mapeo destino_slug (staging) -> nombre_destino (DIM_DESTINO)
MAPA_DESTINO_NOMBRE = {
    "salinas": "Salinas",
    "montanita": "Montañita",
    "ayangue": "Ayangue",
    "punta_carnero": "Punta Carnero",
    "manglaralto": "Manglaralto",
    "la_libertad": "La Libertad",
}

# Mapeo plataforma (staging) -> nombre_plataforma (DIM_PLATAFORMA)
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


def resolver_id_fecha(conn, fecha_extraccion_str):
    """Convierte fecha_extraccion (ISO datetime) a su id_fecha en DIM_FECHA."""
    try:
        fecha = datetime.fromisoformat(fecha_extraccion_str).date()
    except (ValueError, TypeError):
        return None, None

    fila = conn.execute(
        text("SELECT id_fecha FROM dim_fecha WHERE fecha_completa = :fecha"),
        {"fecha": fecha}
    ).fetchone()

    temporada_nombre = TEMPORADA_POR_MES.get(fecha.month)
    return (fila[0] if fila else None), temporada_nombre


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

    insertados = 0
    omitidos_sin_match = 0
    detalle_omitidos = []

    with engine.begin() as conn:
        # Pre-cargar IDs de temporada (solo 3 filas, se cachean en memoria)
        temporadas = conn.execute(text("SELECT id_temporada, nombre_temporada FROM dim_temporada")).fetchall()
        mapa_temporada_id = {nombre: id_ for id_, nombre in temporadas}

        for r in registros:
            nombre_destino = MAPA_DESTINO_NOMBRE.get(r["destino_slug"])
            nombre_plataforma = MAPA_PLATAFORMA_NOMBRE.get(r["plataforma"])
            nombre_alojamiento = r["nombre_alojamiento"]

            id_destino = None
            if nombre_destino:
                fila = conn.execute(
                    text("SELECT id_destino FROM dim_destino WHERE nombre_destino = :nombre"),
                    {"nombre": nombre_destino}
                ).fetchone()
                id_destino = fila[0] if fila else None

            id_plataforma = None
            if nombre_plataforma:
                fila = conn.execute(
                    text("SELECT id_plataforma FROM dim_plataforma WHERE nombre_plataforma = :nombre"),
                    {"nombre": nombre_plataforma}
                ).fetchone()
                id_plataforma = fila[0] if fila else None

            fila = conn.execute(
                text("SELECT id_alojamiento FROM dim_alojamiento WHERE nombre_alojamiento = :nombre"),
                {"nombre": nombre_alojamiento}
            ).fetchone()
            id_alojamiento = fila[0] if fila else None

            id_fecha, temporada_nombre = resolver_id_fecha(conn, r.get("fecha_extraccion"))
            id_temporada = mapa_temporada_id.get(temporada_nombre)

            # Si falta cualquier FK obligatoria, se omite el registro y se
            # documenta como hallazgo de calidad, en vez de insertar con
            # un valor inventado.
            faltantes = []
            if id_destino is None: faltantes.append("destino")
            if id_plataforma is None: faltantes.append("plataforma")
            if id_alojamiento is None: faltantes.append("alojamiento")
            if id_fecha is None: faltantes.append("fecha")
            if id_temporada is None: faltantes.append("temporada")
            if r.get("precio_noche_usd") is None: faltantes.append("precio")

            if faltantes:
                omitidos_sin_match += 1
                detalle_omitidos.append({
                    "nombre_alojamiento": nombre_alojamiento,
                    "faltantes": faltantes,
                })
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
                    "id_fecha": id_fecha,
                    "id_destino": id_destino,
                    "id_alojamiento": id_alojamiento,
                    "id_plataforma": id_plataforma,
                    "id_temporada": id_temporada,
                    "precio": r.get("precio_noche_usd") if r.get("precio_noche_usd") else None,
                    "rating": r.get("rating_normalizado"),
                    "num_resenas": r.get("num_resenas") or 0,
                    "fuente": r["plataforma"],
                }
            )
            insertados += 1

    print(f"\nInsertados en fact_hospedaje: {insertados}")
    print(f"Omitidos por FK faltante: {omitidos_sin_match}")

    if detalle_omitidos:
        print("\nPrimeros 10 omitidos:")
        for d in detalle_omitidos[:10]:
            print(f"  {d['nombre_alojamiento']} -> faltan: {d['faltantes']}")

    print("\nListo.")


if __name__ == "__main__":
    main()