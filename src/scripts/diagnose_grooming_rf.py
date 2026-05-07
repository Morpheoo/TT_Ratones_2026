"""
Diagnostico de Grooming RF sobre archivos SimBA.

Compara probabilidades del modelo Grooming.sav contra las etiquetas manuales en
project_folder/csv/targets_inserted y barre thresholds para encontrar el punto
mas util antes de entrenar un clasificador temporal.

Uso:
    venv_310\\Scripts\\python.exe src\\scripts\\diagnose_grooming_rf.py --yolo
"""

from __future__ import annotations

import argparse
import csv
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import GROOMING_MODEL, GROOMING_MODEL_YOLO, SIMBA_BASE, SIMBA_YOLO_BASE


def load_model(path: Path):
    with open(path, "rb") as file_handle:
        model = pickle.load(file_handle)
    if hasattr(model, "n_jobs"):
        try:
            model.n_jobs = 1
        except Exception:
            pass
    return model


def align_features(df: pd.DataFrame, model) -> pd.DataFrame:
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    if hasattr(model, "feature_names_in_"):
        expected = list(model.feature_names_in_)
        missing = [column for column in expected if column not in df.columns]
        if missing:
            df = pd.concat([df, pd.DataFrame(0.0, index=df.index, columns=missing)], axis=1)
        df = df[expected]
    return df.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def smooth(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    return pd.Series(values).rolling(window=window, min_periods=1, center=True).mean().to_numpy()


def remove_short_bouts(mask: np.ndarray, min_frames: int) -> np.ndarray:
    if min_frames <= 1:
        return mask.astype(int)

    result = mask.astype(int).copy()
    start = None
    for idx, value in enumerate(np.r_[result, 0]):
        if value and start is None:
            start = idx
        elif not value and start is not None:
            if idx - start < min_frames:
                result[start:idx] = 0
            start = None
    return result


def score_threshold(y_true: np.ndarray, probs: np.ndarray, threshold: float, min_frames: int) -> dict[str, float]:
    pred = remove_short_bouts(probs >= threshold, min_frames=min_frames)
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "predicted_frames": int(pred.sum()),
        "true_frames": int(y_true.sum()),
    }


def iter_video_pairs(project_root: Path):
    features_dir = project_root / "project_folder" / "csv" / "features_extracted"
    targets_dir = project_root / "project_folder" / "csv" / "targets_inserted"
    for features_path in sorted(features_dir.glob("*.csv")):
        target_path = targets_dir / features_path.name
        if target_path.exists():
            yield features_path.stem, features_path, target_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostica thresholds RF para Grooming.")
    parser.add_argument("--yolo", action="store_true", help="Usar proyecto SimBA YOLO.")
    parser.add_argument("--project-root", default="", help="Raiz del proyecto SimBA a diagnosticar.")
    parser.add_argument("--model", default="", help="Ruta opcional a Grooming.sav.")
    parser.add_argument("--threshold-start", type=float, default=0.15)
    parser.add_argument("--threshold-stop", type=float, default=0.60)
    parser.add_argument("--threshold-step", type=float, default=0.01)
    parser.add_argument("--smoothing-frames", type=int, default=15)
    parser.add_argument("--min-bout-ms", type=float, default=500.0)
    parser.add_argument("--fps", type=float, default=30.0, help="FPS para convertir min-bout-ms a frames.")
    parser.add_argument("--output", default="reports/grooming_rf_threshold_diagnostic.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve() if args.project_root else (SIMBA_YOLO_BASE if args.yolo else SIMBA_BASE)
    model_path = Path(args.model).resolve() if args.model else (GROOMING_MODEL_YOLO if args.yolo else GROOMING_MODEL)
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = load_model(model_path)
    thresholds = np.arange(args.threshold_start, args.threshold_stop + 1e-9, args.threshold_step)
    min_frames = max(1, int(round((args.min_bout_ms / 1000.0) * args.fps)))

    all_true: list[np.ndarray] = []
    all_probs: list[np.ndarray] = []
    rows: list[dict[str, object]] = []

    print(f"[INFO] Proyecto: {project_root}")
    print(f"[INFO] Modelo: {model_path}")
    print(f"[INFO] Smoothing: {args.smoothing_frames} frames | Min bout: {min_frames} frames")

    for video_name, features_path, target_path in iter_video_pairs(project_root):
        features = pd.read_csv(features_path)
        targets = pd.read_csv(target_path)
        if "Grooming" not in targets.columns:
            print(f"[WARN] {video_name}: sin columna Grooming")
            continue

        x = align_features(features, model)
        raw_probs = model.predict_proba(x)[:, 1] if hasattr(model, "predict_proba") else model.predict(x)
        probs = smooth(np.asarray(raw_probs, dtype=float), args.smoothing_frames)
        y_true = targets["Grooming"].fillna(0).astype(int).to_numpy()[: len(probs)]
        probs = probs[: len(y_true)]

        all_true.append(y_true)
        all_probs.append(probs)

        best = max((score_threshold(y_true, probs, float(t), min_frames) for t in thresholds), key=lambda item: item["f1"])
        rows.append({"scope": "video", "video": video_name, **best})
        print(
            f"[VIDEO] {video_name}: best={best['threshold']:.2f} "
            f"P={best['precision']:.3f} R={best['recall']:.3f} F1={best['f1']:.3f} "
            f"true={best['true_frames']} pred={best['predicted_frames']}"
        )

    if not all_true:
        print("[ERROR] No se encontraron pares features+targets con Grooming.")
        return 1

    y_all = np.concatenate(all_true)
    p_all = np.concatenate(all_probs)
    for threshold in thresholds:
        rows.append({"scope": "aggregate", "video": "ALL", **score_threshold(y_all, p_all, float(threshold), min_frames)})

    aggregate_rows = [row for row in rows if row["scope"] == "aggregate"]
    best_all = max(aggregate_rows, key=lambda item: float(item["f1"]))
    print(
        f"[ALL] best={best_all['threshold']:.2f} "
        f"P={best_all['precision']:.3f} R={best_all['recall']:.3f} F1={best_all['f1']:.3f} "
        f"true={best_all['true_frames']} pred={best_all['predicted_frames']}"
    )

    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["scope", "video", "threshold", "precision", "recall", "f1", "true_frames", "predicted_frames"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Diagnostico guardado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
