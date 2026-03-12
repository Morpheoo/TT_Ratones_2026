import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZADOR DE ZONAS  (soluciona el Bug C3)
#
# El sistema tiene DOS orígenes de zonas con formatos de claves distintos:
#
#  Origen A – _02_Configuracion_Zonas.py (flujo normal)
#    rect  → {"type":"rect", "Nombre Zona":"...", "left":X, "top":Y,
#               "width":W, "height":H}
#    line  → {"type":"line", "Nombre Zona":"...", "x1":X1, "y1":Y1,
#               "x2":X2, "y2":Y2}
#
#  Origen B – 03_Analisis_IA.py / Carga Rápida de template
#    rect  → {"type":"rect", "id":"...", "x":X, "y":Y, "w":W, "h":H}
#    line  → {"type":"line", "id":"...",  "x1":X1, "y1":Y1, "x2":X2, "y2":Y2}
#
# Formato canónico interno (el que usan checar_zona / detectar_thigmotaxis):
#    rect  → {"type":"rect", "Nombre Zona":"...", "left":X, "top":Y,
#               "width":W, "height":H}
#    line  → {"type":"line", "Nombre Zona":"...", "x1":X1, "y1":Y1,
#               "x2":X2, "y2":Y2}
# ─────────────────────────────────────────────────────────────────────────────

def normalizar_zona(zona: dict) -> dict:
    """
    Convierte cualquier zona (formato A o B) al formato canónico interno.
    Retorna un nuevo dict sin mutar el original.
    """
    z = dict(zona)  # copia defensiva

    # ── Nombre canónico ──────────────────────────────────────────────────────
    # Origen A usa "Nombre Zona"; Origen B usa "id"
    if "Nombre Zona" not in z or not z.get("Nombre Zona"):
        z["Nombre Zona"] = z.get("id", "Zona Desconocida")

    tipo = z.get("type", "rect")

    if tipo == "rect":
        # ── Coordenadas canónicas para rectángulo ────────────────────────────
        # Origen A: left / top / width / height
        # Origen B: x / y / w / h
        if "left" not in z and "x" in z:
            z["left"]   = z.get("x", 0)
            z["top"]    = z.get("y", 0)
            z["width"]  = z.get("w", 0)
            z["height"] = z.get("h", 0)

    # Para líneas (line) ambos orígenes ya usan x1/y1/x2/y2 → no hace falta mapear

    return z


def normalizar_lista_zonas(zonas_lista: list) -> list:
    """Normaliza toda la lista de zonas de una vez. Itera una sola vez."""
    return [normalizar_zona(z) for z in zonas_lista]


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE ANÁLISIS  (trabajan exclusivamente con formato canónico)
# ─────────────────────────────────────────────────────────────────────────────

def checar_zona(punto_xy, zonas_lista: list) -> str:
    """
    Revisa en qué zona cae el punto (x, y) del ratón.
    Acepta zonas en CUALQUIER formato (normaliza internamente).
    Retorna el nombre de zona o "Fuera del Laberinto".
    """
    x, y = punto_xy
    zonas_norm = normalizar_lista_zonas(zonas_lista)

    for zona in zonas_norm:
        nombre = zona.get("Nombre Zona", "")
        tipo   = zona.get("type", "rect")

        # Los muros/paredes no son zonas habitables
        if tipo == "line":
            continue
        nombre_lower = nombre.lower()
        if "muro" in nombre_lower or "pared" in nombre_lower:
            continue

        x_min = zona.get("left", 0)
        x_max = x_min + zona.get("width", 0)
        y_min = zona.get("top", 0)
        y_max = y_min + zona.get("height", 0)

        if x_min <= x <= x_max and y_min <= y <= y_max:
            return nombre

    return "Fuera del Laberinto"


def calcular_distancia(p1, p2) -> float:
    return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))


def detectar_grooming(nose, tail_base, velocity_px_s,
                      umbral_velocidad=20.0, umbral_distancia=60.0) -> bool:
    """
    Heurística de acicalamiento:
    1. Velocidad baja (el ratón suele detenerse para acicalarse).
    2. Distancia Nariz-Cola corta (se hace 'bolita').

    Args:
        nose            (tuple): (x, y) de la nariz.
        tail_base       (tuple): (x, y) de la base de la cola.
        velocity_px_s   (float): Velocidad actual en px/s.
        umbral_velocidad(float): Velocidad máxima para considerar grooming.
        umbral_distancia(float): Distancia máxima nariz-cola para 'bolita'.
    """
    dist_cuerpo = calcular_distancia(nose, tail_base)
    return velocity_px_s < umbral_velocidad and dist_cuerpo < umbral_distancia


def distancia_punto_segmento(x, y, x1, y1, x2, y2) -> float:
    """Distancia ortogonal mínima de un punto (x,y) a un segmento (x1,y1)→(x2,y2)."""
    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0:
        return float(np.sqrt((x - x1)**2 + (y - y1)**2))

    t = max(0.0, min(1.0,
        ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2
    ))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    return float(np.sqrt((x - proj_x)**2 + (y - proj_y)**2))


def detectar_thigmotaxis(punto, zona_nombre, zonas_lista: list,
                         margin_px: int = 22) -> bool:
    """
    Thigmotaxis = contacto con pared.

    Estrategia 1 (prioritaria): Si el usuario dibujó muros explícitos (líneas),
    calcula la distancia ortogonal al segmento más cercano.
    Estrategia 2 (fallback):    Distancia a los bordes rectangulares del brazo cerrado más cercano.

    IMPORTANTE: NO revierte a bounding-boxes cuando hay muros dibujados.
    """
    x, y = punto
    zonas_norm = normalizar_lista_zonas(zonas_lista)

    # ── Estrategia 1: muros físicos dibujados ────────────────────────────────
    muros = [
        z for z in zonas_norm
        if z.get("type") == "line"
        or "muro"  in z.get("Nombre Zona", "").lower()
        or "pared" in z.get("Nombre Zona", "").lower()
    ]

    if muros:
        for muro in muros:
            x1 = muro.get("x1", 0)
            y1 = muro.get("y1", 0)
            x2 = muro.get("x2", 0)
            y2 = muro.get("y2", 0)
            if distancia_punto_segmento(x, y, x1, y1, x2, y2) <= margin_px:
                return True
        return False  # Hay muros pero el ratón no está cerca de ninguno

    # ── Estrategia 2: fallback con bordes del brazo cerrado ──────────────────
    if "Cerrado" not in zona_nombre:
        return False

    zona_obj = next(
        (z for z in zonas_norm if z.get("Nombre Zona") == zona_nombre),
        None
    )
    if not zona_obj:
        return False

    left   = zona_obj.get("left",   0)
    top    = zona_obj.get("top",    0)
    right  = left + zona_obj.get("width",  0)
    bottom = top  + zona_obj.get("height", 0)

    toca_izq = abs(x - left)   < margin_px
    toca_der = abs(x - right)  < margin_px
    toca_arr = abs(y - top)    < margin_px
    toca_aba = abs(y - bottom) < margin_px

    return toca_izq or toca_der or toca_arr or toca_aba
