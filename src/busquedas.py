"""Integrante 4 – Búsqueda y ordenamiento.

Algoritmos implementados a mano (sin sorted(), list.sort() ni bisect):

  * Ordenamiento burbuja
      - ordenar_por_fecha_nacimiento(): del mayor al menor (o al revés).
      - ordenar_hijos(): los hijos de una persona por nacimiento.
      - Puede guardar el estado de la lista después de cada pasada
        para mostrar el algoritmo "paso a paso".

  * Búsqueda binaria
      - IndicePorId: ordena UNA vez por id (burbuja) y luego busca en O(log n).
      - buscar_nacidos_entre(): dos búsquedas binarias (límite inferior y
        superior) sobre la lista ordenada por fecha.

  * Búsqueda secuencial
      - Por nombre completo o por apellidos, sin importar tildes/mayúsculas.
      - Acepta varias palabras en cualquier orden ("bukele nayib").
      - Ordena los resultados por relevancia (con burbuja).

Todas las funciones aceptan un dict opcional `estadisticas` que se llena con
contadores (comparaciones, intercambios, pasos...) para la presentación.
"""
from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any, Callable, Iterable, TYPE_CHECKING

if TYPE_CHECKING:  # solo para anotaciones; evita importaciones circulares
    from arbol import Arbol
    from persona import Persona

__all__ = [
    "normalizar", "partes_fecha", "anio_de", "clave_fecha",
    "ordenamiento_burbuja", "ordenar_por_fecha_nacimiento", "ordenar_hijos",
    "ordenar_hijos_de_todos", "ordenar_por_id",
    "busqueda_binaria_por_id", "IndicePorId", "buscar_por_id", "buscar_nacidos_entre",
    "apellidos_de", "busqueda_secuencial", "buscar_por_nombre", "buscar_por_apellido",
]

SIN_FECHA = (1, 0, 0, 0)     # clave que manda a las personas sin fecha al final


# ===========================================================================
# Utilidades
# ===========================================================================
def normalizar(texto: Any) -> str:
    """Minúsculas, sin tildes y sin espacios extra: '  Rodríguez ' -> 'rodriguez'."""
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def partes_fecha(fecha: str | None) -> tuple[int, int, int] | None:
    """Convierte la fecha del JSON a (año, mes, día).

    '1981-07-24' -> (1981, 7, 24)
    '2015'       -> (2015, 0, 0)     (solo se conoce el año)
    '1981-07'    -> (1981, 7, 0)
    None, ''     -> None
    '1981-13-40' -> None             (fecha imposible)
    """
    if not fecha:
        return None
    try:
        piezas = [int(x) for x in str(fecha).strip().split("-")]
    except ValueError:
        return None
    if not 1 <= len(piezas) <= 3:
        return None
    while len(piezas) < 3:
        piezas.append(0)
    a, m, d = piezas
    try:
        if m and d:
            date(a, m, d)              # valida día/mes reales (ej. 30 de febrero)
        elif m and not 1 <= m <= 12:
            return None
    except ValueError:
        return None
    return a, m, d


def anio_de(persona: "Persona") -> int | None:
    f = partes_fecha(persona.fecha_nacimiento)
    return f[0] if f else None


def clave_fecha(persona: "Persona", descendente: bool = False) -> tuple:
    """Clave para ordenar por nacimiento.

    - Las personas sin fecha van SIEMPRE al final (aunque el orden sea descendente).
    - Si dos personas tienen la misma fecha (o ninguna), se desempata por nombre,
      así el resultado es siempre el mismo.
    """
    f = partes_fecha(persona.fecha_nacimiento)
    nombre = normalizar(persona.nombre)
    if f is None:
        return SIN_FECHA + (nombre,)
    a, m, d = f
    if descendente:
        a, m, d = -a, -m, -d
    return (0, a, m, d, nombre)


def _sumar(estadisticas: dict | None, **valores: int) -> None:
    if estadisticas is not None:
        for k, v in valores.items():
            estadisticas[k] = estadisticas.get(k, 0) + v


# ===========================================================================
# Ordenamiento burbuja
# ===========================================================================
def ordenamiento_burbuja(elementos: Iterable, clave: Callable[[Any], Any] = lambda x: x,
                         descendente: bool = False, estadisticas: dict | None = None,
                         historial: list | None = None) -> list:
    """Burbuja optimizada.

    * Cada pasada deja el mayor elemento restante en su lugar final, por eso
      el ciclo interno recorre un elemento menos cada vez.
    * Si una pasada no hace intercambios, la lista ya está ordenada y se corta
      (mejor caso O(n), peor caso O(n²)).
    * Es estable: elementos con la misma clave conservan su orden original.
    * Devuelve una lista NUEVA; la original no se modifica.

    historial: si se pasa una lista, se le agrega una copia del estado
               después de cada pasada (para mostrarlo paso a paso).
    """
    lista = list(elementos)
    claves = [clave(x) for x in lista]          # se calcula la clave una sola vez
    n = len(lista)
    comparaciones = intercambios = pasadas = 0

    if historial is not None:
        historial.append(list(lista))

    for i in range(n - 1):
        pasadas += 1
        hubo_intercambio = False
        for j in range(n - 1 - i):
            comparaciones += 1
            fuera_de_orden = claves[j] < claves[j + 1] if descendente else claves[j] > claves[j + 1]
            if fuera_de_orden:
                lista[j], lista[j + 1] = lista[j + 1], lista[j]
                claves[j], claves[j + 1] = claves[j + 1], claves[j]
                intercambios += 1
                hubo_intercambio = True
        if historial is not None:
            historial.append(list(lista))
        if not hubo_intercambio:
            break

    if estadisticas is not None:
        estadisticas.update(pasadas=pasadas, comparaciones=comparaciones,
                            intercambios=intercambios, elementos=n)
    return lista


def ordenar_por_fecha_nacimiento(personas: Iterable["Persona"], descendente: bool = False,
                                 estadisticas: dict | None = None,
                                 historial: list | None = None) -> list["Persona"]:
    """descendente=False: del mayor (nació antes) al menor. Sin fecha -> al final."""
    return ordenamiento_burbuja(personas, clave=lambda p: clave_fecha(p, descendente),
                                estadisticas=estadisticas, historial=historial)


def ordenar_hijos(persona: "Persona", en_lugar: bool = True) -> list["Persona"]:
    """Ordena los hijos de una persona por nacimiento (el mayor primero).

    en_lugar=True modifica persona.hijos (la misma lista, no una nueva),
    así cualquier otra parte del programa que la use ve el orden nuevo.
    """
    ordenados = ordenar_por_fecha_nacimiento(persona.hijos)
    if en_lugar:
        persona.hijos[:] = ordenados
    return ordenados


def ordenar_hijos_de_todos(arbol: "Arbol") -> None:
    for persona in arbol.personas.values():
        ordenar_hijos(persona, en_lugar=True)


def ordenar_por_id(personas: Iterable["Persona"], estadisticas: dict | None = None) -> list["Persona"]:
    return ordenamiento_burbuja(personas, clave=lambda p: normalizar(p.id), estadisticas=estadisticas)


# ===========================================================================
# Búsqueda binaria
# ===========================================================================
def busqueda_binaria_por_id(personas_ordenadas: list["Persona"], id_buscado: str,
                            pasos: list | None = None,
                            estadisticas: dict | None = None) -> "Persona | None":
    """Busca un id en una lista YA ORDENADA por id (usar ordenar_por_id). O(log n).

    No distingue mayúsculas: 'Karim' encuentra 'karim'.
    pasos: si se pasa una lista, se agrega un dict por cada iteración.
    """
    objetivo = normalizar(id_buscado)
    izquierda, derecha = 0, len(personas_ordenadas) - 1
    comparaciones = 0

    while izquierda <= derecha:
        medio = (izquierda + derecha) // 2
        id_medio = normalizar(personas_ordenadas[medio].id)
        comparaciones += 1

        if id_medio == objetivo:
            decision = "encontrado"
        elif id_medio < objetivo:
            decision = "buscar a la derecha"
        else:
            decision = "buscar a la izquierda"

        if pasos is not None:
            pasos.append({"izquierda": izquierda, "derecha": derecha, "medio": medio,
                          "id_en_medio": id_medio, "decision": decision})

        if decision == "encontrado":
            _sumar(estadisticas, comparaciones=comparaciones)
            return personas_ordenadas[medio]
        if id_medio < objetivo:
            izquierda = medio + 1
        else:
            derecha = medio - 1

    _sumar(estadisticas, comparaciones=comparaciones)
    return None


class IndicePorId:
    """Índice para buscar por id muchas veces sin reordenar cada vez.

    Ordenar con burbuja cuesta O(n²), así que se hace UNA vez al crear el
    índice; cada búsqueda después cuesta solo O(log n).

        indice = IndicePorId(arbol.personas.values())
        indice.buscar("karim")
        "karim" in indice
    """

    def __init__(self, personas: Iterable["Persona"]):
        self.estadisticas_orden: dict = {}
        self.ordenadas = ordenar_por_id(personas, self.estadisticas_orden)

    def buscar(self, id_buscado: str, pasos: list | None = None) -> "Persona | None":
        return busqueda_binaria_por_id(self.ordenadas, id_buscado, pasos)

    def ids(self) -> list[str]:
        return [p.id for p in self.ordenadas]

    def __contains__(self, id_buscado: str) -> bool:
        return self.buscar(id_buscado) is not None

    def __len__(self) -> int:
        return len(self.ordenadas)


def buscar_por_id(arbol: "Arbol", id_buscado: str, pasos: list | None = None) -> "Persona | None":
    """Atajo para una sola búsqueda. Para muchas búsquedas usar IndicePorId."""
    return IndicePorId(arbol.personas.values()).buscar(id_buscado, pasos)


def _limite_inferior(anios: list[int], valor: int) -> int:
    """Primer índice i tal que anios[i] >= valor (búsqueda binaria)."""
    izq, der = 0, len(anios)
    while izq < der:
        medio = (izq + der) // 2
        if anios[medio] < valor:
            izq = medio + 1
        else:
            der = medio
    return izq


def buscar_nacidos_entre(personas: Iterable["Persona"], desde: int, hasta: int) -> list["Persona"]:
    """Personas nacidas entre dos años (inclusive), usando búsqueda binaria.

    1. Se ordena por fecha (burbuja) y se descartan los que no tienen fecha.
    2. Con dos búsquedas binarias se halla dónde empieza y dónde termina el rango.
    """
    if desde > hasta:
        desde, hasta = hasta, desde
    con_fecha = [p for p in ordenar_por_fecha_nacimiento(personas) if anio_de(p) is not None]
    anios = [anio_de(p) for p in con_fecha]
    inicio = _limite_inferior(anios, desde)
    fin = _limite_inferior(anios, hasta + 1)
    return con_fecha[inicio:fin]


# ===========================================================================
# Búsqueda secuencial
# ===========================================================================
PARTICULAS = {"de", "del", "la", "las", "los", "y"}


def apellidos_de(nombre_completo: str) -> str:
    """Heurística para nombres hispanos (no hay forma 100 % segura sin un campo aparte).

    'Nayib Armando Bukele Ortez'   -> 'Bukele Ortez'          (4+ palabras: las 2 últimas)
    'Gabriela Rodriguez de Bukele' -> 'Rodriguez de Bukele'   (apellido de casada)
    'Juan Pérez de la Cruz'        -> 'Pérez de la Cruz'      (apellido compuesto)
    'Armando Bukele Kattan'        -> 'Bukele Kattan'          (3 palabras: las 2 últimas)
    'Olga Ortez'                   -> 'Ortez'
    """
    palabras = nombre_completo.split()
    if len(palabras) <= 1:
        return ""
    minus = [normalizar(p) for p in palabras]
    # una partícula a partir de la 3.ª palabra indica apellido compuesto/de casada
    for k in range(2, len(palabras)):
        if minus[k] in PARTICULAS and minus[k - 1] not in PARTICULAS:
            return " ".join(palabras[k - 1:])
    if len(palabras) >= 3:
        return " ".join(palabras[-2:])
    return palabras[-1]


def _relevancia(texto: str, palabras_buscadas: list[str]) -> int:
    """0 = no coincide. Mayor número = mejor coincidencia.

    Por cada palabra buscada: 3 si es una palabra exacta, 2 si es el inicio
    de una palabra, 1 si aparece en medio. Si alguna no aparece -> 0.
    """
    palabras_texto = texto.split()
    total = 0
    for buscada in palabras_buscadas:
        if buscada in palabras_texto:
            total += 3
        elif any(p.startswith(buscada) for p in palabras_texto):
            total += 2
        elif buscada in texto:
            total += 1
        else:
            return 0
    return total


def busqueda_secuencial(personas: Iterable["Persona"], termino: str, por: str = "nombre",
                        estadisticas: dict | None = None) -> list["Persona"]:
    """Revisa a las personas UNA POR UNA y devuelve todas las que coinciden. O(n).

    por = "nombre"   -> busca en el nombre completo
          "apellido" -> busca solo en los apellidos (ver apellidos_de)

    - No distingue mayúsculas ni tildes ("NÁYIB" == "nayib").
    - Varias palabras en cualquier orden: TODAS deben aparecer ("bukele nayib").
    - Los resultados vienen ordenados por relevancia (burbuja): primero las
      coincidencias exactas, después las parciales. Empates: orden original.
    """
    if por not in ("nombre", "apellido"):
        raise ValueError("por debe ser 'nombre' o 'apellido'")
    palabras_buscadas = normalizar(termino).split()
    if not palabras_buscadas:
        if estadisticas is not None:
            estadisticas.update(revisadas=0, encontradas=0)
        return []

    encontrados: list[tuple[int, "Persona"]] = []
    revisadas = 0
    for persona in personas:
        revisadas += 1
        campo = apellidos_de(persona.nombre) if por == "apellido" else persona.nombre
        puntos = _relevancia(normalizar(campo), palabras_buscadas)
        if puntos:
            encontrados.append((puntos, persona))

    ordenados = ordenamiento_burbuja(encontrados, clave=lambda par: par[0], descendente=True)
    if estadisticas is not None:
        estadisticas.update(revisadas=revisadas, encontradas=len(ordenados))
    return [persona for _, persona in ordenados]


def buscar_por_nombre(personas: Iterable["Persona"], termino: str) -> list["Persona"]:
    return busqueda_secuencial(personas, termino, por="nombre")


def buscar_por_apellido(personas: Iterable["Persona"], termino: str) -> list["Persona"]:
    return busqueda_secuencial(personas, termino, por="apellido")


# ===========================================================================
# Demostración:  python busquedas.py
# ===========================================================================
if __name__ == "__main__":
    from arbol import Arbol

    from pathlib import Path
    ruta = Path(__file__).resolve().parent.parent / "data" / "familia.json"
    arbol = Arbol.cargar_desde_json(str(ruta))
    personas = list(arbol.personas.values())

    print("== Burbuja por fecha de nacimiento ==")
    stats: dict = {}
    for p in ordenar_por_fecha_nacimiento(personas, estadisticas=stats):
        print(f"  {p.fecha_nacimiento or 'sin fecha':>10}  {p.nombre}")
    print("  ", stats)

    print("\n== Hijos de Armando ==")
    for h in ordenar_hijos(arbol.buscar_por_id("armando")):
        print(f"  {h.fecha_nacimiento or 'sin fecha':>10}  {h.nombre}")

    indice = IndicePorId(personas)
    print("\n== Índice por id ==", indice.ids())
    for buscado in ("karim", "YAMIL", "nadie"):
        pasos: list = []
        r = indice.buscar(buscado, pasos)
        print(f"  {buscado!r:8} -> {r.nombre if r else 'no existe'}  ({len(pasos)} pasos)")

    print("\n== Nacidos entre 1985 y 1990 ==")
    for p in buscar_nacidos_entre(personas, 1985, 1990):
        print("  ", p.fecha_nacimiento, p.nombre)

    print("\n== Secuencial 'bukele nayib' (nombre) ==")
    for p in buscar_por_nombre(personas, "bukele nayib"):
        print("  ", p.nombre)
    print("== Secuencial 'ortez' (apellido) ==")
    for p in buscar_por_apellido(personas, "ortez"):
        print("  ", p.nombre)
