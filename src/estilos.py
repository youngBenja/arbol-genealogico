# Paleta y config compartida del proyecto
COLOR_GENERACION = {0: "#4E79A7", 1: "#59A14F", 2: "#F28E2B", 3: "#B07AA1"}
COLOR_CONYUGE = "#E15759"
COLOR_RAMA = "#888888"


def color_de_generacion(g):
    # da la vuelta si hay más generaciones que colores
    return COLOR_GENERACION[g % len(COLOR_GENERACION)]
