import sys, os
from sqlalchemy import text
sys.path.append(os.path.abspath("."))
from database.conexion import get_engine

engine = get_engine()
with engine.connect() as conn:
    resultado = conn.execute(text("SELECT COUNT(*) FROM fact_hospedaje"))
    print("Filas actuales en fact_hospedaje:", resultado.scalar())
