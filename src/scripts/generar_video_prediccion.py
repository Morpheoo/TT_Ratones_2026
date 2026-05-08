import pandas as pd
import os, sys, shutil
print("\n" + "="*40)
print("GENERADOR DE VIDEO MULTIMODAL v2.1 [FORCE_NEW]")
print("="*40)
import pickle
import cv2
import os
import argparse
import math
import numpy as np
import json

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
YOLO_MODEL_PATH = os.path.join(PROJECT_DIR, "yolo_tracker.pt")
TRACKING_CONFIDENCE_MIN = 0.25
TRACKING_DOT_COLOR = (190, 70, 210)  # BGR morado, visible sobre rata blanca sin invadir.
TRACKING_DOT_OUTLINE_COLOR = (250, 220, 255)
THIGMO_CONFIRM_THRESHOLD = 0.30
THIGMO_POSSIBLE_THRESHOLD = 0.25
THIGMO_MIN_EVENT_SECONDS = 0.50
GROOMING_CONFIRM_THRESHOLD = 0.41
GROOMING_POSSIBLE_THRESHOLD = 0.30
GROOMING_MIN_EVENT_SECONDS = 0.50
BEHAVIOR_SMOOTHING_FRAMES = 15
SIMBA_MODELS_DIR = os.path.join(
    PROJECT_DIR,
    "data",
    "simba_projects",
    "New folder",
    "thigmotaxis_optimizado",
    "models",
)
GENERATED_MODELS_DIR = os.path.join(SIMBA_MODELS_DIR, "generated_models")
VALIDATION_MODELS_DIR = os.path.join(SIMBA_MODELS_DIR, "validations")


def safe_print(*args, sep=" ", end="\n", file=None, flush=False):
    """
    Evita que la consola de Windows falle si stdout usa cp1252 y el texto trae emojis
    u otros caracteres no representables.
    """
    target = sys.stdout if file is None else file
    text = sep.join(str(arg) for arg in args) + end

    try:
        target.write(text)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "utf-8"
        fallback_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        target.write(fallback_text)

    if flush:
        target.flush()


print = safe_print


def get_yolo_class():
    """Carga Ultralytics solo cuando realmente se necesita."""
    try:
        from ultralytics import YOLO
        return YOLO
    except ModuleNotFoundError as exc:
        suggested_python = os.path.join(PROJECT_DIR, "venv_311", "Scripts", "python.exe")
        print("[ENV] ERROR: No se encontro el modulo 'ultralytics' en este interprete.")
        print(f"[ENV] Python actual: {sys.executable}")
        if os.path.exists(suggested_python):
            print(f"[ENV] Sugerencia: ejecuta este script con: {suggested_python}")
        raise SystemExit(2) from exc


def resolve_behavior_model(requested_path: str, generated_name: str, fallback_names: list[str]) -> str:
    """
    Respeta primero el modelo pedido por el pipeline.
    Esto evita mezclar modelos DLC con features YOLO cuando el backend activo es YOLO Pose.
    """
    candidate_paths = []
    if requested_path:
        candidate_paths.append(requested_path)
    candidate_paths.append(os.path.join(GENERATED_MODELS_DIR, generated_name))
    for fallback_name in fallback_names:
        candidate_paths.append(os.path.join(VALIDATION_MODELS_DIR, fallback_name))

    seen: set[str] = set()
    for candidate_path in candidate_paths:
        normalized = os.path.abspath(candidate_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.exists(normalized):
            return normalized

    return os.path.abspath(requested_path) if requested_path else ""

def format_time(seconds: float) -> str:
    """Convierte segundos a formato MM:SS.ss"""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"

def select_maze_rois(video_path: str):
    """
    Selector de ROIs Avanzado (Usando cv2.selectROI nativo):
    - Permite dibujar, redimensionar y mover la caja.
    - Presionar ENTER o ESPACIO para confirmar la ROI actual.
    """
    cap = cv2.VideoCapture(video_path)
    ret, frame_orig = cap.read()
    cap.release()
    if not ret: return None

    # Configuración de categorías
    categorias = [
        {"id": "Norte (Abierto)", "color": (120, 120, 240)}, # Coral
        {"id": "Sur (Abierto)",   "color": (120, 120, 240)},
        {"id": "Este (Cerrado)",  "color": (255, 250, 0)},   # Cyan
        {"id": "Oeste (Cerrado)", "color": (255, 250, 0)},
        {"id": "Centro",          "color": (0, 165, 255)},   # Naranja
    ]
    
    rois_finished = {}
    current_cat_idx = 0
    
    print("\n" + "="*50)
    print("INSTRUCCIONES DE SELECCIÓN DE ZONAS (NUEVO MOTOR)")
    print("1. Dibuja un rectángulo con el mouse.")
    print("2. Puedes arrastrar los bordes para redimensionar la caja.")
    print("3. Puedes hacer clic en el centro para mover la caja entera.")
    print("4. Presiona ENTER o ESPACIO cuando esté perfecta para pasar a la siguiente.")
    print("5. Presiona 'c' para cancelar todo.")
    print("="*50 + "\n")

    while current_cat_idx < len(categorias):
        cat_actual = categorias[current_cat_idx]
        
        # Preparar el canvas con las zonas anteriores dibujadas para contexto
        canvas = frame_orig.copy()
        for name, r in rois_finished.items():
            color = next(c["color"] for c in categorias if c["id"] == name)
            cv2.rectangle(canvas, (r[0], r[1]), (r[0]+r[2], r[1]+r[3]), color, 2)
            cv2.putText(canvas, name, (r[0], max(0, r[1]-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Instrucción visual grande
        cv2.putText(canvas, f"SELECCIONA: {cat_actual['id']} (Usa el mouse y presiona ENTER)", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # El popup interactivo mágico de OpenCV
        roi = cv2.selectROI(f"Ajuste Fino de ROI - {cat_actual['id']}", canvas, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(f"Ajuste Fino de ROI - {cat_actual['id']}")
        
        # Si x,y,w,h son todos 0, significa que canceló (presionó c o esc)
        if roi == (0, 0, 0, 0):
            print("Selección cancelada por el usuario.")
            return None
            
        rois_finished[cat_actual['id']] = roi
        current_cat_idx += 1

    return rois_finished, categorias

def is_point_in_roi(px, py, roi):
    """Verifica si un punto (px, py) cae dentro de una tupla OpenCV ROI (x, y, w, h)."""
    x, y, w, h = roi
    return x <= px <= x + w and y <= py <= y + h

def load_simba_model(model_path: str):
    """Carga el modelo de Machine Learning entrenado por SimBA."""
    print(f"Cargando modelo clasificador desde: {model_path}")
    import warnings
    # Filtrar warnings de version de sklearn que interfieren con la consola
    warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
    with open(model_path, 'rb') as f:
        clf = pickle.load(f)
    # Evita problemas de joblib/thread pools en Windows y hace el renderer reproducible.
    if hasattr(clf, "n_jobs"):
        try:
            clf.n_jobs = 1
        except Exception:
            pass
    if hasattr(clf, "verbose"):
        try:
            clf.verbose = 0
        except Exception:
            pass
    return clf

def load_and_clean_features(df_master, clf):
    """
    Recorta las columnas para que empaten exactamente con las variables que 
    espera el modelo predictivo individual.
    """
    df_reducido = df_master.copy()
    try:
        expected_feats = list(clf.feature_names_in_)
        missing_feats = [f for f in expected_feats if f not in df_reducido.columns]
        
        if len(missing_feats) > 0:
            print(f"[MODEL] Advertencia: Faltan {len(missing_feats)} características. Se usará 0.0.")
            # Crear un dataframe con ceros para las faltantes y concatenar
            df_missing = pd.DataFrame(0.0, index=df_reducido.index, columns=missing_feats)
            df_reducido = pd.concat([df_reducido, df_missing], axis=1)
        else:
            print(f"[MODEL] Éxito: Todas las {len(expected_feats)} características encontradas.")
            
        df_reducido = df_reducido[expected_feats]
    except AttributeError:
        print("[MODEL] El modelo no tiene atributo feature_names_in_. Se usará el dataframe tal cual.")
    return df_reducido


def _resolve_tracking_columns(df: pd.DataFrame) -> tuple[str, str, str | None, str] | None:
    """
    Devuelve las columnas de pose que representan el centro corporal para tracking.
    En el backend YOLO Pose, Center_x/Center_y viene del keypoint `torso`.
    """
    lookup = {str(column).lower(): str(column) for column in df.columns}
    candidates = [
        ("Center_x", "Center_y", ["Center_p", "Center_likelihood"], "Center/torso"),
        ("torso_x", "torso_y", ["torso_p", "torso_likelihood"], "torso"),
        ("mouse_center_x", "mouse_center_y", ["mouse_center_p", "mouse_center_likelihood"], "mouse_center"),
    ]

    for x_name, y_name, p_names, label in candidates:
        x_col = lookup.get(x_name.lower())
        y_col = lookup.get(y_name.lower())
        if not x_col or not y_col:
            continue
        p_col = next((lookup.get(p_name.lower()) for p_name in p_names if lookup.get(p_name.lower())), None)
        return x_col, y_col, p_col, label
    return None


def build_pose_tracking(df_master: pd.DataFrame) -> dict[str, object] | None:
    """
    Construye una trayectoria desde la pose ya calculada.
    Para YOLO Pose, el bridge mapea `torso` -> `Center`, por eso este punto
    reemplaza al centro del bbox del tracker YOLO antiguo.
    """
    resolved = _resolve_tracking_columns(df_master)
    if resolved is None:
        print("[TRACKING] No se encontraron columnas de centro corporal en features. Se usara fallback bbox YOLO.")
        return None

    x_col, y_col, p_col, label = resolved
    x_values = pd.to_numeric(df_master[x_col], errors="coerce").astype(float)
    y_values = pd.to_numeric(df_master[y_col], errors="coerce").astype(float)
    valid = np.isfinite(x_values) & np.isfinite(y_values) & ~((x_values == 0) & (y_values == 0))

    if p_col:
        p_values = pd.to_numeric(df_master[p_col], errors="coerce").astype(float)
        valid = valid & np.isfinite(p_values) & (p_values >= TRACKING_CONFIDENCE_MIN)

    valid_count = int(valid.sum())
    total_count = int(len(df_master))
    if valid_count == 0:
        print(f"[TRACKING] Columnas {x_col}/{y_col} encontradas, pero sin frames validos. Se usara fallback bbox YOLO.")
        return None

    tracking_df = pd.DataFrame({"x": x_values.where(valid), "y": y_values.where(valid)})
    tracking_df = tracking_df.interpolate(method="linear", limit=15, limit_direction="both")
    interpolated_valid = np.isfinite(tracking_df["x"]) & np.isfinite(tracking_df["y"])

    print(
        f"[TRACKING] Usando pose para tracking: {label} ({x_col}, {y_col}) | "
        f"{valid_count}/{total_count} frames validos"
    )
    if p_col:
        print(f"[TRACKING] Umbral de confianza {p_col}: >= {TRACKING_CONFIDENCE_MIN}")

    return {
        "x": tracking_df["x"].to_numpy(dtype=float),
        "y": tracking_df["y"].to_numpy(dtype=float),
        "valid": interpolated_valid.to_numpy(dtype=bool),
        "source": label,
    }


def get_yolo_bbox_center(frame, yolo_model):
    best_box = None
    yolo_results = yolo_model(frame, verbose=False)
    for box in yolo_results[0].boxes:
        if box.conf[0] > 0.35:
            if best_box is None or box.conf[0] > best_box.conf[0]:
                best_box = box

    if best_box is None:
        return None, None

    x1, y1, x2, y2 = map(int, best_box.xyxy[0])
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def draw_hud(frame, time_str, fps, width, height,
             # Datos Thigmotaxis
             thigmo_prob=0.0, thigmo_status="Normal", thigmo_color=(255,100,0), thigmo_acc=0.0, thigmo_events=[],
             # Datos Grooming
             groom_prob=0.0, groom_status="Normal", groom_color=(255,100,0), groom_acc=0.0, groom_events=[],
             # Datos Espaciales
             combined_timers={}, 
             # Globales
             thigmo_pred_status=0, groom_pred_status=0):
    
    overlay = frame.copy()
    
    # --- BLOQUE 1: THIGMOTAXIS (Superior Derecha) ---
    x_tr, y_tr, w_tr, h_tr = width - 420, 30, 390, 240
    cv2.rectangle(overlay, (x_tr, y_tr), (x_tr + w_tr, y_tr + h_tr), (30, 30, 30), -1)

    # --- BLOQUE 2: GROOMING (Superior Izquierda) ---
    x_tl, y_tl, w_tl, h_tl = 30, 30, 390, 240
    cv2.rectangle(overlay, (x_tl, y_tl), (x_tl + w_tl, y_tl + h_tl), (30, 30, 30), -1)

    # --- BLOQUE 3: BRAZOS EPM (Inferior Derecha) ---
    x_br, y_br, w_br, h_br = width - 330, height - 260, 305, 230
    cv2.rectangle(overlay, (x_br, y_br), (x_br + w_br, y_br + h_br), (20, 20, 20), -1)

    # Mezclamos los fondos con el frame (Opacidad del 90% para la caja)
    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

    # ================= PINTAR TEXTOS THIGMOTAXIS (Opacidad 100%) =================
    cv2.putText(frame, "DETECTOR DE THIGMOTAXIS", (x_tr + 15, y_tr + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, time_str, (x_tr + 280, y_tr + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Barra Progreso
    bar_x, bar_y, bar_w, bar_h = x_tr + 20, y_tr + 70, 300, 15
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * thigmo_prob), bar_y + bar_h), thigmo_color, -1)
    cv2.putText(frame, f"{int(thigmo_prob*100)}%", (bar_x + bar_w + 10, bar_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, thigmo_status, (x_tr + 20, y_tr + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, thigmo_color, 1)
    cv2.putText(frame, f"Acumulado Thigmo: {thigmo_acc:.1f}s", (x_tr + 20, y_tr + 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

    # Log Eventos
    evts_disp = thigmo_events[-3:]
    curr_y = y_tr + 150
    cv2.putText(frame, "Ultimos Eventos:", (x_tr + 20, curr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    curr_y += 20
    for ev_start, ev_end, _ in reversed(evts_disp):
        cv2.putText(frame, f"-> Thigmo: {format_time(ev_start)} a {format_time(ev_end)}", (x_tr + 30, curr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1)
        curr_y += 18


    # ================= PINTAR TEXTOS GROOMING (Opacidad 100%) =================
    cv2.putText(frame, "DETECTOR DE GROOMING", (x_tl + 15, y_tl + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, time_str, (x_tl + 280, y_tl + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Barra Progreso
    bar_x, bar_y, bar_w, bar_h = x_tl + 20, y_tl + 70, 300, 15
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * groom_prob), bar_y + bar_h), groom_color, -1)
    cv2.putText(frame, f"{int(groom_prob*100)}%", (bar_x + bar_w + 10, bar_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, groom_status, (x_tl + 20, y_tl + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, groom_color, 1)
    cv2.putText(frame, f"Acumulado Groom: {groom_acc:.1f}s", (x_tl + 20, y_tl + 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

    # Log Eventos
    evts_disp_g = groom_events[-3:]
    curr_y = y_tl + 150
    cv2.putText(frame, "Ultimos Eventos:", (x_tl + 20, curr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    curr_y += 20
    for ev_start, ev_end, _ in reversed(evts_disp_g):
        cv2.putText(frame, f"-> Groom: {format_time(ev_start)} a {format_time(ev_end)}", (x_tl + 30, curr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1)
        curr_y += 18


    # ================= PINTAR TEXTOS ESPACIALES =================
    cv2.putText(frame, "TIEMPOS POR BRAZO", (x_br + 15, y_br + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    curr_y = y_br + 70
    
    # Extraemos todos los nombres de las zonas dinámicamente
    for brazo, count in combined_timers.items():
        if "muro" in str(brazo).lower() or "pared" in str(brazo).lower():
            continue # No contar tiempo de permanencia en "muros" lógicos
            
        sec = count / fps
        cv2.putText(frame, f"{brazo}: {sec:.1f} s", (x_br + 25, curr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        curr_y += 30
    
    # Marco exterior de alerta si hay Thigmotaxis y Grooming
    if thigmo_pred_status == 2 and groom_pred_status == 2:
        # Si ocurren ambos (raro pero posible), pintamos marco multicolor/blanco
        cv2.rectangle(frame, (0,0), (width, height), (255,255,255), 8)
    elif thigmo_pred_status == 2:
        cv2.rectangle(frame, (0,0), (width, height), (0,0,255), 8) # Rojo
    elif groom_pred_status == 2:
        cv2.rectangle(frame, (0,0), (width, height), (255,0,255), 8) # Violeta
        
    return frame

def export_timelog(events, output_path, total_frames, current_start, behavior_name, fps):
    if current_start is not None:
        events.append((current_start, float(total_frames/fps), behavior_name)) 
        
    if events:
        log_path = output_path.replace(".mp4", f"_{behavior_name}_TIMELOG.csv")
        df_log = pd.DataFrame(events, columns=["Start_Second", "End_Second", "Type"])
        df_log["Start_MinSec"] = df_log["Start_Second"].apply(format_time)
        df_log["End_MinSec"] = df_log["End_Second"].apply(format_time)
        df_log["Duration_Seconds"] = df_log["End_Second"] - df_log["Start_Second"]
        df_log.to_csv(log_path, index=False)
        print(f"[OK] ¡Reporte científico guardado: {log_path}!")

def state_machine_update(
    prob_val,
    current_sec,
    frames_acc,
    events_list,
    current_start,
    is_confirming,
    umbral_confrm=0.35,
    umbral_posible=0.30,
    min_event_seconds=0.50,
):
    """
    Maquina de estados generalizada para un comportamiento.
    Maneja el paso de Ausente -> Posible -> Confirmado
    Retorna: status_text, bar_color, pred_status, frames_acc, events_list, current_start, is_confirming
    """
    if prob_val >= umbral_confrm: # UMBRAL DE CONFIRMACIÓN
        pred_status = 2 
        status_text = "Confirmado"
        bar_color = (0, 0, 255) # Rojo en BGR / O color fuerte
        frames_acc += 1
        
        if not is_confirming:
            if current_start is not None and (current_sec - current_start >= min_event_seconds):
                events_list.append((current_start, current_sec, "Confirmada"))
            current_start = current_sec
            is_confirming = True
            
    elif prob_val >= umbral_posible: # UMBRAL DE POSIBLE
        pred_status = 1 
        status_text = "Posible"
        bar_color = (0, 255, 255) # Amarillo/Naranja
        
        if is_confirming:
            if current_start is not None and (current_sec - current_start >= min_event_seconds):
                events_list.append((current_start, current_sec, "Confirmada"))
            current_start = current_sec
            is_confirming = False
    else: # NORMAL
        pred_status = 0 
        status_text = "Normal"
        bar_color = (255, 100, 0) # Azul
        
        if current_start is not None:
            if current_sec - current_start >= min_event_seconds:
                events_list.append((current_start, current_sec, "Confirmada" if is_confirming else "Posible"))
            current_start = None
            is_confirming = False
            
    return status_text, bar_color, pred_status, frames_acc, events_list, current_start, is_confirming

def generate_video(
    video_path: str,
    features_path: str,
    output_path: str,
    zonas_json_str: str = "",
    model_thigmo: str = "",
    model_grooming: str = "",
    thigmo_confirm_threshold: float = THIGMO_CONFIRM_THRESHOLD,
    thigmo_possible_threshold: float = THIGMO_POSSIBLE_THRESHOLD,
    thigmo_min_event_seconds: float = THIGMO_MIN_EVENT_SECONDS,
    grooming_confirm_threshold: float = GROOMING_CONFIRM_THRESHOLD,
    grooming_possible_threshold: float = GROOMING_POSSIBLE_THRESHOLD,
    grooming_min_event_seconds: float = GROOMING_MIN_EVENT_SECONDS,
    smoothing_frames: int = BEHAVIOR_SMOOTHING_FRAMES,
    lstm_grooming_csv: str = "",
    grooming_source: str = "rf",
    lstm_rescue_rf_threshold: float = 0.22,
    lstm_rescue_threshold: float = 0.11,
):
    import sys
    import os
    
    # Guardia defensiva: evita pd.read_csv('') que genera FileNotFoundError críptico
    if not features_path or not os.path.isfile(features_path):
        print(f"[FATAL] features_path inválido o inexistente: '{features_path}'")
        print("  → Primero extrae los keypoints en 02 · Keypoints para generar el CSV de features.")
        sys.exit(1)

    print("Cargando features maestras...")
    df_master = pd.read_csv(features_path)
    if 'Unnamed: 0' in df_master.columns:
        df_master = df_master.drop(columns=['Unnamed: 0'])

    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if src_path not in sys.path:
        sys.path.append(src_path)
    
    from src.analysis_logic import detectar_thigmotaxis, checar_zona

    # --- CARGA DE MODELOS MACHINE LEARNING (SimBA) ---
    print("\n[IA] Solicitud de Modelos entrenados (RF SimBA)...")
    model_thigmo = resolve_behavior_model(
        model_thigmo,
        "Thigmotaxis.sav",
        ["Thigmotaxis_3.sav", "Thigmotaxis_0.sav", "Thigmotaxis_2.sav"],
    )
    model_grooming = resolve_behavior_model(
        model_grooming,
        "Grooming.sav",
        ["Grooming_0.sav", "Grooming_1.sav", "Grooming_2.sav"],
    )

    if model_thigmo and os.path.exists(model_thigmo):
        print(f"[IA] Cargando modelo Thigmotaxis: {model_thigmo}")
        clf_thigmo = load_simba_model(model_thigmo)
        X_thigmo = load_and_clean_features(df_master, clf_thigmo)
        # Random Forest returns [prob_class0, prob_class1] usually
        preds = clf_thigmo.predict_proba(X_thigmo) if hasattr(clf_thigmo, "predict_proba") else None
        probs_thigmo = preds[:, 1] if preds is not None else clf_thigmo.predict(X_thigmo)
    else:
        print("[IA] Modelo de Thigmotaxis no encontrado. Se usará 0.0")
        probs_thigmo = np.zeros(len(df_master))

    if model_grooming and os.path.exists(model_grooming):
        print(f"[IA] Cargando modelo Grooming: {model_grooming}")
        clf_groom = load_simba_model(model_grooming)
        X_groom = load_and_clean_features(df_master, clf_groom)
        preds2 = clf_groom.predict_proba(X_groom) if hasattr(clf_groom, "predict_proba") else None
        probs_groom = preds2[:, 1] if preds2 is not None else clf_groom.predict(X_groom)
    else:
        print("[IA] Modelo de Grooming no encontrado. Se usará 0.0")
        probs_groom = np.zeros(len(df_master))

    if lstm_grooming_csv:
        if not os.path.exists(lstm_grooming_csv):
            raise FileNotFoundError(f"CSV LSTM Grooming no encontrado: {lstm_grooming_csv}")
        lstm_df = pd.read_csv(lstm_grooming_csv)
        if "Probability_Grooming_LSTM" not in lstm_df.columns:
            raise ValueError(f"El CSV LSTM no contiene Probability_Grooming_LSTM: {lstm_grooming_csv}")
        probs_lstm = lstm_df["Probability_Grooming_LSTM"].fillna(0.0).to_numpy()[: len(df_master)]
        if len(probs_lstm) < len(df_master):
            probs_lstm = np.pad(probs_lstm, (0, len(df_master) - len(probs_lstm)), mode="edge")
        grooming_source = grooming_source.lower().strip()
        if grooming_source == "lstm":
            probs_groom = probs_lstm
            print(f"[LSTM] Grooming reemplaza RF usando: {lstm_grooming_csv}")
        elif grooming_source == "ensemble":
            probs_groom = (np.asarray(probs_groom, dtype=float) + probs_lstm) / 2.0
            print(f"[LSTM] Grooming ensemble RF+LSTM usando: {lstm_grooming_csv}")
        elif grooming_source == "rescue":
            probs_rf = np.asarray(probs_groom, dtype=float)
            rescue_mask = (
                (probs_rf >= float(lstm_rescue_rf_threshold))
                & (probs_rf < float(grooming_confirm_threshold))
                & (probs_lstm >= float(lstm_rescue_threshold))
            )
            probs_groom = probs_rf.copy()
            probs_groom[rescue_mask] = np.maximum(probs_groom[rescue_mask], float(grooming_confirm_threshold))
            print(
                f"[LSTM] Grooming rescue RF+LSTM usando: {lstm_grooming_csv} | "
                f"frames_rescatados={int(rescue_mask.sum())} | "
                f"rf_floor={lstm_rescue_rf_threshold:.3f} | lstm_threshold={lstm_rescue_threshold:.3f}"
            )
        else:
            print("[LSTM] CSV cargado, pero grooming_source=rf; se mantiene RF.")

    # --- SUAVIZADO Y FILTROS (Moving Average) ---
    smoothing_frames = max(1, int(smoothing_frames))
    print("Suavizando probabilidades para evitar parpadeo de microsegundos...")
    print(
        "[CALIB] "
        f"Thigmo confirm={thigmo_confirm_threshold:.3f}, possible={thigmo_possible_threshold:.3f}, "
        f"min={thigmo_min_event_seconds:.2f}s | "
        f"Grooming confirm={grooming_confirm_threshold:.3f}, possible={grooming_possible_threshold:.3f}, "
        f"min={grooming_min_event_seconds:.2f}s | smoothing={smoothing_frames} frames"
    )
    # Thigmotaxis: filtro temporal. Evita alertas falsas breves.
    probs_thigmo = pd.Series(probs_thigmo).rolling(window=smoothing_frames, min_periods=1, center=True).mean().values
    
    # Grooming: Filtro de 15 frames (0.5s). 
    probs_groom = pd.Series(probs_groom).rolling(window=smoothing_frames, min_periods=1, center=True).mean().values

    # Pre-calcular el movimiento promedio de la nariz para evitar "falsos estáticos"
    if 'Movement_mouse_nose' in df_master.columns:
        mov_nose = pd.Series(df_master['Movement_mouse_nose'].values).rolling(window=smoothing_frames, min_periods=1, center=True).mean().values
    else:
        mov_nose = np.ones(len(probs_groom)) * 10.0 # Dummy fallback

    tracking_data = build_pose_tracking(df_master)

    # Preparamos los cronómetros de SimBA (por si acaso los queremos en el fondo)
    roi_cols = [c for c in df_master.columns if 'Center in zone' in c]
    zona_cols = [c for c in roi_cols if 'pared' not in c.lower()]
    roi_timers = {c.replace(' Animal_1 Center in zone', ''): 0 for c in zona_cols}

    # Interactividad ROIs o vía JSON
    if zonas_json_str and zonas_json_str.strip() != "":
        try:
            parsed_zones = json.loads(zonas_json_str)
            maze_rois = {}
            if isinstance(parsed_zones, list): # Streamlit usa una lista de dicts [{'name': 'Norte', 'x': 100, ...}] generamente
                for z in parsed_zones:
                    # Checamos si es formato web 'name', 'x', 'y', 'width', 'height'
                    name = z.get('name') or z.get('id') or z.get('Nombre Zona') or "Zona"
                    x = z.get('x') if z.get('x') is not None else z.get('left')
                    y = z.get('y') if z.get('y') is not None else z.get('top')
                    w = z.get('w') if z.get('w') is not None else z.get('width')
                    h = z.get('h') if z.get('h') is not None else z.get('height')
                    if all(v is not None for v in [x, y, w, h]):
                        maze_rois[name] = (int(x), int(y), int(w), int(h))
            elif isinstance(parsed_zones, dict): # Nuestro dict original de CV2 {'Norte': (x,y,w,h)}
                for k, v in parsed_zones.items():
                    if isinstance(v, (list, tuple)) and len(v) >= 4:
                        maze_rois[k] = (int(v[0]), int(v[1]), int(v[2]), int(v[3]))
            
            # Definir colores fijos que venian de select_maze_rois
            config_cats = [
                {"id": "Norte (Abierto)", "color": (120, 120, 240)}, # Coral
                {"id": "Sur (Abierto)",   "color": (120, 120, 240)},
                {"id": "Este (Cerrado)",  "color": (255, 250, 0)},   # Cyan
                {"id": "Oeste (Cerrado)", "color": (255, 250, 0)},
                {"id": "Centro",          "color": (0, 165, 255)},   # Naranja
            ]
            # Si existen zonas personalizadas no contempladas arriba, les asignamos un color default
            for nombre in maze_rois:
                if not any(c['id'] == nombre for c in config_cats):
                    if "abierto" in nombre.lower(): col = (120, 120, 240)    # Coral/Rojo tenue
                    elif "cerrado" in nombre.lower(): col = (255, 250, 0)    # Cyan
                    elif "centro" in nombre.lower(): col = (0, 165, 255)     # Naranja
                    else: col = (150, 150, 150) # default gris oscuro
                    config_cats.append({"id": nombre, "color": col}) 

            print(f"[OK] Zonas cargadas vía JSON (modo silencioso): {list(maze_rois.keys())}")
        except Exception as e:
            print(f"[ERROR] Error parseando zonas JSON, fallback a manual: {e}")
            roi_result = select_maze_rois(video_path)
            if roi_result is None: return
            maze_rois, config_cats = roi_result
    else:
        # Modo interactivo
        roi_result = select_maze_rois(video_path)
        if roi_result is None:
            return
        maze_rois, config_cats = roi_result

    yolo_model = None
    if tracking_data is None:
        print("Cargando modelo de seguimiento YOLO11 (fallback bbox)...")
        if not os.path.exists(YOLO_MODEL_PATH):
            raise FileNotFoundError(f"No se encontro el modelo YOLO en: {YOLO_MODEL_PATH}")
        yolo_model = get_yolo_class()(YOLO_MODEL_PATH)
    else:
        print("[TRACKING] Tracker bbox YOLO desactivado; se usara la pose precomputada.")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Iniciando ciclo multihilo de {total_frames} frames...")

    # Estados Thigmo
    thigmo_frames = 0
    thigmo_events = []
    thigmo_start = None
    thigmo_is_conf = False

    # Estados Grooming
    groom_frames = 0
    groom_events = []
    groom_start = None
    groom_is_conf = False
    
    arm_timers = {k: 0 for k in maze_rois.keys()}
    
    # Lista para almacenar trayectoria y pasarlo a Estadísticas
    trajectory_data = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
            
        current_sec = frame_idx / fps
        time_str = f"[{int(current_sec//60):0>2}:{current_sec%60:05.2f}]"
            
        if frame_idx < len(probs_groom):
            p_groom = probs_groom[frame_idx]

            track_cx, track_cy = None, None
            if tracking_data is not None and frame_idx < len(tracking_data["x"]):
                if bool(tracking_data["valid"][frame_idx]):
                    track_cx = int(round(float(tracking_data["x"][frame_idx])))
                    track_cy = int(round(float(tracking_data["y"][frame_idx])))
            elif yolo_model is not None:
                track_cx, track_cy = get_yolo_bbox_center(frame, yolo_model)

            # Punto de tracking y deteccion en tiempo real de zona
            current_zone = "Ninguna"
            p_thigmo = 0.0
            if track_cx is not None and track_cy is not None:
                for nombre, roi in maze_rois.items():
                    if is_point_in_roi(track_cx, track_cy, roi):
                        arm_timers[nombre] += 1
                        current_zone = nombre
                        break
                
                # Usando la probabilidad ML original del modelo SimBA
                if frame_idx < len(probs_thigmo):
                    p_thigmo = probs_thigmo[frame_idx]

            # --- EVALUAR THIGMOTAXIS (Basado en el Tracking en Tiempo Real de YOLO) ---
            (t_txt, t_col, t_status, thigmo_frames, thigmo_events, 
             thigmo_start, thigmo_is_conf) = state_machine_update(
                prob_val=p_thigmo, 
                current_sec=current_sec, 
                frames_acc=thigmo_frames, 
                events_list=thigmo_events, 
                current_start=thigmo_start, 
                is_confirming=thigmo_is_conf,
                umbral_confrm=thigmo_confirm_threshold,
                umbral_posible=thigmo_possible_threshold,
                min_event_seconds=thigmo_min_event_seconds
            )
            if t_col == (0, 0, 255): t_col = (0, 0, 255) # Thigmo rojo
            elif t_col == (0, 255, 255): t_col = (0, 165, 255) # Thigmo naranja

            # --- EVALUAR GROOMING (calibrado para YOLO Pose, sin inflar a falsos positivos) ---
            (g_txt, g_col, g_status, groom_frames, groom_events, 
             groom_start, groom_is_conf) = state_machine_update(
                prob_val=p_groom, 
                current_sec=current_sec, 
                frames_acc=groom_frames, 
                events_list=groom_events, 
                current_start=groom_start, 
                is_confirming=groom_is_conf,
                umbral_confrm=grooming_confirm_threshold,
                umbral_posible=grooming_possible_threshold,
                min_event_seconds=grooming_min_event_seconds
            )
            # Personalizamos colores visuales del Grooming (Violeta/Magenta)
            if g_col == (0, 0, 255): g_col = (255, 0, 255) # Confirmado es Violeta
            elif g_col == (0, 255, 255): g_col = (255, 105, 180) # Posible es Rosado

            # Dibujar ROIs
            overlay_rois = frame.copy()
            
            # 1. Dibujar Zonas Rectangulares (Fondo Transparente)
            for nombre, r in maze_rois.items():
                col = next((c["color"] for c in config_cats if c["id"] == nombre), (200, 200, 200))
                cv2.rectangle(overlay_rois, (r[0], r[1]), (r[0]+r[2], r[1]+r[3]), col, -1)
            cv2.addWeighted(overlay_rois, 0.15, frame, 0.85, 0, frame)

            # 2. Muros / Paredes Físicas (Ocultos a peticion del usuario)
            pass

            if track_cx is not None and track_cy is not None:
                cv2.circle(frame, (track_cx, track_cy), 2, TRACKING_DOT_COLOR, -1, lineType=cv2.LINE_AA)
                cv2.circle(frame, (track_cx, track_cy), 4, TRACKING_DOT_OUTLINE_COLOR, 1, lineType=cv2.LINE_AA)
                
            # Log Data
            trajectory_data.append({
                "Tiempo (s)": current_sec,
                "x": track_cx if track_cx is not None else 0,
                "y": track_cy if track_cy is not None else 0,
                "Zona": current_zone,
                "Grooming": 1 if g_status == 2 else 0,
                "Thigmotaxis": 1 if t_status == 2 else 0,
            })
            
            # Draw HUD Multimodal
            combined_data = {**roi_timers, **arm_timers}
            
            frame = draw_hud(frame, time_str, fps, width, height,
                             # Thigmotaxis kwargs
                             thigmo_prob=p_thigmo, thigmo_status=t_txt, thigmo_color=t_col, 
                             thigmo_acc=(thigmo_frames/fps), thigmo_events=thigmo_events,
                             # Grooming kwargs
                             groom_prob=p_groom, groom_status=g_txt, groom_color=g_col,
                             groom_acc=(groom_frames/fps), groom_events=groom_events,
                             # Globales
                             combined_timers=combined_data,
                             thigmo_pred_status=t_status, groom_pred_status=g_status)
        
        out.write(frame)
        frame_idx += 1
        
        if frame_idx % 300 == 0:
            print(f"Renderizados {frame_idx}/{total_frames} frames...")

    cap.release()
    out.release()
    print(f"\n¡Video DUAL renderizado exitosamente en:\n{output_path}")
    
    # Exportar Trayectoria General Continua
    df_traj = pd.DataFrame(trajectory_data)
    traj_csv_path = output_path.replace(".mp4", "_trajectory.csv")
    df_traj.to_csv(traj_csv_path, index=False)
    print(f"¡Trayectoria exportada a {traj_csv_path}!")
    
    export_timelog(thigmo_events, output_path, total_frames, thigmo_start, "THIGMOTAXIS", fps)
    export_timelog(groom_events, output_path, total_frames, groom_start, "GROOMING", fps)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline principal para la predicción MULTIMODAL de comportamientos (Thigmotaxis y Grooming).")
    parser.add_argument("--video", type=str, required=True, help="Ruta hacia el video de origen.")
    parser.add_argument("--features", type=str, required=True, help="Ruta al CSV con todas las características de SimBA.")
    parser.add_argument("--model_thigmo", type=str, required=True, help="Ruta al modelo .sav de Thigmotaxis.")
    parser.add_argument("--model_grooming", type=str, required=True, help="Ruta al modelo .sav de Grooming.")
    parser.add_argument("--output", type=str, required=True, help="Nombre deseado para el archivo multihud final.")
    parser.add_argument("--zonas_json", type=str, required=False, default="", help="Zonas en formato JSON para evitar prompt interactivo.")
    parser.add_argument("--zonas_file", type=str, required=False, default="", help="Ruta a un JSON de zonas para evitar pasar el payload completo por CLI.")
    parser.add_argument("--thigmo-confirm-threshold", type=float, default=THIGMO_CONFIRM_THRESHOLD, help="Umbral para confirmar Thigmotaxis.")
    parser.add_argument("--thigmo-possible-threshold", type=float, default=THIGMO_POSSIBLE_THRESHOLD, help="Umbral para marcar Thigmotaxis posible.")
    parser.add_argument("--thigmo-min-event-seconds", type=float, default=THIGMO_MIN_EVENT_SECONDS, help="Duracion minima de un evento Thigmotaxis.")
    parser.add_argument("--grooming-confirm-threshold", type=float, default=GROOMING_CONFIRM_THRESHOLD, help="Umbral para confirmar Grooming.")
    parser.add_argument("--grooming-possible-threshold", type=float, default=GROOMING_POSSIBLE_THRESHOLD, help="Umbral para marcar Grooming posible.")
    parser.add_argument("--grooming-min-event-seconds", type=float, default=GROOMING_MIN_EVENT_SECONDS, help="Duracion minima de un evento Grooming.")
    parser.add_argument("--behavior-smoothing-frames", type=int, default=BEHAVIOR_SMOOTHING_FRAMES, help="Ventana de suavizado para probabilidades.")
    parser.add_argument("--lstm-grooming-csv", type=str, default="", help="CSV generado por infer_grooming_lstm.py.")
    parser.add_argument("--grooming-source", choices=["rf", "lstm", "ensemble", "rescue"], default="rf", help="Fuente de probabilidad para Grooming.")
    parser.add_argument("--lstm-rescue-rf-threshold", type=float, default=0.22, help="Piso RF para que LSTM pueda rescatar Grooming.")
    parser.add_argument("--lstm-rescue-threshold", type=float, default=0.11, help="Umbral LSTM para rescate temporal de Grooming.")
    
    args = parser.parse_args()
    zonas_json_payload = args.zonas_json
    if args.zonas_file:
        with open(args.zonas_file, "r", encoding="utf-8") as file_handle:
            zonas_json_payload = file_handle.read()
    # model_thigmo y model_grooming are passed directly to override geometry
    generate_video(
        args.video,
        args.features,
        args.output,
        zonas_json_payload,
        args.model_thigmo,
        args.model_grooming,
        thigmo_confirm_threshold=args.thigmo_confirm_threshold,
        thigmo_possible_threshold=args.thigmo_possible_threshold,
        thigmo_min_event_seconds=args.thigmo_min_event_seconds,
        grooming_confirm_threshold=args.grooming_confirm_threshold,
        grooming_possible_threshold=args.grooming_possible_threshold,
        grooming_min_event_seconds=args.grooming_min_event_seconds,
        smoothing_frames=args.behavior_smoothing_frames,
        lstm_grooming_csv=args.lstm_grooming_csv,
        grooming_source=args.grooming_source,
        lstm_rescue_rf_threshold=args.lstm_rescue_rf_threshold,
        lstm_rescue_threshold=args.lstm_rescue_threshold,
    )
