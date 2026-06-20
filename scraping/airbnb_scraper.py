import json
import os
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

DESTINOS = [
    "Montanita Ecuador",
    "Salinas Ecuador",
    "Ayangue Ecuador",
    "Punta Carnero Ecuador",
    "Manglaralto Ecuador",
    "La Libertad Ecuador"
]


def scrape_airbnb(destino: str, browser) -> list:
    resultados = []

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    page = context.new_page()

    try:
        checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")

        destino_url = destino.replace(" ", "-")

        url = (
            f"https://www.airbnb.com/s/{destino_url}/homes?"
            f"checkin={checkin}&checkout={checkout}&adults=2"
        )

        print(f"Scrapeando Airbnb: {destino}")

        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        try:
            page.click('button[aria-label="Cerrar"]', timeout=3000)
        except:
            pass

        page.wait_for_timeout(2000)

        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1500)

        propiedades = page.query_selector_all('[itemprop="itemListElement"]')

        if not propiedades:
            print(f"Sin resultados para: {destino}")
            return []

        print(f"Encontrados {len(propiedades)} alojamientos")

        for prop in propiedades:
            try:
                nombre = prop.query_selector(
                    '[data-testid="listing-card-title"]'
                )

                precio = prop.query_selector(
                    '[data-testid="price-availability-row"]'
                )

                texto_completo = prop.inner_text()

                coincidencia = re.search(
                    r'(\d\.\d)\s*out of 5 average rating,\s*(\d+)\s*reviews',
                    texto_completo
                )

                rating = (
                    f"{coincidencia.group(1)} ({coincidencia.group(2)})"
                    if coincidencia
                    else None
                )

                resultados.append({
                    "fuente": "airbnb",
                    "destino": destino,
                    "nombre": nombre.inner_text().strip() if nombre else None,
                    "precio_raw": precio.inner_text().strip() if precio else None,
                    "rating_raw": rating,
                    "checkin": checkin,
                    "checkout": checkout,
                    "fecha_extraccion": datetime.now().isoformat()
                })

            except Exception as e:
                print(f"Error extrayendo propiedad individual: {e}")
                continue

    except Exception as e:
        print(f"Error general scrapeando {destino}: {e}")

    finally:
        context.close()

    return resultados


def guardar_raw(datos: list, destino: str):
    os.makedirs("data/raw", exist_ok=True)

    nombre_archivo = (
        f"data/raw/airbnb_{destino.replace(' ', '_').lower()}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"Guardado: {nombre_archivo} ({len(datos)} registros)")


def main():
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        for destino in DESTINOS:
            datos = scrape_airbnb(destino, browser)

            if datos:
                guardar_raw(datos, destino)

        browser.close()

    print("\nProceso completado.")


if __name__ == "__main__":
    main()