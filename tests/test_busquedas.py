"""Pruebas de busquedas.py.   Ejecutar:  pytest -v"""
import random
import unittest
from pathlib import Path

import busquedas as bq
from arbol import Arbol
from persona import Persona


RUTA = str(Path(__file__).resolve().parent.parent / "data" / "familia.json")


class Base(unittest.TestCase):
    def setUp(self):
        self.arbol = Arbol.cargar_desde_json(RUTA)
        self.personas = list(self.arbol.personas.values())

    def ids(self, personas):
        return [p.id for p in personas]


class TestFechas(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(bq.partes_fecha("1981-07-24"), (1981, 7, 24))
        self.assertEqual(bq.partes_fecha("2015"), (2015, 0, 0))
        self.assertEqual(bq.partes_fecha("1981-07"), (1981, 7, 0))

    def test_invalidas(self):
        for f in (None, "", "hola", "1981-13-01", "1981-02-30", "1-2-3-4"):
            self.assertIsNone(bq.partes_fecha(f), f)


class TestBurbuja(Base):
    def test_igual_que_sorted(self):
        for _ in range(20):
            datos = [random.randint(-50, 50) for _ in range(random.randint(0, 30))]
            self.assertEqual(bq.ordenamiento_burbuja(datos), sorted(datos))
            self.assertEqual(bq.ordenamiento_burbuja(datos, descendente=True), sorted(datos, reverse=True))

    def test_no_modifica_original(self):
        datos = [3, 1, 2]
        bq.ordenamiento_burbuja(datos)
        self.assertEqual(datos, [3, 1, 2])

    def test_estable(self):
        datos = [(1, "a"), (0, "b"), (1, "c"), (0, "d")]
        r = bq.ordenamiento_burbuja(datos, clave=lambda x: x[0])
        self.assertEqual(r, [(0, "b"), (0, "d"), (1, "a"), (1, "c")])

    def test_mejor_caso_una_pasada(self):
        stats = {}
        bq.ordenamiento_burbuja([1, 2, 3, 4, 5], estadisticas=stats)
        self.assertEqual((stats["pasadas"], stats["intercambios"], stats["comparaciones"]), (1, 0, 4))

    def test_historial(self):
        hist = []
        bq.ordenamiento_burbuja([3, 2, 1], historial=hist)
        self.assertEqual(hist, [[3, 2, 1], [2, 1, 3], [1, 2, 3]])

    def test_ordenar_por_fecha(self):
        r = bq.ordenar_por_fecha_nacimiento(self.personas)
        self.assertEqual(self.ids(r[:3]), ["nayib", "karim", "yusef"])
        # sin fecha al final y en orden alfabético
        self.assertEqual(self.ids(r[3:]), ["armando", "gabriela", "ibrajim", "olga", "yamil"])

    def test_descendente_sin_fecha_sigue_al_final(self):
        r = bq.ordenar_por_fecha_nacimiento(self.personas, descendente=True)
        self.assertEqual(self.ids(r[:3]), ["yusef", "karim", "nayib"])
        self.assertTrue(all(p.fecha_nacimiento is None for p in r[3:]))

    def test_fecha_solo_anio(self):
        a = Persona("a", "A", fecha_nacimiento="1990")
        b = Persona("b", "B", fecha_nacimiento="1985-12-31")
        self.assertEqual(self.ids(bq.ordenar_por_fecha_nacimiento([a, b])), ["b", "a"])

    def test_ordenar_hijos_en_lugar(self):
        armando = self.arbol.buscar_por_id("armando")
        lista_original = armando.hijos
        bq.ordenar_hijos(armando)
        self.assertIs(armando.hijos, lista_original)          # misma lista
        self.assertEqual(self.ids(armando.hijos[:3]), ["nayib", "karim", "yusef"])


class TestBinaria(Base):
    def test_encuentra_a_todos(self):
        indice = bq.IndicePorId(self.personas)
        for p in self.personas:
            self.assertIs(indice.buscar(p.id), p)

    def test_mayusculas_y_espacios(self):
        indice = bq.IndicePorId(self.personas)
        self.assertEqual(indice.buscar("  KARIM ").id, "karim")

    def test_inexistente(self):
        indice = bq.IndicePorId(self.personas)
        self.assertIsNone(indice.buscar("no_existe"))
        self.assertNotIn("no_existe", indice)
        self.assertIsNone(bq.busqueda_binaria_por_id([], "nayib"))

    def test_pocos_pasos(self):
        for p in self.personas:
            pasos = []
            bq.buscar_por_id(self.arbol, p.id, pasos)
            self.assertLessEqual(len(pasos), 4)              # floor(log2(8)) + 1
            self.assertEqual(pasos[-1]["decision"], "encontrado")

    def test_lista_grande(self):
        gente = [Persona(f"p{i:04d}", f"P {i}") for i in range(1000)]
        random.shuffle(gente)
        ordenadas = bq.ordenar_por_id(gente)
        pasos = []
        self.assertEqual(bq.busqueda_binaria_por_id(ordenadas, "p0777", pasos).id, "p0777")
        self.assertLessEqual(len(pasos), 10)

    def test_nacidos_entre(self):
        self.assertEqual(self.ids(bq.buscar_nacidos_entre(self.personas, 1985, 1990)), ["karim", "yusef"])
        self.assertEqual(self.ids(bq.buscar_nacidos_entre(self.personas, 1990, 1980)), ["nayib", "karim", "yusef"])
        self.assertEqual(bq.buscar_nacidos_entre(self.personas, 2000, 2010), [])


class TestSecuencial(Base):
    def test_sin_tildes_ni_mayusculas(self):
        self.assertEqual(self.ids(bq.buscar_por_nombre(self.personas, "NÁYIB")), ["nayib"])

    def test_varias_palabras_cualquier_orden(self):
        self.assertEqual(self.ids(bq.buscar_por_nombre(self.personas, "bukele nayib")), ["nayib"])

    def test_relevancia(self):
        # 'yusef' coincide exacto con Yusef; nadie más -> 1 resultado
        self.assertEqual(self.ids(bq.buscar_por_nombre(self.personas, "yusef")), ["yusef"])
        # 'ar' es inicio de "Armando" (Armando y Nayib Armando) y está en medio de "Karim":
        # los que empiezan con 'ar' deben salir antes que Karim
        r = self.ids(bq.buscar_por_nombre(self.personas, "ar"))
        self.assertEqual(set(r[:2]), {"armando", "nayib"})
        self.assertGreater(r.index("karim"), 1)

    def test_apellido(self):
        r = set(self.ids(bq.buscar_por_apellido(self.personas, "ortez")))
        self.assertEqual(r, {"nayib", "olga", "karim", "yusef", "ibrajim"})

    def test_apellido_no_confunde_segundo_nombre(self):
        self.assertEqual(bq.buscar_por_apellido(self.personas, "armando"), [])

    def test_apellido_de_casada(self):
        self.assertEqual(self.ids(bq.buscar_por_apellido(self.personas, "rodriguez")), ["gabriela"])

    def test_apellidos_de(self):
        self.assertEqual(bq.apellidos_de("Juan Pérez de la Cruz"), "Pérez de la Cruz")
        self.assertEqual(bq.apellidos_de("Armando Bukele Kattan"), "Bukele Kattan")
        self.assertEqual(bq.apellidos_de("Olga Ortez"), "Ortez")
        self.assertEqual(bq.apellidos_de("Madonna"), "")

    def test_vacio_y_parametro_invalido(self):
        self.assertEqual(bq.buscar_por_nombre(self.personas, "   "), [])
        with self.assertRaises(ValueError):
            bq.busqueda_secuencial(self.personas, "x", por="edad")

    def test_revisa_todas(self):
        stats = {}
        bq.busqueda_secuencial(self.personas, "bukele", estadisticas=stats)
        self.assertEqual(stats["revisadas"], len(self.personas))


if __name__ == "__main__":
    unittest.main()
