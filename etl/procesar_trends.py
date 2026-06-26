import os
import json
import re
import unicodedata
from datetime import datetime

MAPA_DESTINOS = {
    "montanita": "montanita",
    "montañita": "montanita",
    "salinas": "salinas",
    "ayangue": "ayangue",
    "punta carnero": "punta_carnero",
    "manglaralto": "manglaralto",
    "la libertad": "la_libertad",
}


def quitar_acentos(texto):
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def homologar_destino(destino_raw):
    if not destino_raw:
        return "sin_clasificar"
    texto = quitar_acentos(str(destino_raw)).lower().strip()
    texto = texto.replace("ecuador", "").strip()
    texto = re.sub(r"\s+", " ", texto)
    return MAPA_DESTINOS.get(texto, "sin_clasificar")


def procesar_trends_staging():
    ruta_raw = "data/raw"
    ruta_output = "data/staging"

    archivos = [f for f in os.listdir(ruta_raw) if "trends" in f.lower() and f.endswith(".json")]

    if not archivos:
        print("[-] No se encontraron archivos crudos de Google Trends en data/raw/.")
        return

    archivos.sort()
    ultimo_archivo = os.path.join(ruta_raw, archivos[-1])
    print(f"[*] Leyendo archivo crudo de Google Trends: {ultimo_archivo}")
    with open(ultimo_archivo, "r", encoding="utf-8") as f:
        registros_trends = json.load(f)

    registros_limpios = []
    sin_clasificar = 0

    for reg in registros_trends:
        destino_raw = reg.get("destino_busqueda")  # <-- nombre real del campo
        destino = homologar_destino(destino_raw)
        if destino == "sin_clasificar":
            sin_clasificar += 1

        registros_limpios.append({
            "fuente": "google_trends",
            "fecha": reg.get("fecha") or datetime.now().strftime("%Y-%m-%d"),
            "destino_homologado": destino,
            "interes_busqueda": int(reg.get("interes_relativo") or 0),  # <-- nombre real del campo
            "fecha_proceso": datetime.now().isoformat()
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_final = os.path.join(ruta_output, f"staging_trends_{timestamp}.json")

    with open(ruta_final, "w", encoding="utf-8") as f:
        json.dump(registros_limpios, f, ensure_ascii=False, indent=2)

    print(f"[+] ÉXITO STAGING: Google Trends procesado en: {ruta_final}")
    print(f"[*] Total de métricas temporales en staging: {len(registros_limpios)}")
    print(f"[*] Sin clasificar: {sin_clasificar}")


if __name__ == "__main__":
    procesar_trends_staging()
