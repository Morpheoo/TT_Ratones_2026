import numpy as np

def checar_zona(punto_xy, zonas_lista):
    """
    Revisa en qué zona cae el punto (x, y) del ratón.
    Retorna (Nombre de Zona) o "Fuera del Laberinto".
    """
    x, y = punto_xy
    for zona in zonas_lista:
        x_min = zona["left"]
        x_max = zona["left"] + zona["width"]
        y_min = zona["top"]
        y_max = zona["top"] + zona["height"]

        if x_min <= x <= x_max and y_min <= y <= y_max:
            return zona["Nombre Zona"]
    return "Fuera del Laberinto"

def calcular_distancia(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def detectar_grooming(nose, tail_base, velocity_px_s, umbral_velocidad=20.0, umbral_distancia=60.0):
    """
    Heurística:
    1. Velocidad baja (el ratón suele detenerse para acicalarse).
    2. Distancia Nariz-Cola corta (se hace 'bolita').
    
    Args:
        nose (tuple): (x, y) de la nariz.
        tail_base (tuple): (x, y) de la base de la cola.
        velocity_px_s (float): Velocidad actual en px/s.
        umbral_velocidad (float): Velocidad máxima para considerar grooming.
        umbral_distancia (float): Distancia máxima nariz-cola para considerar 'bolita'.
    """
    dist_cuerpo = calcular_distancia(nose, tail_base)
    
    if velocity_px_s < umbral_velocidad and dist_cuerpo < umbral_distancia:
        return True
    return False

def detectar_thigmotaxis(punto, zona_nombre, zonas_lista, margin_px=15):
    """
    Heurística: Está en un Brazo Cerrado y muy cerca del borde (pared).
    """
    if "Cerrado" not in zona_nombre:
        return False
        
    # Buscar la zona actual
    zona_obj = next((z for z in zonas_lista if z["Nombre Zona"] == zona_nombre), None)
    if not zona_obj: return False
    
    x, y = punto
    left = zona_obj["left"]
    top = zona_obj["top"]
    right = left + zona_obj["width"]
    bottom = top + zona_obj["height"]
    
    # Distancia a los bordes laterales (paredes)
    toca_izq = abs(x - left) < margin_px
    toca_der = abs(x - right) < margin_px
    toca_arr = abs(y - top) < margin_px
    toca_aba = abs(y - bottom) < margin_px
    
    return toca_izq or toca_der or toca_arr or toca_aba
