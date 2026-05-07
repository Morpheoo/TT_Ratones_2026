"""
Inferencia frame-a-frame con el LSTM experimental de Grooming.

Produce un CSV con Probability_Grooming_LSTM y Grooming_LSTM alineado al video.

Uso:
    venv_310\\Scripts\\python.exe src\\scripts\\infer_grooming_lstm.py ^
      --features data\\simba_projects\\grooming_thigmotaxis_yolo\\project_folder\\csv\\features_extracted\\R5B20_01mar24.csv
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_artifacts(model_dir: Path):
    from tensorflow import keras

    model = keras.models.load_model(model_dir / "grooming_lstm.keras")
    with open(model_dir / "scaler.pkl", "rb") as file_handle:
        scaler = pickle.load(file_handle)
    with open(model_dir / "metadata.json", "r", encoding="utf-8") as file_handle:
        metadata = json.load(file_handle)
    return model, scaler, metadata


def build_centered_windows(x: np.ndarray, window: int) -> np.ndarray:
    half = window // 2
    padded = np.pad(x, ((half, half), (0, 0)), mode="edge")
    windows = [padded[idx : idx + window] for idx in range(len(x))]
    return np.asarray(windows, dtype=np.float32)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inferencia LSTM experimental para Grooming.")
    parser.add_argument("--features", required=True, help="CSV features_extracted de SimBA.")
    parser.add_argument("--model-dir", default="data/models/lstm_grooming_yolo")
    parser.add_argument("--output", default="", help="CSV de salida. Default: junto al features CSV.")
    parser.add_argument("--threshold", type=float, default=None, help="Umbral. Default: mejor threshold de metadata.")
    parser.add_argument("--smoothing-frames", type=int, default=15)
    parser.add_argument("--min-bout-ms", type=float, default=500.0)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--batch-size", type=int, default=512)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    features_path = Path(args.features).resolve()
    model_dir = (PROJECT_ROOT / args.model_dir).resolve() if not Path(args.model_dir).is_absolute() else Path(args.model_dir)
    output_path = Path(args.output).resolve() if args.output else features_path.with_name(features_path.stem + "_grooming_lstm.csv")

    model, scaler, metadata = load_artifacts(model_dir)
    feature_columns = metadata["feature_columns"]
    window = int(metadata["window"])
    threshold = float(args.threshold if args.threshold is not None else metadata["best_threshold"]["threshold"])

    df = pd.read_csv(features_path)
    x_df = df.reindex(columns=feature_columns, fill_value=0.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    x = scaler.transform(x_df)
    windows = build_centered_windows(x, window=window)
    probs = model.predict(windows, batch_size=args.batch_size).ravel()
    probs = pd.Series(probs).rolling(window=max(1, args.smoothing_frames), min_periods=1, center=True).mean().to_numpy()
    min_frames = max(1, int(round((args.min_bout_ms / 1000.0) * args.fps)))
    pred = remove_short_bouts(probs >= threshold, min_frames=min_frames)

    out = pd.DataFrame(
        {
            "Frame": np.arange(len(probs)),
            "Probability_Grooming_LSTM": probs,
            "Grooming_LSTM": pred,
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)

    print(f"[OK] LSTM inference: {output_path}")
    print(f"[INFO] threshold={threshold:.3f} smoothing={args.smoothing_frames} min_frames={min_frames}")
    print(f"[INFO] detected_frames={int(pred.sum())} ({int(pred.sum()) / max(args.fps, 1):.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
