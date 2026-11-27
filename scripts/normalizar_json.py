"""Convierte familia_del_presi.json (del rol 1) en data/familia.json (formato final).
Correr desde la raíz del proyecto:  python scripts/normalizar_json.py"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "familia_del_presi.json"
DESTINO = RAIZ / "data" / "familia.json"

# parentesco limpio (visualizacion.py y app.py ya cortan en " (")
PARENTESCO = {
    "nayib": "Presidente de El Salvador",
    "yusef": "Hermano",
    "ibrajim": "Hermano",
    "yamil": "Medio hermano",
}

datos = json.loads(ORIGEN.read_text(encoding="utf-8"))

# URL con espacio -> %20
for clave, url in datos["fuentes"].items():
    datos["fuentes"][clave] = url.replace(" ", "%20")

for p in datos["personas"]:
    if p["id"] in PARENTESCO:
        p["parentesco"] = PARENTESCO[p["id"]]
    # lo del mellizo pasa a la descripción (ibrajim ya lo trae)
    if p["id"] == "yusef" and not p["descripcion"].startswith("Mellizo"):
        p["descripcion"] = "Mellizo de Ibrajim. " + p["descripcion"]

DESTINO.parent.mkdir(exist_ok=True)
DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
print("Listo:", DESTINO)
