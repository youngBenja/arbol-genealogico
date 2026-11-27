from collections import deque
import json
import unicodedata
from persona import Persona


def _normalizar(texto: str) -> str:
    # le quita las tildes y pasa a minúsculas: "Rodríguez" == "rodriguez"
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


class Arbol:
    def __init__(self, raiz: Persona | None = None):
        self.raiz: Persona | None = raiz
        self.personas: dict[str, Persona] = {}
        self.catalogo_fuentes: dict[str, str] = {}
        # guardamos las relaciones aquí también, así no dependemos de cómo
        # esté hecha la clase Persona
        self._padres: dict[str, list[str]] = {}
        self._conyuges: dict[str, str] = {}
        if raiz is not None:
            self.personas[raiz.id] = raiz

    def agregar_persona(self, persona: Persona, es_raiz: bool = False) -> None:
        if persona.id in self.personas:
            raise ValueError(f"Ya existe una persona con id '{persona.id}'")
        self.personas[persona.id] = persona
        if self.raiz is None or es_raiz:
            self.raiz = persona

    def vincular_padre_hijo(self, id_padre: str, id_hijo: str) -> bool:
        padre = self.buscar_por_id(id_padre)
        hijo = self.buscar_por_id(id_hijo)
        if not padre or not hijo:
            return False
        if hijo not in padre.hijos:  # evita duplicados si se llama dos veces
            padre.agregar_hijo(hijo)
        lista = self._padres.setdefault(id_hijo, [])
        if id_padre not in lista:
            lista.append(id_padre)
        return True

    def vincular_conyuges(self, id_persona_1: str, id_persona_2: str) -> bool:
        p1 = self.buscar_por_id(id_persona_1)
        p2 = self.buscar_por_id(id_persona_2)
        if not p1 or not p2:
            return False
        p1.asignar_conyuge(p2)
        self._conyuges[id_persona_1] = id_persona_2
        self._conyuges[id_persona_2] = id_persona_1
        return True

    def buscar_por_id(self, id_persona: str) -> Persona | None:
        return self.personas.get(id_persona)

    def buscar_por_nombre(self, nombre: str) -> list[Persona]:
        termino = _normalizar(nombre)
        return [
            p for p in self.personas.values()
            if termino in _normalizar(p.nombre)
        ]

    # ---------- familiares ----------
    def padres_de(self, persona: Persona) -> list[Persona]:
        return [self.personas[i] for i in self._padres.get(persona.id, [])
                if i in self.personas]

    def hijos_de(self, persona: Persona) -> list[Persona]:
        return list(persona.hijos)

    def hermanos_de(self, persona: Persona) -> list[Persona]:
        # hermanos = hijos de mis padres, sin contarme a mí ni repetir
        ids = {}
        for padre in self.padres_de(persona):
            for h in padre.hijos:
                if h.id != persona.id:
                    ids[h.id] = h
        return list(ids.values())

    # ---------- recorridos ----------
    def recorrido_preorden(self, inicio: Persona | None = None, visitados: set[str] | None = None) -> list[Persona]:
        actual = inicio if inicio is not None else self.raiz
        if actual is None:
            return []
        if visitados is None:
            visitados = set()
        if actual.id in visitados:
            return []

        visitados.add(actual.id)
        resultado = [actual]
        for hijo in actual.hijos:
            resultado.extend(self.recorrido_preorden(hijo, visitados))
        return resultado

    def recorrido_postorden(self, inicio: Persona | None = None, visitados: set[str] | None = None) -> list[Persona]:
        actual = inicio if inicio is not None else self.raiz
        if actual is None:
            return []
        if visitados is None:
            visitados = set()
        if actual.id in visitados:
            return []

        visitados.add(actual.id)
        resultado: list[Persona] = []
        for hijo in actual.hijos:
            resultado.extend(self.recorrido_postorden(hijo, visitados))
        resultado.append(actual)
        return resultado

    def recorrido_por_niveles(self) -> list[tuple[int, Persona]]:
        # OJO: solo baja por descendientes de la raíz
        if self.raiz is None:
            return []

        visitados: set[str] = {self.raiz.id}
        cola: deque[tuple[Persona, int]] = deque([(self.raiz, 0)])
        recorrido: list[tuple[int, Persona]] = []

        while cola:
            actual, nivel = cola.popleft()
            recorrido.append((nivel, actual))
            for hijo in actual.hijos:
                if hijo.id not in visitados:
                    visitados.add(hijo.id)
                    cola.append((hijo, nivel + 1))

        return recorrido

    # ---------- generaciones ----------
    def calcular_generaciones(self) -> dict[str, int]:
        """Nivel relativo a la raíz: raíz = 0, padres = -1, hijos = +1,
        cónyuge = mismo nivel. Solo incluye a quienes se conectan con la raíz."""
        if self.raiz is None:
            return {}
        nivel = {self.raiz.id: 0}
        cola = deque([self.raiz.id])
        while cola:
            actual = cola.popleft()
            n = nivel[actual]
            vecinos = [(p, n - 1) for p in self._padres.get(actual, [])]
            vecinos += [(h.id, n + 1) for h in self.personas[actual].hijos]
            if actual in self._conyuges:
                vecinos.append((self._conyuges[actual], n))
            for id_vecino, n_vecino in vecinos:
                if id_vecino in self.personas and id_vecino not in nivel:
                    nivel[id_vecino] = n_vecino
                    cola.append(id_vecino)
        return nivel

    def listar_por_generaciones(self) -> dict[int, list[Persona]]:
        """Generación 0 = la más antigua (para mostrar 'Generación 1, 2...' en la interfaz)."""
        niveles = self.calcular_generaciones()
        if not niveles:
            return {}
        minimo = min(niveles.values())
        generaciones: dict[int, list[Persona]] = {}
        for id_persona, n in niveles.items():
            generaciones.setdefault(n - minimo, []).append(self.personas[id_persona])
        return dict(sorted(generaciones.items()))

    def urls_fuentes_de(self, persona: Persona) -> list[str]:
        return [
            self.catalogo_fuentes.get(clave, clave)
            for clave in persona.fuentes
        ]

    # ---------- carga ----------
    @classmethod
    def cargar_desde_json(cls, ruta_json: str, id_raiz_preferida: str | None = None) -> "Arbol":
        with open(ruta_json, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        arbol = cls()
        arbol.catalogo_fuentes = datos.get("fuentes", {})
        lista_personas = datos.get("personas", [])

        # 1. Crear personas (si hay ids repetidos, agregar_persona avisa)
        for item in lista_personas:
            persona = Persona(
                id_persona=str(item["id"]),
                nombre=item.get("nombre", "Sin nombre"),
                parentesco=item.get("parentesco", ""),
                fecha_nacimiento=item.get("fecha_nacimiento"),
                fecha_fallecimiento=item.get("fecha_fallecimiento"),
                descripcion=item.get("descripcion", ""),
                foto=item.get("foto"),
                fuentes=item.get("fuentes", []),
            )
            arbol.agregar_persona(persona)

        # 2. Vincular padres -> hijos y cónyuges
        for item in lista_personas:
            id_hijo = str(item["id"])
            for id_padre in item.get("padres", []):
                arbol.vincular_padre_hijo(str(id_padre), id_hijo)

            id_conyuge = item.get("conyuge")
            if id_conyuge:
                arbol.vincular_conyuges(id_hijo, str(id_conyuge))

        # 3. Definir raíz
        id_objetivo = id_raiz_preferida or datos.get("raiz")
        if id_objetivo and arbol.buscar_por_id(str(id_objetivo)):
            arbol.raiz = arbol.buscar_por_id(str(id_objetivo))
        elif arbol.personas:
            arbol.raiz = next(iter(arbol.personas.values()))

        return arbol
