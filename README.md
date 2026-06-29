# Plataforma de Inteligencia de Negocios — Turismo Santa Elena

Proyecto académico de la asignatura Inteligencia de Negocios (UPSE, 2026-1).
Integra 8 fuentes heterogéneas de datos turísticos de la provincia de Santa
Elena, Ecuador, mediante un pipeline ETL en Python con Data Warehouse en
PostgreSQL bajo modelo Star Schema.

## Equipo

- Skay Gisell Alvarado Rodríguez
- Peter Leonardo Villón Orrala
- Byron Andrés Velecela Méndez

## Requisitos previos

- Python 3.12+
- PostgreSQL 17
- Cuenta gratuita de OpenWeather API (https://openweathermap.org/api)

## 1. Instalación del entorno

```bash
# Clonar el repositorio
git clone https://github.com/ByronVelecelaMendez/turismo-santa-elena-bi.git
cd turismo-santa-elena-bi

# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell

# Instalar dependencias
pip install -r requirements.txt

# Instalar navegador para Playwright (scraping)
playwright install chromium
```

## 2. Configuración de variables de entorno

Crea un archivo `.env` en la raíz del proyecto con tus credenciales locales
de PostgreSQL (este archivo NO se sube a Git, está en `.gitignore`):

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dw_turismo_santa_elena
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
```

También necesitas tu propia API Key de OpenWeather. Colócala directamente
en `scraping/openweather_api.py`, variable `API_KEY`.

## 3. Crear la base de datos

```bash
createdb -U postgres dw_turismo_santa_elena
psql -U postgres -d dw_turismo_santa_elena -f dw_turismo_santa_elena.sql
```

## 4. Descargar manualmente los archivos de fuente externa

Estos 2 tipos de fuente requieren descarga manual (no automatizable por
scraping/API), y deben colocarse en `data/csv/` antes de correr el pipeline:

- **Catastro MINTUR**: descargar desde el portal de Datos Abiertos de
  Ecuador (https://datosabiertos.gob.ec), dataset de Catastro Nacional
  Turístico, periodos 2023-10 y 2025-02 (formato .xlsx).
- **Encuesta propia**: exportar las respuestas del Google Form vinculado
  como CSV (Respuestas → ícono de Sheets → Archivo → Descargar → CSV).

## 5. Ejecutar el pipeline completo, en orden

### 5.1 Extracción (Zona Raw)

```bash
python scraping/booking_scraper.py
python scraping/airbnb_scraper.py
python scraping/kayak_scraper.py
python scraping/hostelworld_scraper.py
python scraping/openweather_api.py
python scraping/google_trends_scraper.py
```

(MINTUR y Encuesta no tienen scraper independiente: su extracción y
staging ocurren en el mismo script, ver paso 5.2)

### 5.2 Staging (limpieza, homologación, deduplicación)

```bash
python etl/staging_hospedaje.py        # Booking + Airbnb + KAYAK + Hostelworld
python etl/procesar_catastro_mintur.py # MINTUR (lee data/csv/, genera raw + staging)
python etl/procesar_encuesta.py        # Encuesta (lee data/csv/, genera raw + staging)
python etl/procesar_trends.py          # Google Trends
python etl/procesar_openweather.py     # OpenWeather
```

### 5.3 Control de calidad

```bash
python etl/calidad_datos.py
```

Genera `data/quality/reporte_calidad_<timestamp>.json` con los 7 controles
de calidad (duplicados, nulos, formatos, estandarización, homologación
inter-fuentes, log de errores y métricas consolidadas), y un log
estructurado en `logs/calidad_datos.log`.

### 5.4 Carga al Data Warehouse

```bash
python etl/carga_dimensiones_fijas.py  # DIM_PLATAFORMA + DIM_DESTINO
```

(Resto de la carga al DW en desarrollo — Entregable 4)

## Estructura del repositorio

turismo-santa-elena-bi/

├── data/

│   ├── csv/              # Archivos descargados manualmente (NO en Git)

│   ├── raw/               # Zona Raw - datos crudos inmutables (NO en Git)

│   │   ├── scraping/       # Booking, Airbnb, KAYAK, Hostelworld

│   │   ├── api/            # OpenWeather, Google Trends

│   │   ├── archivos/       # MINTUR

│   │   └── fuente_propia/  # Encuesta

│   ├── staging/           # Zona Staging - datos limpios (NO en Git)

│   └── quality/            # Reportes de calidad (NO en Git)

├── scraping/               # Scripts de extracción (Playwright/requests/pytrends)

├── etl/                    # Scripts de staging, calidad y carga al DW

├── database/                # Conexión a PostgreSQL (SQLAlchemy)

├── logs/                   # Logs estructurados del pipeline (NO en Git)

├── dw_turismo_santa_elena.sql  # Schema del Data Warehouse (Star Schema)

├── requirements.txt

└── .env                     # Variables de entorno (NO en Git)

## Notas sobre cobertura de datos

- **Hostelworld** no tiene listados propios para Punta Carnero y La
  Libertad (verificado: HTTP 404). Cobertura: 4 de 6 destinos.
- **OpenWeather** se extrajo en una única fecha de consulta (22 de junio
  de 2026); representa solo temporada baja, no las 3 temporadas completas.
- **TripAdvisor y Hotels.com** (fuentes originalmente propuestas en E1)
  fueron sustituidas por **KAYAK** y **Hostelworld** por restricciones
  técnicas de acceso (CAPTCHA y renderizado JS asíncrono respectivamente).
  Justificación completa en Anexo B del Entregable 2.