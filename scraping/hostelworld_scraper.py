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

def extraer_detalle(browser, url_detalle):

    context = browser.new_context()
    page = context.new_page()

    precio_raw = None
    rating_raw = None
    numero_resenas = None

    try:

        page.goto(url_detalle, timeout=60000)
        page.wait_for_timeout(3000)

        texto = page.locator("body").inner_text()

        rating = re.search(r"\b\d+\.\d+\b", texto)
        if rating:
            rating_raw = rating.group()

        resenas = re.search(r"\((\d+)\)", texto)
        if resenas:
            numero_resenas = resenas.group(1)

        precios = re.findall(r"US\$\d+\.\d+", texto)
        if precios:
            precio_raw = precios[0]

    except Exception as e:
        print("Error en alojamiento:", e)

    finally:
        context.close()

    return precio_raw, rating_raw, numero_resenas


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

        enlaces = page.query_selector_all('a[href*="/p/"]')

        urls_vistas = set()

        for enlace in enlaces:

            href = enlace.get_attribute("href")

            if not href:
                continue

            if href.startswith("http"):
                url_detalle = href
            else:
                url_detalle = "https://www.hostelworld.com" + href

            if url_detalle in urls_vistas:
                continue

            urls_vistas.add(url_detalle)

            try:

                texto = enlace.inner_text()

                lineas = [
                    linea.strip()
                    for linea in texto.split("\n")
                    if linea.strip()
                ]

                nombre = None

                if len(lineas) >= 2:
                    nombre = lineas[1]

                precio_raw, rating_raw, numero_resenas = extraer_detalle(
                    browser,
                    url_detalle
                )

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