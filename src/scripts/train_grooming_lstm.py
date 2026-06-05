"""
Entrena un LSTM experimental para Grooming usando features SimBA por ventanas.

El modelo no reemplaza al RF: queda guardado como backend temporal comparativo.

Uso:
    venv_310\\Scripts\\python.exe src\\scripts\\train_grooming_lstm.py --yolo
"""

from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SIMBA_BASE, SIMBA_YOLO_BASE


LABEL_COLUMNS = {"Grooming", "Thigmotaxis"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    excluded = LABEL_COLUMNS | {"Unnamed: 0"}
    return [column for column in df.columns if column not in excluded and pd.api.types.is_numeric_dtype(df[column])]


def make_sequences(x: np.ndarray, y: np.ndarray, window: int, stride: int) -> tuple[np.ndarray, np.ndarray]:
    half_window = window // 2
    xs: list[np.ndarray] = []
    ys: list[int] = []
    for center in range(half_window, len(y) - half_window, stride):
        start = center - half_window
        end = start + window
        xs.append(x[start:end])
        ys.append(int(y[center]))
    if not xs:
        return np.empty((0, window, x.shape[1]), dtype=np.float32), np.empty((0,), dtype=np.int32)
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.int32)


def load_video_table(features_path: Path, target_path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    features = pd.read_csv(features_path)
    targets = pd.read_csv(target_path)
    if "Grooming" not in targets.columns:
        raise ValueError(f"Sin columna Grooming: {target_path}")

    n_rows = min(len(features), len(targets))
    features = features.iloc[:n_rows].copy()
    y = targets["Grooming"].fillna(0).astype(int).to_numpy()[:n_rows]
    return features, y


def collect_dataset(project_root: Path, window: int, stride: int, validation_fraction: float):
    features_dir = project_root / "project_folder" / "csv" / "features_extracted"
    targets_dir = project_root / "project_folder" / "csv" / "targets_inserted"
    pairs = [(p.stem, p, targets_dir / p.name) for p in sorted(features_dir.glob("*.csv")) if (targets_dir / p.name).exists()]
    if len(pairs) < 3:
        raise RuntimeError("Se necesitan al menos 3 videos con features + targets para una validación razonable.")

    validation_count = max(1, int(round(len(pairs) * validation_fraction)))
    train_pairs = pairs[:-validation_count]
    val_pairs = pairs[-validation_count:]

    sample_df, _ = load_video_table(train_pairs[0][1], train_pairs[0][2])
    feature_columns = get_feature_columns(sample_df)
    if not feature_columns:
        raise RuntimeError("No se encontraron columnas numericas de features.")

    train_frames: list[pd.DataFrame] = []
    train_labels: list[np.ndarray] = []
    val_frames: list[pd.DataFrame] = []
    val_labels: list[np.ndarray] = []

    for _, features_path, target_path in train_pairs:
        df, y = load_video_table(features_path, target_path)
        train_frames.append(df.reindex(columns=feature_columns, fill_value=0.0))
        train_labels.append(y)
    for _, features_path, target_path in val_pairs:
        df, y = load_video_table(features_path, target_path)
        val_frames.append(df.reindex(columns=feature_columns, fill_value=0.0))
        val_labels.append(y)

    scaler = StandardScaler()
    scaler.fit(pd.concat(train_frames, axis=0).replace([np.inf, -np.inf], np.nan).fillna(0.0))

    def transform_frames(frames: list[pd.DataFrame], labels: list[np.ndarray]):
        seq_x: list[np.ndarray] = []
        seq_y: list[np.ndarray] = []
        for df, y in zip(frames, labels):
            x = scaler.transform(df.replace([np.inf, -np.inf], np.nan).fillna(0.0))
            x_seq, y_seq = make_sequences(x, y, window=window, stride=stride)
            if len(y_seq):
                seq_x.append(x_seq)
                seq_y.append(y_seq)
        return np.concatenate(seq_x, axis=0), np.concatenate(seq_y, axis=0)

    x_train, y_train = transform_frames(train_frames, train_labels)
    x_val, y_val = transform_frames(val_frames, val_labels)
    return x_train, y_train, x_val, y_val, scaler, feature_columns, train_pairs, val_pairs


def build_model(window: int, n_features: int, learning_rate: float):
    from tensorflow import keras

    inputs = keras.Input(shape=(window, n_features))
    x = keras.layers.Masking(mask_value=0.0)(inputs)
    x = keras.layers.Bidirectional(keras.layers.LSTM(64, return_sequences=True))(x)
    x = keras.layers.Dropout(0.25)(x)
    x = keras.layers.Bidirectional(keras.layers.LSTM(32))(x)
    x = keras.layers.Dropout(0.25)(x)
    outputs = keras.layers.Dense(1, activation="sigmoid")(x)
    model = keras.Model(inputs, outputs, name="grooming_lstm")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.AUC(curve="PR", name="pr_auc"),
        ],
    )
    return model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrena LSTM experimental para Grooming.")
    parser.add_argument("--yolo", action="store_true", help="Usar proyecto SimBA YOLO.")
    parser.add_argument("--project-root", default="", help="Raiz del proyecto SimBA.")
    parser.add_argument("--window", type=int, default=45, help="Frames por ventana temporal.")
    parser.add_argument("--stride", type=int, default=3, help="Paso entre ventanas de entrenamiento.")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data/models/lstm_grooming_yolo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    set_seed(args.seed)

    project_root = Path(args.project_root).resolve() if args.project_root else (SIMBA_YOLO_BASE if args.yolo else SIMBA_BASE)
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    x_train, y_train, x_val, y_val, scaler, feature_columns, train_pairs, val_pairs = collect_dataset(
        project_root=project_root,
        window=args.window,
        stride=args.stride,
        validation_fraction=args.validation_fraction,
    )

    pos = int(y_train.sum())
    neg = int(len(y_train) - pos)
    class_weight = {0: 1.0, 1: float(neg / max(pos, 1))}

    print(f"[DATA] Train windows: {len(y_train)} | positives: {pos} | negatives: {neg}")
    print(f"[DATA] Val windows: {len(y_val)} | positives: {int(y_val.sum())}")
    print(f"[DATA] Features: {len(feature_columns)} | window: {args.window} | stride: {args.stride}")

    model = build_model(args.window, len(feature_columns), args.learning_rate)
    from tensorflow import keras

    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_pr_auc", mode="max", patience=6, restore_best_weights=True),
        keras.callbacks.ModelCheckpoint(output_dir / "grooming_lstm.keras", monitor="val_pr_auc", mode="max", save_best_only=True),
    ]

    model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=2,
    )

    probs = model.predict(x_val, batch_size=args.batch_size).ravel()
    best = None
    for threshold in np.arange(0.10, 0.91, 0.01):
        pred = probs >= threshold
        row = {
            "threshold": float(threshold),
            "precision": float(precision_score(y_val, pred, zero_division=0)),
            "recall": float(recall_score(y_val, pred, zero_division=0)),
            "f1": float(f1_score(y_val, pred, zero_division=0)),
        }
        if best is None or row["f1"] > best["f1"]:
            best = row

    assert best is not None
    print(f"[VAL] Best threshold={best['threshold']:.2f} P={best['precision']:.3f} R={best['recall']:.3f} F1={best['f1']:.3f}")
    print(classification_report(y_val, probs >= best["threshold"], zero_division=0))

    model.save(output_dir / "grooming_lstm.keras")
    with open(output_dir / "scaler.pkl", "wb") as file_handle:
        pickle.dump(scaler, file_handle)
    metadata = {
        "behavior": "Grooming",
        "project_root": str(project_root),
        "window": args.window,
        "stride": args.stride,
        "feature_columns": feature_columns,
        "best_threshold": best,
        "train_videos": [item[0] for item in train_pairs],
        "validation_videos": [item[0] for item in val_pairs],
    }
    with open(output_dir / "metadata.json", "w", encoding="utf-8") as file_handle:
        json.dump(metadata, file_handle, indent=2, ensure_ascii=False)

    print(f"[OK] Modelo LSTM guardado en: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
