"""Interfaz Streamlit del árbol genealógico.

Ejecutar:   streamlit run app.py

Usa el trabajo de todo el equipo:
  arbol.py          -> carga del JSON, recorridos preorden / postorden / niveles
  visualizacion.py  -> generaciones, posiciones y vista pyvis
  busquedas.py      -> burbuja, búsqueda binaria y secuencial (integrante 4)
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import busquedas as bq
import visualizacion as viz
from arbol import Arbol
from estilos import color_de_generacion

RUTA_POR_DEFECTO = str(Path(__file__).resolve().parent.parent / "data" / "familia.json")
DORADO = "#C98B00"

st.set_page_config(page_title="Árbol genealógico", page_icon="🌳", layout="wide")


# ===========================================================================
# Estado de la sesión
# ===========================================================================
def _init_estado():
    st.session_state.setdefault("sel", None)          # id de la persona seleccionada
    st.session_state.setdefault("version_grafo", 0)   # cambia para reiniciar el clic
    st.session_state.setdefault("historial", [])      # personas consultadas
    st.session_state.setdefault("mensaje", None)


def seleccionar(pid: str | None):
    """Callback usado por todos los botones 'Ver ficha'."""
    st.session_state.sel = pid
    st.session_state.version_grafo += 1
    if pid:
        hist = [h for h in st.session_state.historial if h != pid]
        st.session_state.historial = ([pid] + hist)[:10]


_init_estado()


# ===========================================================================
# Lectura / escritura del JSON
# ===========================================================================
def leer_json(ruta: str) -> dict:
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta: str, datos: dict) -> None:
    ruta_p = Path(ruta)
    if ruta_p.exists():
        shutil.copyfile(ruta_p, ruta_p.with_suffix(".json.bak"))   # respaldo
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ===========================================================================
# Consultas familiares (a partir de los objetos Persona)
# ===========================================================================
def padres_de(arbol, persona):
    return [p for p in arbol.personas.values() if any(h.id == persona.id for h in p.hijos)]


def conyuge_de(persona):
    return getattr(persona, "conyuge", None)


def hermanos_de(arbol, persona):
    """[(persona, 'Hermano' | 'Medio hermano')]"""
    mis_padres = {p.id for p in padres_de(arbol, persona)}
    if not mis_padres:
        return []
    salida = []
    for otro in arbol.personas.values():
        if otro.id == persona.id:
            continue
        sus_padres = {p.id for p in padres_de(arbol, otro)}
        comunes = mis_padres & sus_padres
        if comunes:
            tipo = "Hermano/a" if comunes == mis_padres == sus_padres else "Medio hermano/a"
            salida.append((otro, tipo))
    return salida


def ancestros_de(arbol, persona):
    vistos, cola, salida = {persona.id}, [persona], []
    while cola:
        actual = cola.pop(0)
        for padre in padres_de(arbol, actual):
            if padre.id not in vistos:
                vistos.add(padre.id)
                salida.append(padre)
                cola.append(padre)
    return salida


def ruta_a_raiz(arbol, persona):
    """Camino persona -> padre -> abuelo... (primer padre que aparezca)."""
    ruta, actual, vistos = [persona], persona, {persona.id}
    while True:
        padres = [p for p in padres_de(arbol, actual) if p.id not in vistos]
        if not padres:
            return ruta
        actual = padres[0]
        vistos.add(actual.id)
        ruta.append(actual)


def edad(persona) -> str | None:
    f = bq.partes_fecha(persona.fecha_nacimiento)
    if not f or not f[1] or persona.fecha_fallecimiento:
        return None
    hoy = date.today()
    años = hoy.year - f[0] - ((hoy.month, hoy.day) < (f[1], f[2] or 1))
    return f"{años} años"


def ids_visibles(arbol, gen, modo, foco, generaciones):
    if modo == "Todo el árbol" or foco is None:
        ids = set(arbol.personas)
    elif modo == "Familia cercana":
        ids = {foco.id}
        ids |= {p.id for p in padres_de(arbol, foco)}
        ids |= {h.id for h in foco.hijos}
        ids |= {h.id for h, _ in hermanos_de(arbol, foco)}
        if conyuge_de(foco):
            ids.add(conyuge_de(foco).id)
    elif modo == "Descendientes":
        ids = {p.id for p in arbol.recorrido_preorden(foco)}       # integrante 1
        ids |= {conyuge_de(p).id for p in arbol.personas.values()
                if p.id in ids and conyuge_de(p)}
    else:  # Ancestros
        ids = {foco.id} | {p.id for p in ancestros_de(arbol, foco)}
    return {i for i in ids if gen[i] in generaciones}


# ===========================================================================
# Gráfico clicable (plotly)
# ===========================================================================
def _etiqueta_corta(p):
    """'Nayib Armando Bukele Ortez' -> 'Nayib Bukele' + parentesco corto."""
    apellidos = bq.apellidos_de(p.nombre).split()
    nombre = " ".join([p.nombre.split()[0]] + apellidos[:1]) if apellidos else p.nombre
    rol = p.parentesco.split(" (")[0]
    rol = rol if len(rol) <= 14 else rol[:13] + "…"
    return f"<b>{nombre}</b><br>{rol}"


def figura_arbol(arbol, gen, visibles, sel_id):
    sub = SimpleNamespace(personas={i: p for i, p in arbol.personas.items() if i in visibles})
    pos = viz.calcular_posiciones(sub, gen)   # integrante 3 (reacomoda solo lo visible)

    pareja_x, pareja_y = [], []
    rama_x, rama_y = [], []
    sola_x, sola_y = [], []
    union_x, union_y = [], []

    def codo(x0, y0, x1, y1, xs, ys):
        ym = (y0 + y1) / 2
        xs += [x0, x0, x1, x1, None]
        ys += [y0, ym, ym, y1, None]

    hechos, hijos_cubiertos = set(), set()
    for p in sub.personas.values():
        c = conyuge_de(p)
        if c is None or c.id not in visibles:
            continue
        par = tuple(sorted((p.id, c.id)))
        if par in hechos:
            continue
        hechos.add(par)
        (x0, y0), (x1, y1) = pos[p.id], pos[c.id]
        pareja_x += [x0, x1, None]
        pareja_y += [y0, y1, None]
        comunes = [h for h in p.hijos if h in c.hijos and h.id in visibles]
        if comunes:
            jx, jy = (x0 + x1) / 2, y0
            union_x.append(jx); union_y.append(jy)
            for h in comunes:
                codo(jx, jy, *pos[h.id], rama_x, rama_y)
                hijos_cubiertos.add((p.id, h.id)); hijos_cubiertos.add((c.id, h.id))

    for p in sub.personas.values():
        for h in p.hijos:
            if h.id in visibles and (p.id, h.id) not in hijos_cubiertos:
                codo(*pos[p.id], *pos[h.id], sola_x, sola_y)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rama_x, y=rama_y, mode="lines", hoverinfo="skip",
                             line=dict(color=viz.GRIS, width=2.5), name="Padres → hijos"))
    fig.add_trace(go.Scatter(x=sola_x, y=sola_y, mode="lines", hoverinfo="skip",
                             line=dict(color=viz.GRIS, width=2, dash="dash"),
                             name="Hijo de un solo padre"))
    fig.add_trace(go.Scatter(x=pareja_x, y=pareja_y, mode="lines", hoverinfo="skip",
                             line=dict(color=viz.ROSA, width=4, dash="dot"), name="Casados"))
    fig.add_trace(go.Scatter(x=union_x, y=union_y, mode="markers", hoverinfo="skip",
                             marker=dict(color=viz.GRIS, size=8), showlegend=False))

    ids = list(sub.personas)
    personas = [arbol.personas[i] for i in ids]
    colores = ["#FFFFFF" if p.fecha_fallecimiento else color_de_generacion(gen[p.id])
               for p in personas]
    bordes = [DORADO if p.id == sel_id else (viz.GRIS if p.fecha_fallecimiento
              else color_de_generacion(gen[p.id])) for p in personas]
    fig.add_trace(go.Scatter(
        x=[pos[i][0] for i in ids], y=[pos[i][1] for i in ids],
        mode="markers+text", customdata=ids, name="Personas", showlegend=False,
        text=[_etiqueta_corta(p) for p in personas], textposition="bottom center",
        textfont=dict(size=11, color="#222"),
        hovertext=[f"{p.nombre}<br>{p.parentesco}<br>Nac.: {p.fecha_nacimiento or '—'}"
                   + (f"<br>✝ {p.fecha_fallecimiento}" if p.fecha_fallecimiento else "")
                   + "<br><i>clic para ver ficha</i>" for p in personas],
        hoverinfo="text",
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
        marker=dict(size=[52 if i == sel_id else 40 for i in ids], color=colores, opacity=1,
                    symbol="circle", line=dict(color=bordes, width=[6 if i == sel_id else 3 for i in ids])),
    ))

    ys = [pos[i][1] for i in ids] or [0]
    xs = [pos[i][0] for i in ids] or [0]
    fig.update_layout(
        height=470, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#FAFAF5",
        paper_bgcolor="#FAFAF5", dragmode="pan", clickmode="event+select",
        legend=dict(orientation="h", y=1.02, x=0),
        xaxis=dict(visible=False, range=[min(xs) - 160, max(xs) + 160]),
        yaxis=dict(visible=False, range=[max(ys) + 120, min(ys) - 70]),
    )
    return fig


# ===========================================================================
# Ficha de la persona
# ===========================================================================
def boton_persona(p, contexto, etiqueta=None):
    st.button(etiqueta or p.nombre, key=f"btn_{contexto}_{p.id}", on_click=seleccionar,
              args=(p.id,), width="stretch")


def mostrar_ficha(arbol, p, gen):
    st.subheader(p.nombre)
    st.caption(f"`{p.id}` · {p.parentesco} · Generación {gen[p.id] + 1}")
    c1, c2 = st.columns(2)
    c1.metric("Nacimiento", p.fecha_nacimiento or "—", edad(p))
    c2.metric("Fallecimiento", p.fecha_fallecimiento or "—")
    if p.descripcion:
        st.write(p.descripcion)

    padres = padres_de(arbol, p)
    cony = conyuge_de(p)
    hijos = bq.ordenar_hijos(p, en_lugar=False)            # burbuja
    hermanos = hermanos_de(arbol, p)

    if padres:
        st.markdown("**Padres**")
        for x in padres:
            boton_persona(x, "padre")
    if cony:
        st.markdown("**Cónyuge**")
        boton_persona(cony, "cony")
    if hijos:
        st.markdown("**Hijos** (ordenados por nacimiento)")
        for x in hijos:
            boton_persona(x, "hijo", f"{x.nombre} · {x.fecha_nacimiento or 's/f'}")
    if hermanos:
        st.markdown("**Hermanos**")
        tipo_de = {h.id: t for h, t in hermanos}
        for x in bq.ordenar_por_fecha_nacimiento([h for h, _ in hermanos]):
            boton_persona(x, "herm", f"{x.nombre} · {tipo_de[x.id]}")

    ruta = ruta_a_raiz(arbol, p)
    if len(ruta) > 1:
        st.markdown("**Ruta de ancestros**")
        st.write(" → ".join(x.nombre.split()[0] for x in ruta))

    urls = arbol.urls_fuentes_de(p)
    if urls:
        with st.expander(f"Fuentes ({len(urls)})"):
            for u in urls:
                st.markdown(f"- [{u.split('/')[2] if '//' in u else u}]({u})")


# ===========================================================================
# Barra lateral
# ===========================================================================
with st.sidebar:
    st.title("🌳 Árbol genealógico")
    ruta_json = st.text_input("Archivo de datos", RUTA_POR_DEFECTO)
    if not Path(ruta_json).exists():
        st.error(f"No encuentro `{ruta_json}`.")
        st.stop()

    try:
        datos = leer_json(ruta_json)
        arbol = Arbol.cargar_desde_json(ruta_json)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        st.error(f"El JSON tiene un error: {e}")
        st.stop()

    gen = viz.calcular_generaciones(arbol)
    todas_gen = sorted(set(gen.values()))
    st.markdown("### Filtros")
    generaciones = st.multiselect("Generaciones", todas_gen, default=todas_gen,
                                  format_func=lambda g: f"Generación {g + 1}")
    modo = st.radio("Mostrar", ["Todo el árbol", "Familia cercana", "Descendientes", "Ancestros"])
    foco = None
    if modo != "Todo el árbol":
        opciones = [p.id for p in bq.ordenar_por_fecha_nacimiento(arbol.personas.values())]
        idx = opciones.index(st.session_state.sel) if st.session_state.sel in opciones else 0
        foco_id = st.selectbox("…de la persona", opciones, index=idx,
                               format_func=lambda i: arbol.personas[i].nombre)
        foco = arbol.personas[foco_id]

    if st.session_state.historial:
        st.markdown("### Consultados recientemente")
        for pid in st.session_state.historial:
            if pid in arbol.personas:
                boton_persona(arbol.personas[pid], "hist")

    st.caption(datos.get("nota", ""))

if st.session_state.sel not in arbol.personas:
    st.session_state.sel = None

if st.session_state.mensaje:
    st.success(st.session_state.mensaje)
    st.session_state.mensaje = None

# ===========================================================================
# Pestañas
# ===========================================================================
t_arbol, t_buscar, t_ordenar, t_gen, t_form, t_pyvis = st.tabs(
    ["🌳 Árbol", "🔎 Buscar", "↕️ Ordenar", "🧬 Generaciones y recorridos",
     "✏️ Agregar / editar", "🕸️ Vista pyvis"])

# ---------------------------------------------------------------- Árbol ----
with t_arbol:
    visibles = ids_visibles(arbol, gen, modo, foco, set(generaciones))
    col_g, col_f = st.columns([5, 3], gap="large")
    with col_g:
        st.caption(f"Mostrando {len(visibles)} de {len(arbol.personas)} personas · "
                   "Hacé clic en un círculo para ver su ficha · Blanco = fallecido")
        if not visibles:
            st.info("Ninguna persona cumple los filtros.")
        else:
            evento = st.plotly_chart(
                figura_arbol(arbol, gen, visibles, st.session_state.sel),
                on_select="rerun", selection_mode="points", theme=None,
                key=f"grafo_{st.session_state.version_grafo}",
                config={"displayModeBar": False, "scrollZoom": True},
            )
            puntos = (evento.selection.points if evento and evento.selection else []) or []
            for pt in puntos:
                cd = pt.get("customdata")
                if isinstance(cd, list):
                    cd = cd[0] if cd else None
                if cd in arbol.personas and cd != st.session_state.sel:
                    seleccionar(cd)
                    st.rerun()
    with col_f:
        if st.session_state.sel:
            mostrar_ficha(arbol, arbol.personas[st.session_state.sel], gen)
            st.button("Cerrar ficha", on_click=seleccionar, args=(None,))
        else:
            st.info("👈 Seleccioná a alguien en el árbol.")

# --------------------------------------------------------------- Buscar ----
with t_buscar:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Búsqueda secuencial por nombre o apellido")
        termino = st.text_input("Escribí un nombre o apellido", placeholder="ej. ortez, nayib, rodríguez")
        por = st.radio("Buscar en", ["nombre", "apellido"], horizontal=True,
                       format_func=lambda x: "Nombre completo" if x == "nombre" else "Solo apellidos")
        if termino:
            stats = {}
            res = bq.busqueda_secuencial(arbol.personas.values(), termino, por=por, estadisticas=stats)
            st.caption(f"Revisó {stats['revisadas']} personas una por una · {stats['encontradas']} coincidencias")
            if not res:
                st.warning("Sin resultados.")
            for p in res:
                with st.container(border=True):
                    a, b = st.columns([3, 1])
                    a.markdown(f"**{p.nombre}**  \n{p.parentesco} · apellidos: *{bq.apellidos_de(p.nombre)}*")
                    b.button("Ver ficha", key=f"busq_{p.id}", on_click=seleccionar, args=(p.id,))

    with c2:
        st.markdown("#### Búsqueda binaria por identificador")
        indice = bq.IndicePorId(arbol.personas.values())      # se ordena una sola vez
        st.caption("Lista ordenada por id (con burbuja): " + " · ".join(f"`{i}`" for i in indice.ids()))
        id_buscar = st.text_input("Identificador", placeholder="ej. karim").strip()
        if id_buscar:
            pasos = []
            encontrada = indice.buscar(id_buscar, pasos)
            st.dataframe(
                [{"Paso": i + 1, "Izq": s["izquierda"], "Der": s["derecha"], "Medio": s["medio"],
                  "Id en medio": s["id_en_medio"], "Decisión": s["decision"]} for i, s in enumerate(pasos)],
                hide_index=True, width="stretch")
            if encontrada:
                st.success(f"Encontrada en {len(pasos)} paso(s): **{encontrada.nombre}** "
                           f"(secuencial habría necesitado hasta {len(indice)})")
                st.button("Ver ficha", key="bin_ver", on_click=seleccionar, args=(encontrada.id,))
            else:
                st.error(f"No existe el id `{id_buscar}` (descartado en {len(pasos)} pasos).")

        st.markdown("#### Nacidos entre dos años (búsqueda binaria)")
        anios = [a for a in (bq.anio_de(p) for p in arbol.personas.values()) if a]
        if anios:
            lo, hi = min(anios), max(anios)
            desde, hasta = st.slider("Rango de años", lo - 5, hi + 5, (lo, hi))
            rango = bq.buscar_nacidos_entre(arbol.personas.values(), desde, hasta)
            st.caption(f"{len(rango)} persona(s) nacidas entre {desde} y {hasta}. "
                       "Quienes no tienen fecha registrada no aparecen.")
            for p in rango:
                a, b = st.columns([3, 1])
                a.write(f"{p.fecha_nacimiento} · {p.nombre}")
                b.button("Ver ficha", key=f"rango_{p.id}", on_click=seleccionar, args=(p.id,))
        else:
            st.info("Nadie tiene fecha de nacimiento registrada.")

# -------------------------------------------------------------- Ordenar ----
with t_ordenar:
    st.markdown("#### Ordenamiento burbuja por fecha de nacimiento")
    c1, c2 = st.columns([1, 3])
    sentido = c1.radio("Orden", ["Mayor a menor edad", "Menor a mayor edad"])
    solo_vis = c1.checkbox("Solo generaciones filtradas", value=False)
    base = [p for p in arbol.personas.values() if not solo_vis or gen[p.id] in generaciones]
    stats, historial = {}, []
    ordenadas = bq.ordenar_por_fecha_nacimiento(base, descendente=sentido.startswith("Menor"),
                                                estadisticas=stats, historial=historial)
    c1.metric("Pasadas", stats.get("pasadas", 0))
    c1.metric("Comparaciones", stats.get("comparaciones", 0))
    c1.metric("Intercambios", stats.get("intercambios", 0))
    c2.dataframe([{"#": i + 1, "Nombre": p.nombre, "Nacimiento": p.fecha_nacimiento or "sin fecha",
                   "Edad": edad(p) or "", "Parentesco": p.parentesco}
                  for i, p in enumerate(ordenadas)], hide_index=True, width="stretch")
    c2.caption("Las personas sin fecha registrada quedan al final (en orden alfabético).")

    with st.expander("Ver el ordenamiento burbuja paso a paso"):
        if len(historial) > 1:
            paso = st.slider("Pasada", 0, len(historial) - 1, len(historial) - 1,
                             help="0 = lista original. Cada pasada lleva al mayor restante a su lugar.")
            antes = historial[paso - 1] if paso else historial[0]
            ahora = historial[paso]
            fijos = len(ahora) - paso      # desde aquí ya quedaron en su lugar final
            st.dataframe([{"Posición": i + 1, "Persona": p.nombre,
                           "Nacimiento": p.fecha_nacimiento or "sin fecha",
                           "¿Se movió?": "↕️" if paso and antes[i] is not p else "",
                           "Estado": "✅ en su lugar" if paso and i >= fijos else ""}
                          for i, p in enumerate(ahora)], hide_index=True, width="stretch")
            if paso == len(historial) - 1 and paso < len(ahora) - 1:
                st.caption("En esta pasada no hubo intercambios, así que el algoritmo se detuvo antes.")
        else:
            st.info("Se necesitan al menos 2 personas.")

    st.markdown("#### Hijos ordenados por fecha de nacimiento")
    con_hijos = [p for p in arbol.personas.values() if p.hijos]
    if not con_hijos:
        st.info("Nadie tiene hijos registrados.")
    cols = st.columns(max(1, len(con_hijos)))
    for col, padre in zip(cols, con_hijos):
        with col.container(border=True):
            st.markdown(f"**{padre.nombre}**")
            for i, h in enumerate(bq.ordenar_hijos(padre, en_lugar=False), 1):
                st.write(f"{i}. {h.nombre} — {h.fecha_nacimiento or 'sin fecha'}")

# ---------------------------------------------------------- Generaciones ----
with t_gen:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Familiares por generación")
        for g in todas_gen:
            miembros = bq.ordenar_por_fecha_nacimiento([p for p in arbol.personas.values() if gen[p.id] == g])
            with st.expander(f"Generación {g + 1} · {len(miembros)} personas", expanded=True):
                for p in miembros:
                    boton_persona(p, f"gen{g}", f"{p.nombre} — {p.parentesco}")
    with c2:
        st.markdown("#### Recorridos del árbol (integrante 1)")
        sin_padres = [p.id for p in arbol.personas.values() if not padres_de(arbol, p)]
        raiz_id = st.selectbox("Empezar desde", sin_padres + [i for i in arbol.personas if i not in sin_padres],
                               format_func=lambda i: arbol.personas[i].nombre)
        arbol.raiz = arbol.personas[raiz_id]
        tipo = st.radio("Recorrido", ["Preorden", "Postorden", "Por niveles (cola)"], horizontal=True)
        if tipo == "Preorden":
            filas = [(i + 1, p.nombre) for i, p in enumerate(arbol.recorrido_preorden())]
        elif tipo == "Postorden":
            filas = [(i + 1, p.nombre) for i, p in enumerate(arbol.recorrido_postorden())]
        else:
            filas = [(f"Nivel {n}", p.nombre) for n, p in arbol.recorrido_por_niveles()]
        st.dataframe([{"Orden": a, "Persona": b} for a, b in filas], hide_index=True,
                     width="stretch")

# ------------------------------------------------------------ Formulario ----
def descendientes_ids(lista, raiz_id):
    """Ids de todos los descendientes de raiz_id (para evitar ciclos al editar padres)."""
    hijos_de = {}
    for x in lista:
        for p in x.get("padres", []):
            hijos_de.setdefault(str(p), []).append(str(x["id"]))
    vistos, pila = set(), [raiz_id]
    while pila:
        for h in hijos_de.get(pila.pop(), []):
            if h not in vistos:
                vistos.add(h)
                pila.append(h)
    return vistos


ID_VALIDO = re.compile(r"^[a-z0-9_]+$")
FECHA_VALIDA = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

with t_form:
    lista = datos.setdefault("personas", [])
    por_id = {str(x["id"]): x for x in lista}
    accion = st.radio("¿Qué querés hacer?", ["Agregar persona", "Editar persona", "Eliminar persona"],
                      horizontal=True)

    if accion == "Eliminar persona":
        if not por_id:
            st.info("No hay personas.")
        else:
            borrar = st.selectbox("Persona", list(por_id), format_func=lambda i: por_id[i]["nombre"])
            seguro = st.checkbox(f"Confirmo que quiero eliminar a {por_id[borrar]['nombre']}")
            if st.button("Eliminar", type="primary", disabled=not seguro):
                datos["personas"] = [x for x in lista if str(x["id"]) != borrar]
                for x in datos["personas"]:
                    x["padres"] = [i for i in x.get("padres", []) if str(i) != borrar]
                    if str(x.get("conyuge")) == borrar:
                        x["conyuge"] = None
                if datos.get("raiz") == borrar:
                    datos["raiz"] = datos["personas"][0]["id"] if datos["personas"] else None
                guardar_json(ruta_json, datos)
                st.session_state.mensaje = "Persona eliminada (se guardó un respaldo .bak)."
                seleccionar(None)
                st.rerun()
    else:
        editando = accion == "Editar persona"
        actual = {}
        if editando:
            if not por_id:
                st.info("No hay personas para editar.")
                st.stop()
            idx = list(por_id).index(st.session_state.sel) if st.session_state.sel in por_id else 0
            elegido = st.selectbox("Persona a editar", list(por_id), index=idx,
                                   format_func=lambda i: por_id[i]["nombre"])
            actual = por_id[elegido]

        otros = [i for i in por_id if i != actual.get("id")]
        nombre_de = lambda i: por_id[i]["nombre"]
        catalogo = datos.get("fuentes", {})

        with st.form(f"form_{accion}_{actual.get('id', 'nuevo')}", clear_on_submit=not editando):
            c1, c2 = st.columns(2)
            nuevo_id = c1.text_input("Identificador *", actual.get("id", ""), disabled=editando,
                                     help="Minúsculas, números y _ (ej. karim, abuela_olga)")
            nombre = c2.text_input("Nombre completo *", actual.get("nombre", ""))
            parentesco = c1.text_input("Parentesco", actual.get("parentesco", ""))
            nac = c2.text_input("Fecha de nacimiento", actual.get("fecha_nacimiento") or "",
                                placeholder="AAAA-MM-DD o AAAA")
            fall = c1.text_input("Fecha de fallecimiento", actual.get("fecha_fallecimiento") or "",
                                 placeholder="vacío si vive")
            padres_sel = c2.multiselect("Padres (máx. 2)", otros,
                                        default=[str(i) for i in actual.get("padres", []) if str(i) in otros],
                                        format_func=nombre_de, max_selections=2)
            cony_ops = [""] + otros
            cony_act = str(actual.get("conyuge") or "")
            cony = c1.selectbox("Cónyuge", cony_ops,
                                index=cony_ops.index(cony_act) if cony_act in cony_ops else 0,
                                format_func=lambda i: "— ninguno —" if not i else nombre_de(i))
            fuentes_sel = c2.multiselect("Fuentes", list(catalogo),
                                         default=[f for f in actual.get("fuentes", []) if f in catalogo])
            descripcion = st.text_area("Descripción", actual.get("descripcion", ""))
            enviar = st.form_submit_button("Guardar cambios" if editando else "Agregar a la familia",
                                           type="primary")

        if enviar:
            pid = (actual.get("id") if editando else nuevo_id.strip().lower())
            errores = []
            if not pid or not ID_VALIDO.match(pid):
                errores.append("El identificador es obligatorio y solo admite minúsculas, números y _.")
            elif not editando and pid in por_id:
                errores.append(f"Ya existe alguien con el id `{pid}`.")
            if not nombre.strip():
                errores.append("El nombre es obligatorio.")
            for etiqueta, valor in (("nacimiento", nac), ("fallecimiento", fall)):
                v = valor.strip()
                if v and (not FECHA_VALIDA.match(v) or bq.partes_fecha(v) is None):
                    errores.append(f"La fecha de {etiqueta} no es válida (AAAA-MM-DD o AAAA).")
            f_nac, f_fall = bq.partes_fecha(nac.strip()), bq.partes_fecha(fall.strip())
            if f_nac and f_fall and f_fall < f_nac:
                errores.append("La fecha de fallecimiento es anterior al nacimiento.")
            if f_nac and not f_fall and date.today().year - f_nac[0] < 18:
                errores.append("El proyecto no incluye menores de edad.")
            if not fuentes_sel:
                errores.append("Elige al menos una fuente.")
            if editando and set(padres_sel) & descendientes_ids(lista, pid):
                errores.append("Un padre no puede ser descendiente de la persona (haría un ciclo).")
            if pid in padres_sel or pid == cony:
                errores.append("Una persona no puede ser su propio padre ni cónyuge.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                registro = actual if editando else {"id": pid, "foto": None}
                registro.update(nombre=nombre.strip(), parentesco=parentesco.strip(),
                                fecha_nacimiento=nac.strip() or None,
                                fecha_fallecimiento=fall.strip() or None,
                                descripcion=descripcion.strip(), padres=padres_sel,
                                conyuge=cony or None, fuentes=fuentes_sel)
                if not editando:
                    lista.append(registro)
                # mantener el cónyuge recíproco
                for x in lista:
                    if x is registro:
                        continue
                    if str(x["id"]) == cony:
                        if x.get("conyuge") and str(x["conyuge"]) != pid:      # deja a su anterior pareja
                            if str(x["conyuge"]) in por_id:
                                por_id[str(x["conyuge"])]["conyuge"] = None
                        x["conyuge"] = pid
                    elif str(x.get("conyuge")) == pid:
                        x["conyuge"] = None
                guardar_json(ruta_json, datos)
                st.session_state.mensaje = (f"✅ {'Actualizado' if editando else 'Agregado'}: "
                                            f"{nombre.strip()} (respaldo guardado como .bak)")
                seleccionar(pid)
                st.rerun()

# ----------------------------------------------------------------- pyvis ----
with t_pyvis:
    st.caption("Vista original de visualizacion.py (integrante 3). Arrastrá y hacé zoom; "
               "pasá el mouse sobre una persona para ver su ficha.")
    try:
        html = viz.generar_html(arbol)
        if hasattr(st, "iframe"):
            st.iframe(html, height=780)
        else:
            components.html(html, height=780, scrolling=False)
    except Exception as e:   # pyvis no instalado o error de plantilla
        st.warning(f"No se pudo generar la vista pyvis: {e}")
