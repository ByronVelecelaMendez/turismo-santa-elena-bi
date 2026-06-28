import json
import os
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

def scrape_booking(destino: str, browser) -> list:
    resultados = []

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        # Fechas de búsqueda: 30 días desde hoy, estadía de 2 noches
        checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")

        url = (
            f"https://www.booking.com/searchresults.es.html?"
            f"ss={destino.replace(' ', '+')}&lang=es"
            f"&checkin={checkin}&checkout={checkout}"
            f"&group_adults=2&no_rooms=1&group_children=0"
        )
        print(f"Scrapeando Booking: {destino}")

        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        try:
            page.click('[aria-label="Descartar inicio de sesión."]', timeout=3000)
        except:
            pass

        page.wait_for_timeout(2000)

        hoteles = page.query_selector_all('[data-testid="property-card"]')

        if not hoteles:
            print(f"Sin resultados para: {destino}")
            context.close()
            return []

        print(f"Encontrados {len(hoteles)} hoteles")

        for hotel in hoteles:
            try:
                nombre = hotel.query_selector('[data-testid="title"]')
                precio = hotel.query_selector('[data-testid="price-and-discounted-price"]')
                rating = hotel.query_selector('[data-testid="review-score"]')

                resultados.append({
                    "fuente":           "booking",
                    "destino":          destino,
                    "nombre":           nombre.inner_text().strip() if nombre else None,
                    "precio_raw":       precio.inner_text().strip() if precio else None,
                    "rating_raw":       rating.inner_text().strip() if rating else None,
                    "checkin":          checkin,
                    "checkout":         checkout,
                    "fecha_extraccion": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error extrayendo hotel individual: {e}")
                continue

    except Exception as e:
        print(f"Error general scrapeando {destino}: {e}")
    finally:
        context.close()

    return resultados


def guardar_raw(datos: list, destino: str):
    os.makedirs("data/raw/scraping/booking", exist_ok=True)
    nombre_archivo = f"data/raw/scraping/booking/booking_{destino.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"Guardado: {nombre_archivo} ({len(datos)} registros)")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for destino in DESTINOS:
            datos = scrape_booking(destino, browser)
            if datos:
                guardar_raw(datos, destino)

        browser.close()

    print("\nProceso completado.")


if __name__ == "__main__":
    main()