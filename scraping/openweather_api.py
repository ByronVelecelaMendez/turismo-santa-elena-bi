import json
import os
import requests
from datetime import datetime

API_KEY = "061eb338d8b760bffebf2ec0c408bdce"

DESTINOS = {
    "salinas": (-2.214520, -80.951510),
    "la_libertad": (-2.227500, -80.910100),
    "punta_carnero": (-2.216700, -80.966700),
    "montanita": (-1.833300, -80.766700),
    "ayangue": (-1.966700, -80.750000),
    "manglaralto": (-1.866700, -80.733300),
}

URL_BASE = "https://api.openweathermap.org/data/2.5/weather"


def consultar_clima(destino, lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "lang": "es",
    }

    respuesta = requests.get(URL_BASE, params=params, timeout=15)

    if respuesta.status_code != 200:
        print(f"Error en {destino}: {respuesta.status_code} - {respuesta.text}")
        return None

    data = respuesta.json()

    return {
        "fuente": "openweather",
        "destino": destino,
        "latitud": lat,
        "longitud": lon,
        "temperatura_c": data.get("main", {}).get("temp"),
        "temperatura_sensacion_c": data.get("main", {}).get("feels_like"),
        "temperatura_min_c": data.get("main", {}).get("temp_min"),
        "temperatura_max_c": data.get("main", {}).get("temp_max"),
        "humedad_pct": data.get("main", {}).get("humidity"),
        "presion_hpa": data.get("main", {}).get("pressure"),
        "condicion_clima": data.get("weather", [{}])[0].get("description"),
        "nubosidad_pct": data.get("clouds", {}).get("all"),
        "viento_velocidad_ms": data.get("wind", {}).get("speed"),
        "precipitacion_mm": data.get("rain", {}).get("1h", 0),
        "fecha_extraccion": datetime.now().isoformat(),
    }


def main():
    os.makedirs("data/raw/api/openweather", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resultados = []

    for destino, (lat, lon) in DESTINOS.items():
        print(f"Consultando clima en {destino}...")
        dato = consultar_clima(destino, lat, lon)
        if dato:
            resultados.append(dato)
            print(f"  -> {dato['temperatura_c']}°C, {dato['condicion_clima']}")

    archivo = f"data/raw/api/openweather/openweather_santa_elena_{timestamp}.json"
    
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {archivo}")
    print(f"Total destinos consultados: {len(resultados)}")


if __name__ == "__main__":
    main()