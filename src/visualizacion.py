from pathlib import Path
from pyvis.network import Network
from arbol import Arbol
from estilos import color_de_generacion, COLOR_CONYUGE, COLOR_RAMA

ROSA, GRIS = COLOR_CONYUGE, COLOR_RAMA   # colores salen de estilos.py
CENTRO = "nayib"          # persona que queda al centro
# Orden de izquierda a derecha dentro de cada generación (los ids que falten se agregan al final)
ORDEN = ["armando", "olga", "ibrajim", "yusef", "karim", "nayib", "gabriela", "yamil"]
ANCHO, ALTO = 250, 280    # separación horizontal y vertical entre nodos


def calcular_generaciones(arbol):
    """Hijo = generación del padre + 1; los cónyuges quedan en la misma generación."""
    gen = {pid: 0 for pid in arbol.personas}
    for _ in range(len(gen) + 1):
        cambio = False
        for p in arbol.personas.values():
            for h in p.hijos:
                if gen[h.id] < gen[p.id] + 1:
                    gen[h.id] = gen[p.id] + 1; cambio = True
            c = getattr(p, "conyuge", None)
            if c is not None and gen[p.id] != gen[c.id]:
                gen[p.id] = gen[c.id] = max(gen[p.id], gen[c.id]); cambio = True
        if not cambio:
            break
    return gen


def calcular_posiciones(arbol, gen):
    """Devuelve {id: (x, y)}. La fila de CENTRO se ancla con él en x=0; las demás se centran."""
    filas = {}
    ids = [i for i in ORDEN if i in arbol.personas] + [i for i in arbol.personas if i not in ORDEN]
    for pid in ids:
        filas.setdefault(gen[pid], []).append(pid)
    pos = {}
    for g, fila in filas.items():
        base = fila.index(CENTRO) if CENTRO in fila else (len(fila) - 1) / 2
        for i, pid in enumerate(fila):
            sep = ANCHO if CENTRO in fila else ANCHO * 1.8   # padres más separados
            pos[pid] = ((i - base) * sep, g * ALTO)
    return pos


def _etiqueta(p):
    partes = p.nombre.split()
    nombre = " ".join(partes[:2]) + ("\n" + " ".join(partes[2:]) if len(partes) > 2 else "")
    parentesco = p.parentesco.split(" (")[0]
    fecha = p.fecha_nacimiento or "fecha no disponible"
    texto = f"{nombre}\n{parentesco}\n* {fecha}"
    if p.fecha_fallecimiento:
        texto += f"\n† {p.fecha_fallecimiento}"
    return texto


def _ficha(p):
    t = [p.nombre, p.parentesco]
    if p.fecha_fallecimiento: t.append(f"Falleció: {p.fecha_fallecimiento}")
    if p.descripcion: t += ["", p.descripcion]
    return "\n".join(t)


def construir_red(arbol, alto="750px"):
    net = Network(height=alto, width="100%", directed=False, bgcolor="#FAFAF5",
                  font_color="#222222", cdn_resources="in_line")   # sin esto sale en blanco en Streamlit
    gen = calcular_generaciones(arbol)
    pos = calcular_posiciones(arbol, gen)

    for p in arbol.personas.values():
        g, fall = gen[p.id], bool(p.fecha_fallecimiento)
        color = color_de_generacion(g)
        x, y = pos[p.id]
        net.add_node(p.id, label=_etiqueta(p), title=_ficha(p), shape="box", margin=12,
                     x=x, y=y, physics=False, fixed=True, borderWidth=3,
                     color={"background": "#FFFFFF" if fall else color, "border": GRIS if fall else color,
                            "highlight": {"background": "#FFE08A", "border": "#C98B00"}},
                     font={"size": 15, "color": "#222222" if fall else "#FFFFFF"})

    hecho = set()
    for p in arbol.personas.values():
        c = getattr(p, "conyuge", None)
        if c is None:
            continue
        par = tuple(sorted((p.id, c.id)))
        if par in hecho:
            continue
        hecho.add(par)
        net.add_edge(p.id, c.id, color=ROSA, width=4, dashes=True, label="casados",
                     font={"size": 12, "color": ROSA, "strokeWidth": 0}, smooth=False)
        # Rama: punto de unión de la pareja -> hijos que tienen en común
        comunes = [h for h in p.hijos if h in c.hijos]
        if comunes:
            jx = (pos[p.id][0] + pos[c.id][0]) / 2
            jy = pos[p.id][1]
            jid = f"union_{par[0]}_{par[1]}"
            net.add_node(jid, label=" ", shape="dot", size=6, x=jx, y=jy,
                         physics=False, fixed=True, color=GRIS)
            for h in comunes:
                net.add_edge(jid, h.id, color=GRIS, width=2.5,
                             smooth={"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.6})

    # Hijos de un solo padre/madre (ej. medios hermanos): rama directa punteada
    for p in arbol.personas.values():
        for h in p.hijos:
            c = getattr(p, "conyuge", None)
            if c is None or h not in c.hijos:
                net.add_edge(p.id, h.id, color=GRIS, width=2, dashes=True,
                             smooth={"type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.6})

    net.set_options("""{"physics":{"enabled":false},
      "interaction":{"hover":true,"navigationButtons":true,"tooltipDelay":100}}""")
    return net


def generar_html(arbol, alto="750px"):
    return construir_red(arbol, alto).generate_html()


def exportar_html(arbol, ruta="arbol_genealogico.html"):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(generar_html(arbol))
    return ruta


if __name__ == "__main__":
    ruta = Path(__file__).resolve().parent.parent / "data" / "familia.json"
    arbol = Arbol.cargar_desde_json(str(ruta), id_raiz_preferida="nayib")
    print("Archivo generado:", exportar_html(arbol))
