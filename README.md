# 🌳 Árbol Genealógico

Árbol genealógico interactivo en Python, hecho solo con información pública y verificable (sin menores de edad).

## Equipo
- Datos: (nombre)
- Estructura: (nombre)
- Visualización: (nombre)
- Interfaz y búsquedas: (nombre)
- Integración: (nombre)

## Requisitos
Python 3.10 o superior.

## Instalación y ejecución
    pip install -r requirements.txt
    streamlit run src/app.py

## Pruebas
    pytest -v

## Estructura
- `data/familia.json`: personas, relaciones y fuentes
- `src/persona.py` y `src/arbol.py`: estructura de datos y recorridos
- `src/busquedas.py`: burbuja, búsqueda binaria y secuencial
- `src/visualizacion.py`: grafo con pyvis
- `src/app.py`: interfaz Streamlit
- `src/estilos.py`: colores compartidos
- `scripts/normalizar_json.py`: convierte el JSON original del rol 1 al formato final

## Notas
- Las personas agregadas desde la app se guardan en `data/familia.json` (con respaldo `.bak`).
- Para agregar a alguien desde la app hay que elegir al menos una fuente y no puede ser menor de edad.
