import sys, os
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.conexion import get_engine

engine = get_engine()
df = pd.read_sql("SELECT * FROM fact_encuesta", engine)

col = "¿Cuánto paga por noche de hospedaje en Santa Elena?"
print("Valores unicos de precio:")
print(df[col].value_counts())

col2 = "¿Cómo califica la relación precio-calidad del hospedaje? (1 al 5)"
print()
print("Valores unicos de calidad:")
print(df[col2].value_counts())

col3 = "¿Recomendaría visitar Santa Elena a otras personas?"
print()
print("Valores unicos de recomendacion:")
print(df[col3].value_counts())
