from persona import Persona


def test_constructor_como_lo_usa_arbol():
    p = Persona(id_persona="a", nombre="A", parentesco="x", fecha_nacimiento="1990",
                fecha_fallecimiento=None, descripcion="", foto=None, fuentes=["k"])
    assert p.id == "a" and p.fuentes == ["k"] and p.hijos == []


def test_conyuge_es_reciproco_y_no_se_cuelga():
    a, b = Persona("a", "A"), Persona("b", "B")
    a.asignar_conyuge(b)   # si se cuelga aquí, hay recursión infinita
    assert a.conyuge is b and b.conyuge is a


def test_agregar_hijo():
    a, h = Persona("a", "A"), Persona("h", "H")
    a.agregar_hijo(h)
    assert a.hijos == [h]
