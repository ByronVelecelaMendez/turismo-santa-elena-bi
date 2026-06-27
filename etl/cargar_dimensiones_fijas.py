"""
Carga de dimensiones con datos fijos/catalogo:
  - DIM_PLATAFORMA (8 fuentes del proyecto)
  - DIM_DESTINO (6 destinos oficiales)

Estas tablas no dependen de los archivos de staging, son catalogos
que se definen una sola vez segun la documentacion del proyecto (E1/E2).
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.conexion import get_engine


# ============================================================
# DIM_PLATAFORMA
# ============================================================

PLATAFORMAS = [
    {"nombre_plataforma": "Booking", "tipo_fuente": "scraping", "url_base": "https://www.booking.com"},
    {"nombre_plataforma": "Airbnb", "tipo_fuente": "scraping", "url_base": "https://www.airbnb.com"},
    {"nombre_plataforma": "KAYAK", "tipo_fuente": "scraping", "url_base": "https://www.kayak.com.ec"},
    {"nombre_plataforma": "Hostelworld", "tipo_fuente": "scraping", "url_base": "https://www.hostelworld.com"},
    {"nombre_plataforma": "OpenWeather", "tipo_fuente": "api", "url_base": "https://openweathermap.org/api"},
    {"nombre_plataforma": "MINTUR", "tipo_fuente": "csv", "url_base": "https://servicios.turismo.gob.ec"},
    {"nombre_plataforma": "Google Forms", "tipo_fuente": "encuesta", "url_base": "https://forms.gle"},
    {"nombre_plataforma": "Google Trends", "tipo_fuente": "api", "url_base": "https://trends.google.com"},
]


# ============================================================
# DIM_DESTINO
# ============================================================

DESTINOS = [
    {
        "nombre_destino": "Montañita", "tipo_destino": "pueblo_artesanal",
        "canton": "Santa Elena", "latitud": -1.833300, "longitud": -80.766700,
    },
    {
        "nombre_destino": "Salinas", "tipo_destino": "playa",
        "canton": "Salinas", "latitud": -2.214520, "longitud": -80.951510,
    },
    {
        "nombre_destino": "Ayangue", "tipo_destino": "playa",
        "canton": "Santa Elena", "latitud": -1.966700, "longitud": -80.750000,
    },
    {
        "nombre_destino": "Punta Carnero", "tipo_destino": "playa",
        "canton": "Salinas", "latitud": -2.216700, "longitud": -80.966700,
    },
    {
        "nombre_destino": "Manglaralto", "tipo_destino": "playa",
        "canton": "Santa Elena", "latitud": -1.866700, "longitud": -80.733300,
    },
    {
        "nombre_destino": "La Libertad", "tipo_destino": "playa",
        "canton": "La Libertad", "latitud": -2.227500, "longitud": -80.910100,
    },
]


def cargar_dim_plataforma(engine):
    with engine.begin() as conn:
        for p in PLATAFORMAS:
            existe = conn.execute(
                text("SELECT 1 FROM dim_plataforma WHERE nombre_plataforma = :nombre"),
                {"nombre": p["nombre_plataforma"]}
            ).fetchone()

            if existe:
                print(f"  [SKIP] Ya existe: {p['nombre_plataforma']}")
                continue

            conn.execute(
                text("""
                    INSERT INTO dim_plataforma (nombre_plataforma, tipo_fuente, url_base)
                    VALUES (:nombre_plataforma, :tipo_fuente, :url_base)
                """),
                p
            )
            print(f"  [OK] Insertado: {p['nombre_plataforma']}")


def cargar_dim_destino(engine):
    with engine.begin() as conn:
        for d in DESTINOS:
            existe = conn.execute(
                text("SELECT 1 FROM dim_destino WHERE nombre_destino = :nombre"),
                {"nombre": d["nombre_destino"]}
            ).fetchone()

            if existe:
                print(f"  [SKIP] Ya existe: {d['nombre_destino']}")
                continue

            conn.execute(
                text("""
                    INSERT INTO dim_destino (nombre_destino, tipo_destino, canton, latitud, longitud)
                    VALUES (:nombre_destino, :tipo_destino, :canton, :latitud, :longitud)
                """),
                d
            )
            print(f"  [OK] Insertado: {d['nombre_destino']}")


def main():
    engine = get_engine()

    print("=== Cargando DIM_PLATAFORMA ===")
    cargar_dim_plataforma(engine)

    print("\n=== Cargando DIM_DESTINO ===")
    cargar_dim_destino(engine)

    print("\nListo.")


if __name__ == "__main__":
    main()