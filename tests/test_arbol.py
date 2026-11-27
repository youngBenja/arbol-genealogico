from pathlib import Path
from arbol import Arbol

RUTA = str(Path(__file__).resolve().parent.parent / "data" / "familia.json")


def test_generaciones():
    gens = Arbol.cargar_desde_json(RUTA).listar_por_generaciones()
    assert {p.id for p in gens[0]} == {"armando", "olga"}
    assert {p.id for p in gens[1]} == {
        "nayib", "gabriela", "karim", "yusef", "ibrajim", "yamil"
    }


def test_hermanos_de_nayib():
    a = Arbol.cargar_desde_json(RUTA)
    ids = {p.id for p in a.hermanos_de(a.buscar_por_id("nayib"))}
    assert ids == {"karim", "yusef", "ibrajim", "yamil"}


def test_buscar_sin_tildes():
    a = Arbol.cargar_desde_json(RUTA)
    assert a.buscar_por_nombre("rodriguez")


def test_generaciones_coinciden_con_visualizacion():
    import visualizacion as viz
    a = Arbol.cargar_desde_json(RUTA)
    gv = viz.calcular_generaciones(a)
    for g, personas in a.listar_por_generaciones().items():
        for p in personas:
            assert gv[p.id] == g
