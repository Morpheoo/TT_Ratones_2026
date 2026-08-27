from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path("reportes/figuras/secuencia_53")
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 2400, 1550
MARGIN = 90
TOP = 180
BOX_H = 86
LIFE_TOP = TOP + BOX_H
LIFE_BOTTOM = H - 155


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_HEAD = font(31, True)
F_MSG = font(25)
F_SMALL = font(22)
F_ALT = font(27, True)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        test = word if not cur else f"{cur} {word}"
        if text_size(draw, test, fnt)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_centered_multiline(draw, center_x, y, text, fnt, max_width, fill=(0, 0, 0)):
    lines = wrap_text(draw, text, fnt, max_width)
    line_h = text_size(draw, "Ag", fnt)[1] + 8
    start_y = y - (len(lines) * line_h) / 2
    for i, line in enumerate(lines):
        tw, _ = text_size(draw, line, fnt)
        draw.text((center_x - tw / 2, start_y + i * line_h), line, font=fnt, fill=fill)


def arrow(draw, x1, y1, x2, y2, dashed=False):
    if abs(x2 - x1) < 2:
        # UML self-message loop.
        loop_w = 105
        loop_h = 58
        draw.line((x1, y1, x1 + loop_w, y1), fill="black", width=3)
        draw.line((x1 + loop_w, y1, x1 + loop_w, y1 + loop_h), fill="black", width=3)
        draw.line((x1 + loop_w, y1 + loop_h, x1 + 18, y1 + loop_h), fill="black", width=3)
        draw.polygon([(x1 + 18, y1 + loop_h), (x1 + 34, y1 + loop_h - 8), (x1 + 34, y1 + loop_h + 8)], fill="black")
        return

    if dashed:
        dash = 18
        gap = 12
        total = abs(x2 - x1)
        direction = 1 if x2 >= x1 else -1
        x = x1
        while abs(x - x1) < total:
            nx = x + direction * min(dash, total - abs(x - x1))
            draw.line((x, y1, nx, y2), fill="black", width=3)
            x = nx + direction * gap
    else:
        draw.line((x1, y1, x2, y2), fill="black", width=3)

    direction = 1 if x2 >= x1 else -1
    size = 16
    pts = [
        (x2, y2),
        (x2 - direction * size, y2 - size / 2),
        (x2 - direction * size, y2 + size / 2),
    ]
    draw.polygon(pts, fill="black")


def draw_activation(draw, x, y, height=56):
    draw.rectangle((x - 10, y - 18, x + 10, y + height), outline="black", fill="white", width=2)


def draw_sequence(spec):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # Outer UML frame.
    draw.rectangle((MARGIN, 78, W - MARGIN, H - 78), outline="black", width=3)
    title_w = text_size(draw, f"sd {spec['title']}", F_TITLE)[0]
    tab_w = min(W - (2 * MARGIN) - 160, title_w + 92)
    draw.rectangle((MARGIN, 78, MARGIN + tab_w, 134), outline="black", fill="white", width=3)
    draw.line((MARGIN + tab_w, 134, MARGIN + tab_w + 34, 78), fill="black", width=3)
    draw.text((MARGIN + 18, 91), f"sd {spec['title']}", font=F_TITLE, fill="black")

    parts = spec["participants"]
    usable_w = W - 2 * MARGIN - 120
    step = usable_w / (len(parts) - 1)
    xs = [MARGIN + 60 + i * step for i in range(len(parts))]

    # Participant boxes and lifelines.
    for x, label in zip(xs, parts):
        box_w = max(250, min(365, text_size(draw, label, F_HEAD)[0] + 80))
        draw.rectangle((x - box_w / 2 + 16, TOP + 16, x + box_w / 2 + 16, TOP + BOX_H + 16),
                       fill=(235, 235, 235), outline=None)
        draw.rectangle((x - box_w / 2, TOP, x + box_w / 2, TOP + BOX_H),
                       outline="black", fill="white", width=3)
        draw_centered_multiline(draw, x, TOP + BOX_H / 2, label, F_HEAD, box_w - 24)

        y = LIFE_TOP + 10
        while y < LIFE_BOTTOM:
            draw.line((x, y, x, min(y + 18, LIFE_BOTTOM)), fill="black", width=2)
            y += 34

    def label_message(msg_text, x1, x2, y, dashed=False):
        max_w = abs(x2 - x1) - 30
        if max_w < 260:
            max_w = 420
        lines = wrap_text(draw, msg_text, F_MSG, max_w)
        line_h = text_size(draw, "Ag", F_MSG)[1] + 6
        tx = min(x1, x2) + 22
        if x2 < x1:
            tx = min(x1, x2) + 36
        for j, line in enumerate(lines):
            draw.text((tx, y - 38 - (len(lines) - 1) * line_h + j * line_h),
                      line, font=F_MSG, fill="black")

    y = LIFE_TOP + 78
    dy = spec.get("dy", 108)
    for msg in spec["messages"]:
        src, dst, text = msg["from"], msg["to"], msg["text"]
        dashed = msg.get("return", False)
        x1, x2 = xs[src], xs[dst]
        label_message(text, x1, x2, y, dashed)
        arrow(draw, x1, y, x2, y, dashed=dashed)
        draw_activation(draw, x2, y)
        y += dy

    if spec.get("alt"):
        alt_top = y - 25
        alt_bottom = min(LIFE_BOTTOM - 18, alt_top + 250)
        draw.rectangle((MARGIN + 40, alt_top, W - MARGIN - 40, alt_bottom),
                       outline="black", width=3)
        draw.text((MARGIN + 66, alt_top + 30), spec["alt"]["title"], font=F_ALT, fill="black")
        ay = alt_top + 108
        for msg in spec["alt"]["messages"]:
            src, dst, text = msg["from"], msg["to"], msg["text"]
            x1, x2 = xs[src], xs[dst]
            label_message(text, x1, x2, ay, msg.get("return", False))
            arrow(draw, x1, ay, x2, ay, dashed=msg.get("return", False))
            draw_activation(draw, x2, ay)
            ay += 82

    img.save(OUT_DIR / f"{spec['file']}.png", dpi=(300, 300))


DIAGRAMS = [
    {
        "file": "fig_seq_cu01_registrar_usuario",
        "title": "CU1: Registrar usuario",
        "participants": ["Usuario", "Interfaz Streamlit", "Servicio de usuarios", "PostgreSQL", "Servicio de correo"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: selecciona perfil e ingresa datos"},
            {"from": 1, "to": 2, "text": "2: enviar_formulario(datos)"},
            {"from": 2, "to": 2, "text": "3: validar dominio IPN y contraseña"},
            {"from": 2, "to": 3, "text": "4: buscar_correo(correo)"},
            {"from": 3, "to": 2, "text": "5: correo no registrado", "return": True},
            {"from": 2, "to": 3, "text": "6: crear_usuario(is_verified=false, otp)"},
            {"from": 2, "to": 4, "text": "7: enviar_codigo_otp(correo)"},
            {"from": 1, "to": 0, "text": "8: mns1 codigo enviado", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "5a: correo existente", "return": True},
                {"from": 1, "to": 0, "text": "6a: mns2 usuario ya existe / mns3 dominio invalido", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu02_iniciar_sesion",
        "title": "CU2: Iniciar sesión",
        "participants": ["Usuario", "Interfaz Streamlit", "Servicio de autenticación", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: ingresa correo y contraseña"},
            {"from": 1, "to": 2, "text": "2: autenticar(credenciales)"},
            {"from": 2, "to": 3, "text": "3: consultar usuario activo"},
            {"from": 3, "to": 2, "text": "4: usuario activo + hash", "return": True},
            {"from": 2, "to": 2, "text": "5: comparar hash bcrypt"},
            {"from": 2, "to": 3, "text": "6: registrar evento en security_audit_log"},
            {"from": 1, "to": 0, "text": "7: mns1 redirige a pantalla principal", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "4a: usuario inexistente/inactivo o contraseña incorrecta", "return": True},
                {"from": 1, "to": 0, "text": "5a: mns2 o mns3; registrar intento fallido", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu03_gestionar_tratamientos",
        "title": "CU3: Gestionar tratamientos",
        "participants": ["Usuario", "Modulo de ingesta", "Servicio de tratamientos", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: abre gestion de tratamientos"},
            {"from": 1, "to": 2, "text": "2: solicitar catalogo activo"},
            {"from": 2, "to": 3, "text": "3: consultar treatments"},
            {"from": 3, "to": 1, "text": "4: mostrar catalogo", "return": True},
            {"from": 0, "to": 1, "text": "5: captura nombre y descripcion"},
            {"from": 1, "to": 2, "text": "6: anadir_tratamiento(datos)"},
            {"from": 2, "to": 3, "text": "7: verificar duplicado e insertar"},
            {"from": 1, "to": 0, "text": "8: mns1 tratamiento añadido", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "7a: tratamiento duplicado o en uso", "return": True},
                {"from": 1, "to": 0, "text": "8a: mns2 duplicado / mns4 desactivado", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu04_registrar_experimento",
        "title": "CU4: Registrar experimento",
        "participants": ["Usuario", "Modulo de ingesta", "Servicio de experimentos", "Sistema de archivos", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: captura rat_id, tratamiento, fecha y responsable"},
            {"from": 0, "to": 1, "text": "2: carga video experimental"},
            {"from": 1, "to": 2, "text": "3: registrar_experimento(metadata, video)"},
            {"from": 2, "to": 2, "text": "4: validar datos obligatorios"},
            {"from": 2, "to": 3, "text": "5: almacenar video con nombre normalizado"},
            {"from": 2, "to": 4, "text": "6: insertar registro en experiments"},
            {"from": 1, "to": 0, "text": "7: mns1 experimento registrado", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 2, "to": 1, "text": "4a: falta video o rat_id obligatorio", "return": True},
                {"from": 1, "to": 0, "text": "5a: mns2 sin video / mns3 rat_id obligatorio", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu05_configurar_rois",
        "title": "CU5: Configurar ROIs",
        "participants": ["Usuario", "Editor de ROIs", "Servicio de ROIs", "PostgreSQL", "Archivo zonas_activas.json"],
        "messages": [
            {"from": 1, "to": 2, "text": "1: solicitar video activo"},
            {"from": 2, "to": 3, "text": "2: consultar experimento y video"},
            {"from": 3, "to": 1, "text": "3: fotograma representativo", "return": True},
            {"from": 0, "to": 1, "text": "4: traza brazos, centro y paredes"},
            {"from": 0, "to": 1, "text": "5: oprime Guardar zonas"},
            {"from": 1, "to": 2, "text": "6: guardar_rois(coordenadas)"},
            {"from": 2, "to": 3, "text": "7: persistir roi_configurations"},
            {"from": 2, "to": 4, "text": "8: escribir zonas activas e importar paredes"},
            {"from": 1, "to": 0, "text": "9: mns1 y mns2 zonas guardadas", "return": True},
        ],
        "dy": 82,
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "2a: no existe video activo", "return": True},
                {"from": 1, "to": 0, "text": "3a: mns3 registrar o seleccionar experimento", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu06_ejecutar_analisis",
        "title": "CU6: Ejecutar análisis de video",
        "participants": ["Usuario", "Interfaz Streamlit", "Motor de análisis", "YOLO-Pose", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: selecciona experimento"},
            {"from": 1, "to": 2, "text": "2: iniciar_analisis(experimento)"},
            {"from": 2, "to": 4, "text": "3: cargar ROI y ruta de video"},
            {"from": 2, "to": 3, "text": "4: detectar keypoints por frame"},
            {"from": 3, "to": 2, "text": "5: keypoints y centroide", "return": True},
            {"from": 2, "to": 2, "text": "6: calcular trayectoria, distancias y zonas"},
            {"from": 2, "to": 4, "text": "7: guardar analysis_results y processed=true"},
            {"from": 1, "to": 0, "text": "8: mns1 trayectoria y heatmaps disponibles", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 4, "to": 2, "text": "3a: video inexistente o ROI invalido", "return": True},
                {"from": 1, "to": 0, "text": "4a: mns2 archivo dañado / mns3 ROI no válido", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu07_agrupar_comportamientos",
        "title": "CU7: Agrupar comportamientos",
        "participants": ["Usuario", "Interfaz Streamlit", "Motor conductual", "Modelos RF/LSTM", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: solicita clasificacion del experimento"},
            {"from": 1, "to": 2, "text": "2: clasificar_comportamientos(experimento)"},
            {"from": 2, "to": 4, "text": "3: obtener caracteristicas por frame"},
            {"from": 2, "to": 3, "text": "4: predecir Grooming y Thigmotaxis"},
            {"from": 3, "to": 2, "text": "5: probabilidades por frame", "return": True},
            {"from": 2, "to": 2, "text": "6: aplicar rescate LSTM, suavizado y umbrales"},
            {"from": 2, "to": 4, "text": "7: guardar eventos y tiempos acumulados"},
            {"from": 1, "to": 0, "text": "8: mns1 clasificacion completada", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 4, "to": 2, "text": "3a: no hay caracteristicas disponibles", "return": True},
                {"from": 1, "to": 0, "text": "4a: mns2 detener clasificacion", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu08_editar_tiempos",
        "title": "CU8: Editar tiempos conductuales",
        "participants": ["Investigador/Admin", "Panel de resultados", "Servicio de auditoría", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: abre detalle de experimento analizado"},
            {"from": 0, "to": 1, "text": "2: activa modo edicion y modifica tiempos"},
            {"from": 0, "to": 1, "text": "3: escribe motivo y guarda"},
            {"from": 1, "to": 2, "text": "4: actualizar_tiempos(datos, motivo)"},
            {"from": 2, "to": 3, "text": "5: validar permiso y obtener snapshot previo"},
            {"from": 2, "to": 3, "text": "6: actualizar analysis_results"},
            {"from": 2, "to": 3, "text": "7: insertar behavior_edits before/after"},
            {"from": 1, "to": 0, "text": "8: mns1 tiempos actualizados", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 2, "to": 1, "text": "5a: motivo vacio o permiso insuficiente", "return": True},
                {"from": 1, "to": 0, "text": "6a: mns2 motivo obligatorio / mns3 sin permiso", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu09_exportar_resultados",
        "title": "CU9: Exportar resultados",
        "participants": ["Usuario", "Panel de resultados", "Servicio de reportes", "PostgreSQL", "Archivo Excel/PDF"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: consulta experimento o comparacion"},
            {"from": 0, "to": 1, "text": "2: selecciona formato Excel o PDF"},
            {"from": 0, "to": 1, "text": "3: oprime Descargar"},
            {"from": 1, "to": 2, "text": "4: generar_reporte(seleccion, formato)"},
            {"from": 2, "to": 3, "text": "5: consultar analysis_results"},
            {"from": 2, "to": 4, "text": "6: construir archivo descargable"},
            {"from": 1, "to": 0, "text": "7: mns1 entregar descarga", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "5a: no hay resultados disponibles", "return": True},
                {"from": 1, "to": 0, "text": "6a: mns2 no se genera archivo", "return": True},
            ],
        },
    },
    {
        "file": "fig_seq_cu10_bitacora_auditoria",
        "title": "CU10: Consultar bitácora de auditoría",
        "participants": ["Usuario", "Panel de auditoría", "Servicio de auditoría", "PostgreSQL"],
        "messages": [
            {"from": 0, "to": 1, "text": "1: abre historial de experimento o panel de auditoría"},
            {"from": 1, "to": 2, "text": "2: solicitar_registros(filtro, rol)"},
            {"from": 2, "to": 2, "text": "3: validar alcance segun rol"},
            {"from": 2, "to": 3, "text": "4: consultar behavior_edits o security_audit_log"},
            {"from": 3, "to": 2, "text": "5: registros cronologicos", "return": True},
            {"from": 2, "to": 1, "text": "6: preparar vista de solo lectura", "return": True},
            {"from": 1, "to": 0, "text": "7: mostrar autor, rol, fecha y detalle", "return": True},
        ],
        "alt": {
            "title": "Trayectoria alternativa",
            "messages": [
                {"from": 3, "to": 2, "text": "5a: sin registros para el filtro", "return": True},
                {"from": 1, "to": 0, "text": "6a: mns1 no existen registros", "return": True},
            ],
        },
    },
]


def main():
    for spec in DIAGRAMS:
        draw_sequence(spec)
    print(f"Diagramas generados en: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
