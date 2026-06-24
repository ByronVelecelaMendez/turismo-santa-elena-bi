import json
import os
import re
import pandas as pd
from datetime import datetime

ARCHIVO_ENCUESTA = "data/csv/Experiencia_Turística_en_la_Provincia_de_Santa_Elena.csv"

DESTINOS_VALIDOS = {
    "Salinas": "salinas",
    "La Libertad": "la_libertad",
    "Ayangue": "ayangue",
    "Montañita": "montanita",
    "Punta Carnero": "punta_carnero",
    "Manglaralto": "manglaralto",
}

DESTINOS_FUERA_ALCANCE = {
    "Olón": "olon",
}

RANGOS_PRECIO = {
    "Menos de $30": 15,
    "$30 a $60": 45,
    "$61 a $100": 80,
    "Más de $100": 120,
}


def extraer_rating_numerico(texto):
    if pd.isna(texto):
        return None
    match = re.match(r"^\s*(\d+)", str(texto))
    return int(match.group(1)) if match else None


def main():
    df = pd.read_csv(ARCHIVO_ENCUESTA)

    registros = []
    descartados_fuera_alcance = 0

    for _, fila in df.iterrows():
        destino_raw = str(fila["¿Qué destino de Santa Elena visitó más recientemente?"]).strip()

        if destino_raw in DESTINOS_FUERA_ALCANCE:
            descartados_fuera_alcance += 1
            destino_normalizado = DESTINOS_FUERA_ALCANCE[destino_raw]
            dentro_alcance = False
        elif destino_raw in DESTINOS_VALIDOS:
            destino_normalizado = DESTINOS_VALIDOS[destino_raw]
            dentro_alcance = True
        else:
            destino_normalizado = "sin_clasificar"
            dentro_alcance = False

        registros.append({
            "fuente": "encuesta_propia",
            "marca_temporal": str(fila["Marca temporal"]),
            "origen_visitante": fila["¿De qué provincia o país viene?"],
            "destino_visitado_raw": destino_raw,
            "destino_normalizado": destino_normalizado,
            "dentro_alcance_proyecto": dentro_alcance,
            "temporada_preferida": fila["¿En qué temporada prefiere visitar Santa Elena?"],
            "tipo_alojamiento_preferido": fila["¿Qué tipo de alojamiento prefiere?"],
            "rango_precio_noche": fila["¿Cuánto paga por noche de hospedaje en Santa Elena?"],
            "precio_noche_estimado_usd": RANGOS_PRECIO.get(fila["¿Cuánto paga por noche de hospedaje en Santa Elena?"]),
            "plataforma_reserva": fila["¿A través de qué plataforma reserva su hospedaje?"],
            "rating_precio_calidad": extraer_rating_numerico(fila["¿Cómo califica la relación precio-calidad del hospedaje? (1 al 5)"]),
            "rating_atencion_turista": extraer_rating_numerico(fila["¿Cómo califica la atención al turista en la provincia? (1 al 5)"]),
            "aspecto_a_mejorar": fila["¿Qué aspecto necesita mejorar más el turismo en Santa Elena?"],
            "recomendaria": fila["¿Recomendaría visitar Santa Elena a otras personas?"],
            "fecha_extraccion": datetime.now().isoformat(),
        })

    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = f"data/raw/encuesta_propia_{timestamp}.json"

    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    print(f"Total respuestas procesadas: {len(registros)}")
    print(f"Respuestas fuera de los 6 destinos oficiales (ej. Olón): {descartados_fuera_alcance}")
    print(f"Guardado: {archivo_salida}")

    print("\n=== Resumen rápido ===")
    print("Rating promedio precio-calidad:", round(pd.Series([r["rating_precio_calidad"] for r in registros]).mean(), 2))
    print("Rating promedio atención al turista:", round(pd.Series([r["rating_atencion_turista"] for r in registros]).mean(), 2))


if __name__ == "__main__":
    main()