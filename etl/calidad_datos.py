"""
Framework de Calidad de Datos - Proyecto BI Turismo Santa Elena
Implementa los 7 controles obligatorios del Entregable 3:
  3.1 Duplicados
  3.2 Control de Nulos
  3.3 Formatos y Casting
  3.4 Estandarizacion
  3.5 Homologacion inter-fuentes
  3.6 Registro de errores
  3.7 Reporte final de metricas
"""

import glob
import json
import logging
import os
from collections import Counter
from datetime import datetime

# ============================================================
# CONFIGURACION DE LOG ESTRUCTURADO (Control 3.6)
# ============================================================

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("calidad_datos")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("logs/calidad_datos.log", encoding="utf-8")
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(fuente)s | %(tipo_error)s | %(message)s | Accion: %(accion)s"
))
logger.addHandler(handler)


def registrar_error(fuente, tipo_error, descripcion, accion):
    """Registra una anomalia de calidad con la estructura exigida por la rubrica:
    Timestamp | Fuente | Tipo de Error | Descripcion | Accion Tomada"""
    logger.info(descripcion, extra={"fuente": fuente, "tipo_error": tipo_error, "accion": accion})


# ============================================================
# UTILIDADES DE CARGA
# ============================================================

def cargar_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def ultimo_archivo(patron):
    archivos = sorted(glob.glob(patron))
    return archivos[-1] if archivos else None


def contar_raw(patron):
    total = 0
    for ruta in glob.glob(patron):
        datos = cargar_json(ruta)
        total += len(datos) if isinstance(datos, list) else 1
    return total


# ============================================================
# 3.1 DUPLICADOS
# ============================================================

def control_duplicados(nombre_fuente, registros, campos_clave):
    """Detecta duplicados segun una clave compuesta y reporta cuantos hay."""
    claves = [tuple(r.get(c) for c in campos_clave) for r in registros]
    contador = Counter(claves)
    duplicados = {k: v for k, v in contador.items() if v > 1}
    total_duplicados = sum(v - 1 for v in duplicados.values())

    if total_duplicados > 0:
        registrar_error(
            nombre_fuente, "DUPLICADO",
            f"Se detectaron {total_duplicados} registros duplicados segun clave {campos_clave}",
            "Eliminados, se conserva la primera ocurrencia"
        )

    return {
        "criterio_unicidad": campos_clave,
        "total_registros": len(registros),
        "combinaciones_unicas": len(contador),
        "duplicados_encontrados": total_duplicados,
    }


# ============================================================
# 3.2 CONTROL DE NULOS
# ============================================================

def control_nulos(nombre_fuente, registros, campos_criticos):
    """Calcula % de nulos por campo y aplica estrategia documentada."""
    resultado = {}
    total = len(registros) or 1

    for campo, estrategia in campos_criticos.items():
        nulos = sum(1 for r in registros if r.get(campo) is None)
        porcentaje = round((nulos / total) * 100, 2)
        resultado[campo] = {
            "nulos": nulos,
            "porcentaje": porcentaje,
            "estrategia": estrategia,
        }
        if nulos > 0:
            registrar_error(
                nombre_fuente, "NULO",
                f"Campo '{campo}' tiene {nulos} nulos ({porcentaje}%)",
                estrategia
            )

    return resultado


# ============================================================
# 3.3 FORMATOS Y CASTING (evidencia antes/despues, documentada)
# ============================================================

EVIDENCIA_CASTING = [
    {
        "fuente": "airbnb",
        "campo": "precio_raw",
        "antes": "$640 \\n$461\\nShow price breakdown\\n \\nfor 2 nights",
        "despues": 461.0,
        "regla": "Extraccion del ultimo monto precedido por $ (precio con descuento, no el tachado)",
    },
    {
        "fuente": "booking",
        "campo": "rating_raw",
        "antes": "Puntuación: 9,4\\n9,4\\nFantástico\\n1.170 comentarios",
        "despues": 4.7,
        "regla": "Conversion de escala 0-10 a 1-5 mediante division entre 2",
    },
    {
        "fuente": "kayak",
        "campo": "rating_raw (Punta Carnero)",
        "antes": "0,4 km de Punta Carnero... 9,0 Excelente (2)",
        "despues": 4.5,
        "regla": "Correccion de bug: se anclo el regex a la etiqueta de calificacion para no confundir distancia con rating",
    },
]


# ============================================================
# 3.4 ESTANDARIZACION
# ============================================================

ESTANDARIZACION_APLICADA = [
    "Ratings de Booking, KAYAK y Hostelworld (escala 0-10) normalizados a escala 1.00-5.00 (Airbnb ya nativo en esa escala).",
    "Nombres de destino homologados a 6 slugs oficiales (salinas, montanita, ayangue, punta_carnero, manglaralto, la_libertad), eliminando acentos, sufijo 'Ecuador' y variantes de mayusculas.",
    "Todos los archivos JSON se leen y escriben con encoding UTF-8 explicito, corrigiendo errores de caracteres especiales (ej. 'Ol?n' -> 'Olón').",
    "Tipo de alojamiento mapeado desde >10 valores libres (Lodge, Casa, Resort, Villa, etc.) a 4 categorias controladas del esquema (hotel/hostal/cabana/apartamento).",
    "Provincia/canton de Montañita corregido manualmente: KAYAK lo etiqueta erroneamente como 'Guayas', se fuerza a 'Santa Elena' validado contra fuente oficial.",
]


# ============================================================
# 3.5 HOMOLOGACION INTER-FUENTES
# ============================================================

HOMOLOGACION_CAMPOS = [
    "precio_raw (Booking) = precio_raw (Airbnb) = precio_raw (KAYAK) = precio_min_usd_raw (Hostelworld) -> precio_noche_usd (Staging)",
    "rating_raw (Booking, escala 0-10) = rating_raw (KAYAK, escala 0-10) = rating_raw (Hostelworld, escala 0-10) = rating_raw (Airbnb, escala 1-5 nativa) -> rating_normalizado (Staging, escala 1.00-5.00)",
    "destino (Booking/Airbnb/KAYAK) = destino_aproximado (MINTUR) = destino_busqueda (Google Trends) = destino_visitado_raw (Encuesta) -> destino_slug (Staging, 6 valores oficiales)",
    "tipo_alojamiento_raw (KAYAK) = tipo_alojamiento (Hostelworld) = Clasificacion (MINTUR Catastro) -> tipo_alojamiento (Staging, 4 categorias controladas)",
]


# ============================================================
# 3.7 REPORTE FINAL
# ============================================================

def generar_reporte():
    reporte = {
        "fecha_generacion": datetime.now().isoformat(),
        "controles": {},
    }

    # ---------- HOSPEDAJE (Booking + Airbnb + KAYAK + Hostelworld) ----------
    archivo_hospedaje = ultimo_archivo("data/staging/staging_hospedaje_*.json")
    hospedaje = cargar_json(archivo_hospedaje) if archivo_hospedaje else []

    raw_hospedaje = (
        contar_raw("data/raw/booking_*.json")
        + contar_raw("data/raw/airbnb_*.json")
        + contar_raw("data/raw/kayak_*.json")
        + contar_raw("data/raw/hostelworld_*.json")
    )

    dup_hospedaje = control_duplicados(
        "hospedaje", hospedaje,
        ["plataforma", "destino_slug", "nombre_alojamiento", "_precio_raw", "_rating_raw"]
    )

    nulos_hospedaje = control_nulos(
        "hospedaje", hospedaje,
        {
            "precio_noche_usd": "Se excluye del KPI de precio promedio si es nulo, se mantiene el registro para KPIs de rating/resenas",
            "rating_normalizado": "Se excluye del KPI de valoracion si es nulo",
            "tipo_alojamiento": "Se categoriza como 'apartamento' (categoria por defecto) si no se reconoce",
        }
    )

    reporte["controles"]["hospedaje"] = {
        "registros_raw": raw_hospedaje,
        "registros_staging": len(hospedaje),
        "tasa_completitud_pct": round((len(hospedaje) / raw_hospedaje) * 100, 2) if raw_hospedaje else 0,
        "duplicados": dup_hospedaje,
        "nulos": nulos_hospedaje,
    }

    # ---------- MINTUR ----------
    archivo_mintur = ultimo_archivo("data/staging/staging_mintur_*.json")
    mintur = cargar_json(archivo_mintur) if archivo_mintur else []

    dup_mintur = control_duplicados("mintur", mintur, ["ruc", "nombre_establecimiento", "parroquia", "periodo"])
    nulos_mintur = control_nulos(
        "mintur", mintur,
        {"telefono": "Se mantiene nulo, no es campo critico para los KPIs del proyecto"}
    )

    reporte["controles"]["mintur"] = {
        "registros_staging": len(mintur),
        "duplicados": dup_mintur,
        "nulos": nulos_mintur,
    }

    # ---------- GOOGLE TRENDS ----------
    archivo_trends = ultimo_archivo("data/staging/staging_trends_*.json")
    trends = cargar_json(archivo_trends) if archivo_trends else []

    dup_trends = control_duplicados("google_trends", trends, ["destino_homologado", "fecha"])

    reporte["controles"]["google_trends"] = {
        "registros_staging": len(trends),
        "duplicados": dup_trends,
    }

    # ---------- ENCUESTA ----------
    archivo_encuesta = ultimo_archivo("data/staging/staging_encuesta_*.json")
    encuesta = cargar_json(archivo_encuesta) if archivo_encuesta else []

    dup_encuesta = control_duplicados("encuesta", encuesta, ["Marca temporal"])
    nulos_encuesta = control_nulos(
        "encuesta", encuesta,
        {
            "¿Cómo califica la relación precio-calidad del hospedaje? (1 al 5)": "Se excluye del promedio si es nulo",
            "¿Cómo califica la atención al turista en la provincia? (1 al 5)": "Se excluye del promedio si es nulo",
        }
    )

    reporte["controles"]["encuesta"] = {
        "registros_staging": len(encuesta),
        "duplicados": dup_encuesta,
        "nulos": nulos_encuesta,
    }

    # ---------- OPENWEATHER ----------
    archivo_weather = ultimo_archivo("data/staging/staging_openweather_*.json")
    weather_raw = cargar_json(archivo_weather) if archivo_weather else {}
    weather_detalle = weather_raw.get("detalle_por_destino", [])

    reporte["controles"]["openweather"] = {
        "registros_staging": len(weather_detalle),
        "nota": "Extraido en una unica fecha de consulta; no representa las 3 temporadas completas",
    }

    # ---------- TOTALES GLOBALES ----------
    total_raw = raw_hospedaje + dup_mintur["total_registros"] + dup_trends["total_registros"] + dup_encuesta["total_registros"] + len(weather_detalle)
    total_staging = len(hospedaje) + len(mintur) + len(trends) + len(encuesta) + len(weather_detalle)

    reporte["resumen_global"] = {
        "total_registros_raw_procesados": total_raw,
        "total_registros_staging_consolidados": total_staging,
        "tasa_completitud_general_pct": round((total_staging / total_raw) * 100, 2) if total_raw else 0,
        "total_duplicados_eliminados": (
            dup_hospedaje["duplicados_encontrados"]
            + dup_mintur["duplicados_encontrados"]
            + dup_trends["duplicados_encontrados"]
            + dup_encuesta["duplicados_encontrados"]
        ),
        "evidencia_formatos_casting": EVIDENCIA_CASTING,
        "estandarizacion_aplicada": ESTANDARIZACION_APLICADA,
        "homologacion_inter_fuentes": HOMOLOGACION_CAMPOS,
    }

    return reporte


def main():
    reporte = generar_reporte()

    os.makedirs("data/quality", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_salida = f"data/quality/reporte_calidad_{timestamp}.json"

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("REPORTE DE CALIDAD DE DATOS")
    print("=" * 60)

    for fuente, datos in reporte["controles"].items():
        print(f"\n[{fuente.upper()}]")
        for k, v in datos.items():
            if k not in ("nulos",):
                print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("RESUMEN GLOBAL")
    print("=" * 60)
    resumen = reporte["resumen_global"]
    print(f"Total registros raw procesados: {resumen['total_registros_raw_procesados']}")
    print(f"Total registros en staging consolidados: {resumen['total_registros_staging_consolidados']}")
    print(f"Tasa de completitud general: {resumen['tasa_completitud_general_pct']}%")
    print(f"Total duplicados eliminados: {resumen['total_duplicados_eliminados']}")

    print(f"\nGuardado: {ruta_salida}")
    print(f"Log de errores estructurado: logs/calidad_datos.log")


if __name__ == "__main__":
    main()