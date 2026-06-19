import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Destinos de Santa Elena con coordenadas
DESTINOS = {
    "Montanita":     {"lat": -1.8312, "lon": -80.7561},
    "Salinas":       {"lat": -2.2171, "lon": -80.9596},
    "Ayangue":       {"lat": -1.9711, "lon": -80.7447},
    "Punta Carnero": {"lat": -2.2614, "lon": -80.9089},
    "Manglaralto":   {"lat": -1.8333, "lon": -80.7500},
    "La Libertad":   {"lat": -2.2333, "lon": -80.9000},
}