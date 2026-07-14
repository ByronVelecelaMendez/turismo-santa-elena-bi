# Plataforma de Inteligencia de Negocios — Turismo Santa Elena

Proyecto Integrador de la asignatura Inteligencia de Negocios (UPSE, 2026-1).
Plataforma BI completa de extremo a extremo para el análisis del sector turístico
y hotelero de la provincia de Santa Elena, Ecuador, integrando 8 fuentes heterogéneas
en un Data Warehouse PostgreSQL bajo modelo Star Schema.

## Dashboard en Producción

URL pública: https://turismo-santa-elena-bi-4fpluufci3ryc9tckq5ckz.streamlit.app

Datos en vivo desde el Data Warehouse PostgreSQL alojado en Render Cloud.
No requiere instalación local para visualizar el dashboard.

---

## Equipo

| Nombre | Rol |
|---|---|
| Skay Gisell Alvarado Rodríguez | Desarrolladora |
| Peter Leonardo Villón Orrala | Desarrollador |
| Byron Andrés Velecela Méndez | Desarrollador |

Docente: Ing. Anthony Abrahan Pachay Espinoza
Facultad de Sistemas y Telecomunicaciones — Ingeniería en Software — UPSE 2026-1

---

## Resumen del Proyecto

| Indicador | Valor |
|---|---|
| Fuentes de datos integradas | 8 |
| Destinos turísticos analizados | 6 |
| Registros en fact_hospedaje | 448 |
| Total de registros en el DW | 1,840 |
| KPIs implementados | 6 vistas SQL nativas |
| Páginas del dashboard | 6 |
| Reseñas analizadas | 31,795 |
| Respuestas de encuesta propia | 111 |

### Hallazgos principales

- Brecha de precio del 177%: los visitantes perciben $38.38/noche frente a $106.18 real en plataformas digitales.
- Montañita lidera el mercado digital con 12,265 reseñas (38.6% del total provincial).
- La seguridad es la barrera sistémica más citada: 49.5% de encuestados la identifican como prioridad de mejora.
- Anomalía Punta Carnero: segundo precio más alto ($160.91/noche) con la valoración más baja (3.49/5.00).

---

## Arquitectura del Pipeline

```
Fuentes (8)          Zona Raw          Staging          Data Warehouse       Dashboard
Booking.com          JSON/CSV          PostgreSQL        fact_hospedaje       Streamlit
Airbnb           ->  inmutable     ->  staging       ->  dim_destino      ->  6 paginas
KAYAK                sin procesar      limpio y          dim_plataforma       6 KPIs
Hostelworld                            estandarizado     dim_alojamiento      Plotly
OpenWeather                                              dim_temporada        pydeck
MINTUR CSV                                               dim_fecha
Google Trends
Encuesta propia
```

### Stack tecnologico

| Capa | Tecnologia |
|---|---|
| Extraccion | Python 3.12, Playwright, requests, pytrends |
| Transformacion | pandas, SQLAlchemy |
| Almacenamiento | PostgreSQL 17 (Render Cloud) |
| Dashboard | Streamlit 1.45+, Plotly Express, pydeck |
| Despliegue | Streamlit Cloud + Render PostgreSQL |
| Control de versiones | Git / GitHub |

---

## Modelo Dimensional (Star Schema)

```
                    dim_fecha
                        |
dim_destino ──── fact_hospedaje ──── dim_plataforma
                        |
               dim_alojamiento
                        |
                  dim_temporada
```

| Tabla | Tipo | Registros | Descripcion |
|---|---|---|---|
| fact_hospedaje | Hechos | 448 | Publicaciones activas con precio, rating y resenas |
| dim_destino | Dimension | 6 | Destinos con coordenadas, tipo y canton |
| dim_plataforma | Dimension | 8 | Fuentes clasificadas por tipo de adquisicion |
| dim_alojamiento | Dimension | 279 | Alojamientos unicos de las 4 plataformas |
| dim_temporada | Dimension | 3 | Temporadas con temperatura y condicion climatica |
| dim_fecha | Dimension | 1,096 | Calendario 2024-2026 generado automaticamente |

---

## Instalacion Local

### Requisitos previos

- Python 3.12+
- PostgreSQL 17
- API Key de OpenWeather (https://openweathermap.org/api)

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/ByronVelecelaMendez/turismo-santa-elena-bi.git
cd turismo-santa-elena-bi

python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell
# source venv/bin/activate       # Linux/Mac

pip install -r requirements.txt
playwright install chromium
```

### 2. Variables de entorno

Crear un archivo `.env` en la raiz del proyecto con las credenciales locales de PostgreSQL.
Este archivo no se sube a Git (esta en `.gitignore`).

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dw_turismo_santa_elena
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
```

Para despliegue en Streamlit Cloud se utilizan `st.secrets` — ver `database/conexion.py`.

### 3. Crear la base de datos

```bash
createdb -U postgres dw_turismo_santa_elena
psql -U postgres -d dw_turismo_santa_elena -f dw_turismo_santa_elena.sql
```

### 4. Archivos de descarga manual

Colocar en `data/csv/` antes de ejecutar el pipeline:

- Catastro MINTUR: descargar desde https://datosabiertos.gob.ec, dataset de Catastro Nacional Turistico, periodos 2023-10 y 2025-02 (formato .xlsx).
- Encuesta propia: exportar desde Google Forms como CSV (Respuestas → Descargar → CSV).

---

## Ejecucion del Pipeline ETL

### Paso 1 — Extraccion (Zona Raw)

```bash
python scraping/booking_scraper.py
python scraping/airbnb_scraper.py
python scraping/kayak_scraper.py
python scraping/hostelworld_scraper.py
python scraping/openweather_api.py
python scraping/google_trends_scraper.py
```

### Paso 2 — Staging (limpieza y homologacion)

```bash
python etl/staging_hospedaje.py
python etl/procesar_catastro_mintur.py
python etl/procesar_encuesta.py
python etl/procesar_trends.py
python etl/procesar_openweather.py
```

### Paso 3 — Control de calidad (7 controles)

```bash
python etl/calidad_datos.py
```

Genera reporte en `data/quality/reporte_calidad_<timestamp>.json` y log en `logs/calidad_datos.log`.

### Paso 4 — Carga al Data Warehouse

```bash
python etl/carga_dimensiones_fijas.py
python etl/carga_dim_temporada.py
python etl/carga_dim_alojamiento.py
python etl/carga_fact_hospedaje.py
```

### Paso 5 — Ejecutar el Dashboard

```bash
cd dashboard
streamlit run app.py
```

---

## Estructura del Repositorio

```
turismo-santa-elena-bi/
├── data/
│   ├── csv/                # Archivos descargados manualmente (NO en Git)
│   ├── raw/                # Zona Raw — datos crudos inmutables (NO en Git)
│   │   ├── scraping/       # Booking, Airbnb, KAYAK, Hostelworld
│   │   ├── api/            # OpenWeather, Google Trends
│   │   ├── archivos/       # MINTUR
│   │   └── fuente_propia/  # Encuesta
│   ├── staging/            # Zona Staging — datos limpios (NO en Git)
│   └── quality/            # Reportes de calidad (NO en Git)
├── scraping/               # Scripts de extraccion (Playwright, requests, pytrends)
├── etl/                    # Scripts de staging, calidad y carga al DW
│   └── calidad_datos.py    # Framework de calidad con 7 controles documentados
├── database/
│   └── conexion.py         # SQLAlchemy — soporta .env local y st.secrets cloud
├── dashboard/
│   ├── app.py              # Entrada principal (st.navigation)
│   ├── common.py           # Modulo compartido: CSS, KPIs, navegacion, graficos
│   ├── pages/
│   │   ├── 0_inicio.py
│   │   ├── 1_resumen_general.py
│   │   ├── 2_analisis_precios.py
│   │   ├── 3_valoraciones_plataforma.py
│   │   ├── 4_encuesta_propia.py
│   │   └── 5_datos_fuentes.py
│   └── assets/             # Logo UPSE y banner
├── logs/                   # Logs del pipeline (NO en Git)
├── dw_turismo_santa_elena.sql  # Schema completo del Data Warehouse
├── requirements.txt
└── .env                    # Variables de entorno (NO en Git)
```

---

## Limitaciones Documentadas

- Cobertura temporal unica: todas las extracciones corresponden a temporada baja (junio 2026). Los KPIs de variacion inter-temporal retornan NULL hasta que se programen extracciones en temporada alta y media.
- Hostelworld: sin listados para Punta Carnero y La Libertad (HTTP 404). Cobertura efectiva: 4 de 6 destinos.
- Campos sin poblar: `categoria_estrellas` y `capacidad` en dim_alojamiento presentan 100% de valores NULL. Ninguna plataforma expone esta informacion de forma sistematica en su interfaz publica.
- TripAdvisor y Hotels.com: sustituidas por KAYAK y Hostelworld por restricciones anti-bot. Justificacion completa en el Entregable 2.

---

## Entregables del Proyecto

| Entregable | Descripcion | Estado |
|---|---|---|
| E1 | Definicion del problema y arquitectura conceptual | Completado |
| E2 | Arquitectura de datos y modelo analitico | Completado |
| E3 | Pipeline ETL y framework de calidad | Completado |
| E4 | Data Warehouse y analitica SQL | Completado |
| E5 | Dashboard funcional y reporte cientifico | Completado |

---

Proyecto academico — Universidad Estatal Peninsula de Santa Elena (UPSE) 2026-1.