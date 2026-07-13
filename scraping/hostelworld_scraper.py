import json
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

DESTINOS = {
    "salinas": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/salinas/",
    "montanita": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/montanita/",
    "manglaralto": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/manglaralto/",
    "ayangue": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/ayangue/",
    "punta_carnero": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/punta-carnero/",
    "la_libertad": "https://www.hostelworld.com/es/albergues/america-del-sur/ecuador/la-libertad-ecuador/"
}


def extraer_precio_tarjeta(tarjeta):
    """Lee los bloques de precio de la tarjeta por su etiqueta real
    ("Dormitorios desde" / "Privadas desde"), en vez de adivinar
    posiciones en el texto completo de la página (bug anterior: el
    scraper agarraba un precio fijo de plantilla repetido en todas las
    páginas). Prioriza precio de dormitorio (comparable entre hostales);
    si el hostal no tiene dormitorio disponible, usa el de privada."""
    precio_dormitorio = None
    precio_privada = None

    bloques_precio = tarjeta.query_selector_all(".property-accommodation-price")
    for bloque in bloques_precio:
        etiqueta_el = bloque.query_selector(".accommodation-label")
        valor_el = bloque.query_selector("strong.current")
        if not etiqueta_el or not valor_el:
            continue
        etiqueta = etiqueta_el.inner_text().strip().lower()
        valor = valor_el.inner_text().strip()
        if "dormitorio" in etiqueta:
            precio_dormitorio = valor
        elif "privada" in etiqueta:
            precio_privada = valor

    return precio_dormitorio or precio_privada


def scrape_hostelworld(browser, destino, url):

    resultados = []

    context = browser.new_context()
    page = context.new_page()

    try:

        print(f"\nScrapeando {destino}")

        page.goto(url, timeout=60000)
        page.wait_for_timeout(8000)

        print("Título:", page.title())
        print("URL:", page.url)

        tarjetas = page.query_selector_all("a.property-card-container")
        nombres_vistos = set()

        for tarjeta in tarjetas:

            try:
                nombre_el = tarjeta.query_selector(".property-name span")
                nombre = nombre_el.inner_text().strip() if nombre_el else None

                if nombre and nombre in nombres_vistos:
                    continue

                rating_el = tarjeta.query_selector(".property-rating .score")
                rating_raw = rating_el.inner_text().strip() if rating_el else None

                numero_resenas = None
                resenas_el = tarjeta.query_selector(".property-rating .num-reviews")
                if resenas_el:
                    match = re.search(r"\((\d+)\)", resenas_el.inner_text())
                    if match:
                        numero_resenas = match.group(1)

                precio_raw = extraer_precio_tarjeta(tarjeta)

                # Se descartan tarjetas sin precio: Hostelworld repite
                # algunas propiedades en una sección "destacados" aparte
                # de la lista principal, sin el bloque de precio. La
                # misma propiedad ya aparece con su precio real en otra
                # tarjeta de la lista.
                if precio_raw is None:
                    continue

                href = tarjeta.get_attribute("href")
                if href and not href.startswith("http"):
                    url_detalle = "https://www.hostelworld.com" + href
                else:
                    url_detalle = href

                resultados.append({
                    "fuente": "hostelworld",
                    "destino": destino,
                    "nombre": nombre,
                    "precio_raw": precio_raw,
                    "rating_raw": rating_raw,
                    "numero_resenas": numero_resenas,
                    "url_detalle": url_detalle,
                    "fecha_extraccion": datetime.now().isoformat()
                })

                if nombre:
                    nombres_vistos.add(nombre)

            except Exception:
                continue

    except Exception as e:
        print(e)

    finally:
        context.close()

    print(f"Registros encontrados: {len(resultados)}")

    return resultados


def guardar_raw(datos, destino):

    os.makedirs("data/raw/scraping/hostelworld", exist_ok=True)

    archivo = (
        f"data/raw/scraping/hostelworld/hostelworld_{destino}_ecuador_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print("Guardado:", archivo)


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)

        for destino, url in DESTINOS.items():

            datos = scrape_hostelworld(
                browser,
                destino,
                url
            )

            if datos:
                guardar_raw(datos, destino)

        browser.close()

    print("\nProceso completado.")


if __name__ == "__main__":
    main()