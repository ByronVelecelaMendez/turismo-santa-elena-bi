import json
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DESTINOS = {
    "salinas": "https://www.es.kayak.com/hotels/Salinas,Provincia-de-Santa-Elena,Ecuador-p50381/2026-06-29/2026-07-06/2adults;map?ucs=1tssvuh&sort=rank_a",
    "montanita": "https://www.kayak.com.ec/Hoteles-en-Montanita-Guayas-.59002.hotel.ksp",
    "manglaralto": "https://www.kayak.com.ec/hotels/Olon,Ecuador-p2637203/2026-07-02/2026-07-31/2adults;map?ucs=e1vrmg&sort=rank_a",
    "ayangue": "https://www.kayak.com.ec/hotels/Ayangue,Ecuador-p302544/2026-07-02/2026-07-31/2adults;map?ucs=e1vrmg&sort=rank_a",
    "la_libertad": "https://www.kayak.com.ec/hotels/La-Libertad,Ecuador-p50432/2026-07-02/2026-07-31/2adults;map?ucs=e1vrmg&sort=rank_a",
    "punta_carnero": "https://www.kayak.com.ec/hotels/Punta-Carnero,Ecuador-gChIJVaag1GMPLpARgYP7WwrYfWQ/2026-07-02/2026-07-31/2adults;map?ucs=e1vrmg&sort=distance_a"
}

CANTONES = {
    "salinas": "Salinas",
    "montanita": "Santa Elena",
    "manglaralto": "Santa Elena",
    "ayangue": "Santa Elena",
    "la_libertad": "La Libertad",
    "punta_carnero": "Salinas"
}



def es_ruido(t):
    if not t:
        return True
    if len(t) < 40:
        return True
    basura = ["Ir al", "Buscar", "Filtros", "KAYAK", "Anuncio", "Booking"]
    return any(b.lower() in t.lower() for b in basura)


def limpiar_texto(texto):
    if not texto:
        return None
    try:
        return texto.encode("latin1").decode("utf-8")
    except:
        return texto


def extraer_precio(t):
    m = re.search(r"\$\s?\d+(?:\.\d+)?", t)
    return m.group(0) if m else None


def extraer_rating(t):
    m = re.search(r"\b\d{1,2}[.,]\d\b", t)
    return m.group(0).replace(",", ".") if m else None


def extraer_num_resenas(t):
    m = re.search(r"\((\d[\d.,]*)\)", t)
    return m.group(1).replace(".", "").replace(",", "") if m else None


def scroll(page):
    for _ in range(6):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1500)
    page.keyboard.press("End")
    page.wait_for_timeout(3000)


def safe_goto(page, url):
    for i in range(3):
        try:
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            return True
        except PlaywrightTimeoutError:
            print(f"Reintentando carga... ({i+1}/3)")
    return False




def scrape(destino, url, browser):
    context = browser.new_context(
        locale="es-EC",
        user_agent="Mozilla/5.0",
        viewport={"width": 1280, "height": 800}
    )

    page = context.new_page()
    resultados = []

    try:
        print("Scrapeando:", destino)

        if not safe_goto(page, url):
            print("No se pudo cargar:", destino)
            return []

        page.wait_for_timeout(6000)
        scroll(page)

        bloques = page.query_selector_all("div")
        vistos = set()

        for b in bloques:
            try:
                texto = limpiar_texto(b.inner_text().strip())

                if es_ruido(texto):
                    continue

                if "$" not in texto:
                    continue

                lineas = [l.strip() for l in texto.split("\n") if l.strip()]
                if len(lineas) < 3:
                    continue

                nombre = next(
                    (l for l in lineas
                     if not l.startswith("$")
                     and not re.match(r"^\d+(\.\d+)?$", l)
                     and len(l) > 5),
                    None
                )

                if not nombre:
                    continue

                if nombre.startswith("$"):
                    continue

                if nombre in vistos:
                    continue

                precio = extraer_precio(texto)
                rating = extraer_rating(texto)

                if not precio:
                    continue

                vistos.add(nombre)

                resultados.append({
                    "fuente": "kayak",
                    "destino": destino,
                    "provincia": "Santa Elena",
                    "canton": CANTONES.get(destino, "Santa Elena"),
                    "nombre": nombre,
                    "precio_raw": precio,
                    "rating_raw": rating,
                    "num_resenas": extraer_num_resenas(texto),
                    "raw": texto,
                    "fecha_extraccion": datetime.now().isoformat()
                })

            except Exception:
                continue

    except Exception as e:
        print("Error en:", destino, e)

    finally:
        context.close()

    return resultados


def guardar(data, destino):
    os.makedirs("data/raw/scraping/kayak", exist_ok=True)

    archivo = f"data/raw/scraping/kayak/kayak_{destino}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Guardado:", archivo)



def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        for destino, url in DESTINOS.items():
            data = scrape(destino, url, browser)

            if data:
                guardar(data, destino)
            else:
                print("Sin resultados:", destino)

        browser.close()

    print("Proceso completado")


if __name__ == "__main__":
    main()