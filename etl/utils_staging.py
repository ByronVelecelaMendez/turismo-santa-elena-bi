import re
import unicodedata




def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    return str(texto).strip().lower()


def quitar_acentos(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))




MAPA_DESTINOS = {
    "montanita": "montanita",
    "montañita": "montanita",
    "salinas": "salinas",
    "ayangue": "ayangue",
    "manglaralto": "manglaralto",
    "la libertad": "la_libertad",
    "la_libertad": "la_libertad",
    "punta carnero": "punta_carnero",
}

DESTINOS_OFICIALES = {
    "salinas", "montanita", "ayangue",
    "punta_carnero", "manglaralto", "la_libertad"
}


def homologar_destino(destino_raw: str) -> dict:
    if not destino_raw:
        return {"destino_slug": "sin_clasificar", "dentro_alcance": False}

    texto = quitar_acentos(destino_raw).lower().strip()
    texto = texto.replace("_", " ")
    texto = re.sub(r"\s+", " ", texto)

    if texto in MAPA_DESTINOS:
        slug = MAPA_DESTINOS[texto]
        return {
            "destino_slug": slug,
            "dentro_alcance": slug in DESTINOS_OFICIALES
        }

    for k, v in MAPA_DESTINOS.items():
        if k in texto:
            return {
                "destino_slug": v,
                "dentro_alcance": v in DESTINOS_OFICIALES
            }

    return {"destino_slug": "sin_clasificar", "dentro_alcance": False}




def extraer_precio_usd(texto: str) -> float | None:
    """
    Extrae un valor numerico de precio desde texto sucio.
    Ignora explicitamente frases tipo "Pay $0 today" (el monto que se paga
    HOY en Airbnb, no el precio de la estadia), que antes contaminaba la
    extraccion al ser el ultimo '$' encontrado en el texto.
    Si hay multiples montos restantes (precio tachado + precio con
    descuento), toma el ULTIMO, que suele ser el precio final/actual.
    """
    if not texto:
        return None

    texto_limpio = re.sub(r"[Pp]ay\s*\$\s?[\d.,]+\s*today", "", texto)

    montos = re.findall(r"\$\s?([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)", texto_limpio)
    if not montos:
        return None

    valores = []
    for m in montos:
        import re as _re
        # Caso 1: punto seguido de exactamente 3 digitos al final
        # -> separador de miles latinoamericano (ej. "1.170" = 1170)
        if _re.search(r'\.\d{3}$', m):
            limpio = m.replace(".", "").replace(",", "")
        # Caso 2: coma seguida de exactamente 3 digitos al final (sin decimal)
        # -> separador de miles americano (ej. "1,040" = 1040)
        elif _re.search(r',\d{3}$', m) and '.' not in m:
            limpio = m.replace(",", "")
        # Caso 3: coma Y punto presentes -> formato "1,234.56"
        elif "," in m and "." in m:
            limpio = m.replace(",", "")
        # Caso 4: sin separador de miles
        else:
            limpio = m.replace(",", ".")
        try:
            valores.append(float(limpio))
        except ValueError:
            continue

    if not valores:
        return None

    return valores[-1]


def precio_total_a_por_noche(precio_total: float, noches: int = 2):
    if not precio_total or noches <= 0:
        return None
    return round(precio_total / noches, 2)




def normalizar_rating(rating_raw: str, fuente: str):
    if not rating_raw:
        return None

    match = re.search(r"(\d{1,2}[.,]\d)", str(rating_raw))
    if not match:
        return None

    valor = float(match.group(1).replace(",", "."))

    if fuente in ("booking", "kayak", "hostelworld"):
        valor = valor / 2

    return round(min(max(valor, 1), 5), 2)



def extraer_num_resenas(texto: str):
    if not texto:
        return None

    match = re.search(r"(\d[\d,.]*)", str(texto))
    if not match:
        return None

    try:
        return int(match.group(1).replace(",", "").replace(".", ""))
    except:
        return None


TIPOS_ALOJAMIENTO_CONOCIDOS = [
    "Hotel boutique", "Bed and breakfast", "Casa de huéspedes",
    "Hotel", "Hostal", "Hostel", "Lodge", "Eco-lodge", "Glamping",
    "Hacienda", "Resort", "Villa", "Apartamento", "Departamento", "Casa",
]


def extraer_tipo_alojamiento(texto: str) -> str | None:
    """Busca el tipo de alojamiento dentro de un texto crudo, probando
    las frases mas especificas primero para no perder matices
    (ej. 'Hotel boutique' antes que 'Hotel')."""
    if not texto:
        return None
    for tipo in TIPOS_ALOJAMIENTO_CONOCIDOS:
        if tipo.lower() in str(texto).lower():
            return tipo
    return None

def extraer_tipo_alojamiento_url(url: str) -> str | None:
    """Hostelworld estructura sus URLs por categoria:
    /es/hoteles/, /es/albergues/, /es/pensiones/, etc.
    Esto es mas confiable que buscar texto libre."""
    if not url:
        return None
    mapa_url = {
        "/hoteles/": "Hotel",
        "/albergues/": "Hostel",
        "/pensiones/": "Casa de huéspedes",
        "/apartamentos/": "Apartamento",
    }
    url_lower = str(url).lower()
    for fragmento, tipo in mapa_url.items():
        if fragmento in url_lower:
            return tipo
    return None