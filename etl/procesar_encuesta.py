import os
import json
import pandas as pd
from datetime import datetime

def homologar_destino(texto):
    """Asegura que los destinos de la encuesta coincidan exactamente con tus hoteles."""
    if not texto: 
        return "sin_clasificar"
    t = str(texto).strip().lower()
    if "salinas" in t: return "salinas"
    if "monta" in t or "montañita" in t: return "montanita"
    if "ayangue" in t: return "ayangue"
    if "libertad" in t: return "la_libertad"
    if "manglar" in t: return "manglaralto"
    if "carnero" in t: return "punta_carnero"
    return "sin_clasificar"

def procesar_encuesta_staging():
    ruta_csv = "data/csv/Experiencia_Turística_en_la_Provincia_de_Santa_Elena.csv"
    ruta_output = "data/staging"
    
    if not os.path.exists(ruta_csv):
        print(f"[-] Error: No se encontró el CSV en: {ruta_csv}")
        return

    print(f"[*] Leyendo y limpiando la encuesta: {ruta_csv}")
    
    # Leer el CSV original
    df = pd.read_csv(ruta_csv, encoding="utf-8")
    
    # Buscamos la columna donde el turista puso qué lugar visitó
    columna_destino = [col for col in df.columns if 'destino' in col.lower() or 'lugar' in col.lower()]
    
    if columna_destino:
        col_dest = columna_destino[0]
        # Creamos una columna limpia con destinos homologados
        df['destino_homologado'] = df[col_dest].apply(homologar_destino)
    else:
        df['destino_homologado'] = "sin_clasificar"

    # Convertir a formato JSON de staging
    registros_limpios = df.to_dict(orient="records")
    
    # Guardar en data/staging con la fecha de hoy
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_final = os.path.join(ruta_output, f"staging_encuesta_{timestamp}.json")
    
    with open(ruta_final, "w", encoding="utf-8") as f:
        json.dump(registros_limpios, f, ensure_ascii=False, indent=4)
        
    print(f"[+] ÉXITO: Encuesta procesada y guardada en: {ruta_final}")
    print(f"[*] Respuestas totales procesadas: {len(registros_limpios)}")

if __name__ == "__main__":
    procesar_encuesta_staging()