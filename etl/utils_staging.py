import re
import unicodedata

# ============================================================
# HOMOLOGACIÓN DE DESTINOS
# ============================================================

# Mapa canónico: cualquier variante conocida -> slug oficial (los 6 destinos)
MAPA_DESTINOS = {
    "montanita": "montanita",
    "montañita": "montanita",
    "salinas": "salinas",
    "ayangue": "ayangue",
    "punta carnero": "punta_carnero",
    "manglaralto": "manglaralto",
    "la libertad": "la_libertad",
}

DESTINOS_OFICIALES = {
    "salinas", "montanita", "ayangue",
    "punta_carnero", "manglaralto", "la_libertad",
}


def quitar_acentos(texto: str) -> str:
    """Convierte 'Montañita' -> 'Montanita' para comparar sin tildes."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def homologar_destino(destino_raw: str) -> dict:
    """
    Recibe cualquier variante de texto de destino (ej. 'Ayangue Ecuador',
    'MANGLARALTO', 'Montañita') y devuelve el slug oficial homologado.

    Retorna un dict con:
        - destino_slug: el nombre oficial homologado, o 'sin_clasificar'
        - dentro_alcance: True/False si es uno de los 6 destinos del proyecto
    """
    if not destino_raw:
        return {"destino_slug": "sin_clasificar", "dentro_alcance": False}

    texto = quitar_acentos(str(destino_raw)).lower().strip()
    texto = texto.replace("ecuador", "").replace(",", " ").strip()
    texto = re.sub(r"\s+", " ", texto)

    if texto in MAPA_DESTINOS:
        slug = MAPA_DESTINOS[texto]
        return {"destino_slug": slug, "dentro_alcance": slug in DESTINOS_OFICIALES}

    # Búsqueda parcial: por si viene con texto adicional, ej. "playa de ayangue"
    for variante, slug in MAPA_DESTINOS.items():
        if variante in texto:
            return {"destino_slug": slug, "dentro_alcance": slug in DESTINOS_OFICIALES}

    return {"destino_slug": "sin_clasificar", "dentro_alcance": False}


# ============================================================
# NORMALIZACIÓN DE PRECIO
# ============================================================

def extraer_precio_usd(texto: str) -> float | None:
    """
    Extrae un valor numérico de precio desde texto sucio.
    Solo considera números precedidos por el símbolo $ (evita confundir
    con números sueltos como "2" de "for 2 nights").
    Si hay múltiples montos (ej. precio tachado + precio con descuento),
    toma el ÚLTIMO encontrado, que suele ser el precio final/actual.
    """
    if not texto:
        return None

    montos = re.findall(r"\$\s?([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)", texto)
    if not montos:
        return None

    valores = []
    for m in montos:
        limpio = m.replace(".", "").replace(",", ".") if ("," in m and "." in m) else m.replace(",", "")
        try:
            valores.append(float(limpio))
        except ValueError:
            continue

    if not valores:
        return None

    return valores[-1]


def precio_total_a_por_noche(precio_total: float, noches: int = 2) -> float | None:
    """Convierte precio total de estadia a precio por noche."""
    if precio_total is None or noches <= 0:
        return None
    return round(precio_total / noches, 2)


# ============================================================
# NORMALIZACIÓN DE RATING (todas las fuentes -> escala 1.00 a 5.00)
# ============================================================

def normalizar_rating(rating_raw: str, escala_origen: str) -> float | None:
    """
    escala_origen puede ser:
        'booking'    -> viene en escala 0-10, se divide entre 2
        'kayak'      -> viene en escala 0-10, se divide entre 2
        'airbnb'     -> ya viene en escala 1-5, se usa directo
        'hostelworld'-> viene en escala 0-10, se divide entre 2
    """
    if not rating_raw:
        return None

    match = re.search(r"(\d{1,2}[.,]\d)", str(rating_raw))
    if not match:
        return None

    valor = float(match.group(1).replace(",", "."))

    if escala_origen in ("booking", "kayak", "hostelworld"):
        valor = valor / 2

    if valor < 1:
        valor = 1.0
    if valor > 5:
        valor = 5.0

    return round(valor, 2)


def extraer_num_resenas(texto: str) -> int | None:
    """Extrae numero de reseñas desde texto como '(398)' o '1.170 comentarios'."""
    if not texto:
        return None

    match = re.search(r"([\d][\d.,]*)\s*(?:comentarios|opiniones|reviews|\))", str(texto))
    if not match:
        match = re.search(r"\((\d[\d.,]*)\)", str(texto))

    if not match:
        return None

    numero = match.group(1).replace(".", "").replace(",", "")
    try:
        return int(numero)
    except ValueError:
        return None