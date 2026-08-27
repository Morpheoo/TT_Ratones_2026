from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path("reportes/figuras/codigo_54")
OUT_DIR.mkdir(parents=True, exist_ok=True)


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
F_BOX = font(25, True)
F_TEXT = font(19)
F_SMALL = font(18)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, fnt, width):
    lines = []
    cur = ""
    for word in text.split():
        test = word if not cur else f"{cur} {word}"
        if text_size(draw, test, fnt)[0] <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, xy, text, fnt, width, fill=(0, 0, 0), line_gap=6):
    x, y = xy
    for line in wrap(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_size(draw, "Ag", fnt)[1] + line_gap
    return y


def box(draw, x, y, w, h, title, body=None, fill=(255, 255, 255), outline=(0, 0, 0)):
    draw.rectangle((x + 12, y + 12, x + w + 12, y + h + 12), fill=(228, 228, 228))
    draw.rectangle((x, y, x + w, y + h), fill=fill, outline=outline, width=3)
    draw.text((x + 18, y + 14), title, font=F_BOX, fill=(0, 0, 0))
    draw.line((x, y + 52, x + w, y + 52), fill=outline, width=2)
    if body:
        cy = y + 68
        for item in body:
            cy = draw_wrapped(draw, (x + 18, cy), item, F_TEXT, w - 36)
            cy += 3


def arrow(draw, start, end, label=None):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=(0, 0, 0), width=3)
    dx = 1 if x2 >= x1 else -1
    dy = 1 if y2 >= y1 else -1
    if abs(x2 - x1) >= abs(y2 - y1):
        pts = [(x2, y2), (x2 - dx * 16, y2 - 8), (x2 - dx * 16, y2 + 8)]
    else:
        pts = [(x2, y2), (x2 - 8, y2 - dy * 16), (x2 + 8, y2 - dy * 16)]
    draw.polygon(pts, fill=(0, 0, 0))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        draw.rectangle((mx - 8, my - 16, mx + text_size(draw, label, F_SMALL)[0] + 8, my + 12), fill="white")
        draw.text((mx, my - 14), label, font=F_SMALL, fill=(0, 0, 0))


def generate_module_diagram():
    W, H = 2400, 1550
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((70, 70, W - 70, H - 70), outline="black", width=3)
    draw.text((95, 95), "Diagrama de módulos de código del prototipo", font=F_TITLE, fill="black")

    # Columns.
    x_ui, x_srv, x_db = 120, 900, 1680
    w = 610

    box(draw, x_ui, 180, w, 285, "Interfaz Streamlit", [
        "Home.py",
        "pages/00_Login.py",
        "pages/01_Ingesta_de_Video.py",
        "pages/03_Configuracion_Zonas.py",
        "pages/04_Analisis_Final.py",
        "pages/05_Resultados_y_Estadisticas.py",
        "pages/99_Admin_Panel.py",
    ], fill=(247, 251, 255))

    box(draw, x_srv, 180, w, 285, "Servicios de aplicación", [
        "src/auth.py: registro, OTP, login y roles",
        "src/treatments.py: catálogo de tratamientos",
        "src/db/experiment_history.py: experimentos y ROIs",
        "src/db/behavior_edits.py: auditoría de ediciones",
        "src/security_logger.py: bitácora de seguridad",
    ], fill=(247, 255, 249))

    box(draw, x_db, 180, w, 285, "Persistencia", [
        "src/db/connection.py",
        "schema.sql",
        "PostgreSQL",
        "Archivos auxiliares: zonas_activas.json, videos y salidas del pipeline",
    ], fill=(255, 250, 243))

    box(draw, x_ui, 590, w, 230, "Configuración experimental", [
        "Ingesta de video",
        "Gestión de tratamientos",
        "Registro de experimento",
        "Trazado de ROIs en EPM",
    ], fill=(247, 251, 255))

    box(draw, x_srv, 590, w, 230, "Integración con SimBA", [
        "src/simba_roi_bridge.py",
        "Sincronización de paredes y zonas",
        "Conversión de ROIs de Streamlit al proyecto SimBA",
    ], fill=(247, 255, 249))

    box(draw, x_db, 590, w, 230, "Datos experimentales", [
        "experiments",
        "treatments",
        "roi_configurations",
        "analysis_results",
    ], fill=(255, 250, 243))

    box(draw, x_ui, 960, w, 250, "Análisis y resultados", [
        "pages/04_Analisis_Final.py",
        "src/scripts/full_pipeline.py",
        "YOLO-Pose, SimBA RF, LSTM",
        "pages/05_Resultados_y_Estadisticas.py",
    ], fill=(247, 251, 255))

    box(draw, x_srv, 960, w, 250, "Auditoría y exportación", [
        "Edición manual de tiempos",
        "Snapshots before/after",
        "Exportación CSV, JSON y PDF",
        "Eventos de seguridad",
    ], fill=(247, 255, 249))

    box(draw, x_db, 960, w, 250, "Trazabilidad", [
        "behavior_edits",
        "security_audit_log",
        "logs/security.log",
        "Llaves foráneas a users y experiments",
    ], fill=(255, 250, 243))

    arrow(draw, (730, 300), (900, 300), "llama")
    arrow(draw, (1510, 300), (1680, 300), "SQL")
    arrow(draw, (730, 710), (900, 710), "sincroniza")
    arrow(draw, (1510, 710), (1680, 710), "persiste")
    arrow(draw, (730, 1080), (900, 1080), "procesa")
    arrow(draw, (1510, 1080), (1680, 1080), "audita")
    arrow(draw, (2060, 820), (2060, 960), "resultados")

    draw.text((95, H - 125),
              "Fuente: inspección de Home.py, pages/, src/, src/db/ y schema.sql.",
              font=F_SMALL, fill=(0, 0, 0))
    img.save(OUT_DIR / "fig54_diagrama_modulos_codigo.png", dpi=(300, 300))


def erd_table(draw, x, y, w, title, fields, fill):
    row_h = 33
    h = 58 + row_h * len(fields)
    draw.rectangle((x + 10, y + 10, x + w + 10, y + h + 10), fill=(228, 228, 228))
    draw.rectangle((x, y, x + w, y + h), fill=fill, outline="black", width=3)
    draw.rectangle((x, y, x + w, y + 52), fill=(235, 241, 247), outline="black", width=3)
    draw.text((x + 14, y + 12), title, font=F_BOX, fill="black")
    cy = y + 62
    for field in fields:
        draw.text((x + 14, cy), field, font=F_SMALL, fill="black")
        cy += row_h
    return h


def generate_erd():
    W, H = 2600, 1800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((70, 70, W - 70, H - 70), outline="black", width=3)
    draw.text((95, 95), "Modelo entidad-relación del prototipo", font=F_TITLE, fill="black")

    tables = {
        "users": (120, 180, [
            "PK id SERIAL",
            "username VARCHAR UNIQUE",
            "password_hash TEXT",
            "role VARCHAR",
            "is_verified BOOLEAN",
            "verification_code VARCHAR(6)",
            "verification_code_created_at TIMESTAMP",
            "is_active BOOLEAN",
            "full_name VARCHAR",
            "accepted_terms BOOLEAN",
            "boleta/carrera/escuela",
            "num_empleado/area/centro",
            "created_at TIMESTAMP",
        ]),
        "treatments": (940, 180, [
            "PK id SERIAL",
            "name VARCHAR UNIQUE",
            "description TEXT",
            "FK created_by -> users.id",
            "created_at TIMESTAMP",
            "is_active BOOLEAN",
        ]),
        "experiments": (940, 560, [
            "PK id SERIAL",
            "rat_id VARCHAR",
            "treatment VARCHAR",
            "experiment_date DATE",
            "responsible VARCHAR",
            "video_path TEXT",
            "duration_seconds FLOAT",
            "FK created_by -> users.id",
            "processed BOOLEAN",
            "created_at TIMESTAMP",
        ]),
        "roi_configurations": (1760, 560, [
            "PK id SERIAL",
            "FK experiment_id -> experiments.id",
            "zone_type VARCHAR",
            "coordinates_json JSONB",
            "scale_factor FLOAT",
        ]),
        "analysis_results": (940, 1060, [
            "PK id SERIAL",
            "FK experiment_id -> experiments.id",
            "timestamp TIMESTAMP",
            "total_distance FLOAT",
            "time_open_arms FLOAT",
            "time_closed_arms FLOAT",
            "time_center FLOAT",
            "head_dips_count INTEGER",
            "rearing_count INTEGER",
            "grooming_duration FLOAT",
            "thigmotaxis_duration FLOAT",
            "status VARCHAR",
            "trajectory_path TEXT*",
        ]),
        "behavior_edits": (1760, 1060, [
            "PK id SERIAL",
            "FK experiment_id -> experiments.id",
            "FK edited_by -> users.id",
            "edited_by_email TEXT",
            "edited_role TEXT",
            "edited_at TIMESTAMP",
            "before_open/closed/center FLOAT",
            "before_grooming/thigmo FLOAT",
            "after_open/closed/center FLOAT",
            "after_grooming/thigmo FLOAT",
            "note TEXT",
        ]),
        "security_audit_log": (120, 1060, [
            "PK id SERIAL",
            "timestamp TIMESTAMP",
            "event_type VARCHAR",
            "username VARCHAR",
            "ip_address VARCHAR",
            "success BOOLEAN",
            "message TEXT",
            "level VARCHAR",
        ]),
    }

    dims = {}
    for name, (x, y, fields) in tables.items():
        dims[name] = (x, y, 620, erd_table(draw, x, y, 620, name, fields, (255, 255, 255)))

    def center(name, side):
        x, y, w, h = dims[name]
        if side == "right":
            return x + w, y + h / 2
        if side == "left":
            return x, y + h / 2
        if side == "bottom":
            return x + w / 2, y + h
        return x + w / 2, y

    arrow(draw, center("users", "right"), center("treatments", "left"))
    arrow(draw, (740, 565), (940, 720))
    arrow(draw, center("experiments", "right"), center("roi_configurations", "left"), "1:N")
    arrow(draw, center("experiments", "bottom"), center("analysis_results", "top"), "1:N")
    arrow(draw, center("experiments", "right"), center("behavior_edits", "left"), "1:N")

    draw.text((95, H - 150),
              "* trajectory_path se agrega por migración/ensure_analysis_results_schema en la página de resultados.",
              font=F_SMALL, fill=(0, 0, 0))
    draw.text((95, H - 115),
              "Fuente: schema.sql, src/db/migrations/add_behavior_edits.py y pages/05_Resultados_y_Estadisticas.py.",
              font=F_SMALL, fill=(0, 0, 0))
    img.save(OUT_DIR / "fig54_modelo_entidad_relacion.png", dpi=(300, 300))


def main():
    generate_module_diagram()
    generate_erd()
    print(f"Diagramas generados en: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
