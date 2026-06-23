import json
import os
import time
from datetime import datetime
from pytrends.request import TrendReq

DESTINOS = [
    "Montañita",
    "Salinas Ecuador",
    "Ayangue",
    "Punta Carnero",
    "Manglaralto",
    "La Libertad Ecuador",
]

GEO = "EC"
TIMEFRAME = "today 12-m"
MAX_TERMINOS_POR_CONSULTA = 5


def dividir_en_lotes(lista, tamano):
    for i in range(0, len(lista), tamano):
        yield lista[i:i + tamano]


def consultar_lote(pytrends, lote, intentos=3):
    for intento in range(1, intentos + 1):
        try:
            pytrends.build_payload(lote, cat=0, timeframe=TIMEFRAME, geo=GEO)
            df = pytrends.interest_over_time()
            return df
        except Exception as e:
            print(f"  [Intento {intento}/{intentos}] Error: {e}")
            if intento < intentos:
                espera = 15 * intento
                print(f"  Esperando {espera}s antes de reintentar...")
                time.sleep(espera)
    return None


def main():
    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    pytrends = TrendReq(hl="es-EC", tz=-300)

    resultados = []

    for lote in dividir_en_lotes(DESTINOS, MAX_TERMINOS_POR_CONSULTA):
        print(f"\nConsultando lote: {lote}")
        df = consultar_lote(pytrends, lote)

        if df is None or df.empty:
            print(f"  [AVISO] Sin datos para este lote: {lote}")
            continue

        df = df.drop(columns=["isPartial"], errors="ignore")

        for fecha, fila in df.iterrows():
            for destino in lote:
                if destino in fila:
                    resultados.append({
                        "fuente": "google_trends",
                        "destino_busqueda": destino,
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "interes_relativo": int(fila[destino]),
                        "geo": GEO,
                        "fecha_extraccion": datetime.now().isoformat(),
                    })

        print(f"  -> {len(df)} semanas de datos para {len(lote)} términos")
        time.sleep(10)

    archivo = f"data/raw/google_trends_santa_elena_{timestamp}.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {archivo}")
    print(f"Total registros: {len(resultados)}")


if __name__ == "__main__":
    main()