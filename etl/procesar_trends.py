import os
import json
import re
import unicodedata
from datetime import datetime

# Mapa de homologacion: cualquier variante de texto de destino que devuelva
# la API de Google Trends se reduce a uno de los 6 slugs oficiales del
# proyecto. Esto replica la misma logica que utils_staging.py usa para las
# demas fuentes, para que todos los datasets compartan el mismo vocabulario
# de destinos y se puedan cruzar entre si en el dashboard.
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
    """Normaliza texto removiendo tildes, para que la comparacion contra
    MAPA_DESTINOS no falle por diferencias de acentuacion (ej. 'Montañita'
    vs 'Montanita')."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def homologar_destino(destino_raw):
    """Limpia y homologa el nombre de destino que viene de Google Trends.
    Se quita el sufijo 'Ecuador' porque varios terminos de busqueda lo
    incluyen para mejorar la precision de la consulta (ej. 'Salinas Ecuador'),
    pero ese sufijo no debe formar parte del slug final."""
    if not destino_raw:
        return "sin_clasificar"
    texto = quitar_acentos(str(destino_raw)).lower().strip()
    texto = texto.replace("ecuador", "").strip()
    texto = re.sub(r"\s+", " ", texto)
    return MAPA_DESTINOS.get(texto, "sin_clasificar")


def procesar_trends_staging():
    # IMPORTANTE: tras la reorganizacion de la Zona Raw en subcarpetas por
    # tipo de fuente (ver README), Google Trends se guarda en
    # data/raw/api/google_trends/, no directo en data/raw/.
    ruta_raw = "data/raw/api/google_trends"
    ruta_output = "data/staging"

    archivos = [f for f in os.listdir(ruta_raw) if "trends" in f.lower() and f.endswith(".json")]

    if not archivos:
        print("[-] No se encontraron archivos crudos de Google Trends en data/raw/api/google_trends/.")
        return

    archivos.sort()
    ultimo_archivo = os.path.join(ruta_raw, archivos[-1])
    print(f"[*] Leyendo archivo crudo de Google Trends: {ultimo_archivo}")
    with open(ultimo_archivo, "r", encoding="utf-8") as f:
        registros_trends = json.load(f)

    registros_limpios = []
    sin_clasificar = 0

    for reg in registros_trends:
        # Los nombres de campo "destino_busqueda" e "interes_relativo" son
        # los que realmente genera scraping/google_trends_scraper.py.
        # (Una version anterior de este script usaba "destino" e
        # "interes_busqueda", que no existian en el JSON crudo, causando
        # que el 100% de los registros cayera en sin_clasificar con
        # interes en 0 sin ningun error visible. Ver Anexo de calidad E3.)
        destino_raw = reg.get("destino_busqueda")
        destino = homologar_destino(destino_raw)
        if destino == "sin_clasificar":
            sin_clasificar += 1

        registros_limpios.append({
            "fuente": "google_trends",
            "fecha": reg.get("fecha") or datetime.now().strftime("%Y-%m-%d"),
            "destino_homologado": destino,
            "interes_busqueda": int(reg.get("interes_relativo") or 0),
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