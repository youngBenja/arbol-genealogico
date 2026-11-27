import json
import re
from pathlib import Path

RUTA_JSON = Path(__file__).resolve().parent.parent / "data" / "familia.json"
FECHA_OK = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")   # "2015", "1981-07" o "1981-07-24"


def cargar():
    return json.loads(RUTA_JSON.read_text(encoding="utf-8"))


def test_json_existe_y_es_valido():
    assert RUTA_JSON.exists(), "No existe data/familia.json"
    datos = cargar()
    assert datos["personas"] and "raiz" in datos and "fuentes" in datos


def test_raiz_existe():
    datos = cargar()
    assert datos["raiz"] in {p["id"] for p in datos["personas"]}


def test_ids_unicos():
    ids = [p["id"] for p in cargar()["personas"]]
    assert len(ids) == len(set(ids)), "Hay ids repetidos"


def test_campos_obligatorios():
    obligatorios = {"id", "nombre", "parentesco", "fuentes"}
    for p in cargar()["personas"]:
        faltan = obligatorios - p.keys()
        assert not faltan, f"{p.get('nombre', '?')} le faltan: {faltan}"


def test_fuentes_existen():
    datos = cargar()
    claves = set(datos["fuentes"])
    for p in datos["personas"]:
        assert p["fuentes"], f"{p['id']} no tiene fuentes"
        for f in p["fuentes"]:
            assert f in claves, f"{p['id']} usa fuente inexistente: {f}"


def test_formato_fechas():
    for p in cargar()["personas"]:
        for campo in ("fecha_nacimiento", "fecha_fallecimiento"):
            v = p.get(campo)
            if v is not None:
                assert FECHA_OK.match(v), f"{p['id']}.{campo} mal: {v}"


def test_relaciones_no_rotas():
    datos = cargar()
    ids = {p["id"] for p in datos["personas"]}
    for p in datos["personas"]:
        for padre in p.get("padres", []):
            assert padre in ids, f"{p['id']} apunta a padre inexistente: {padre}"
        if p.get("conyuge"):
            assert p["conyuge"] in ids, f"{p['id']} tiene cónyuge inexistente"


def test_conyuges_reciprocos():
    por_id = {p["id"]: p for p in cargar()["personas"]}
    for p in por_id.values():
        c = p.get("conyuge")
        if c:
            assert por_id[c].get("conyuge") == p["id"], f"{p['id']} y {c} no son mutuos"


def test_fotos_existen():
    for p in cargar()["personas"]:
        if p.get("foto"):
            assert Path(p["foto"]).exists(), f"Falta la foto de {p['nombre']}"
