import sys
import os
from sqlalchemy import inspect

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.conexion import get_engine

engine = get_engine()
inspector = inspect(engine)

tablas = inspector.get_table_names()
vistas = inspector.get_view_names()

print("TABLAS en el Data Warehouse:")
for t in sorted(tablas):
    print(" -", t)

print()
print("VISTAS (KPIs) en el Data Warehouse:")
for v in sorted(vistas):
    print(" -", v)

print()
if any("encuesta" in t.lower() for t in tablas):
    print("Ya existe una tabla de encuesta en el DW.")
else:
    print("NO existe tabla de encuesta en el DW todavia.")
