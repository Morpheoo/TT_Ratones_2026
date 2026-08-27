"""Verificacion rapida del payload antes de compilar el instalador."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


REQUIRED_FILES = (
    "Home.py",
    "run_app.py",
    "start_services.py",
    "schema_sqlite.sql",
    ".env",
    "runtime/py310/python.exe",
    "runtime/py311/python.exe",
    "runs/pose/yolo11s_pose_raton_v4/weights/best.pt",
    "data/models/lstm_grooming_yolo/grooming_lstm.keras",
    "data/models/lstm_grooming_yolo/scaler.pkl",
    "data/models/lstm_grooming_yolo/metadata.json",
    "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav",
    "data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav",
    "data/simba_projects/grooming_thigmotaxis_yolo/project_folder/project_config.ini",
    "reportes/Manual de Usario TT 2026-A155.pdf",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    root = args.payload.resolve()

    missing = [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]
    if missing:
        for relative in missing:
            print(f"[MISSING] {relative}")
        return 2

    environment = os.environ.copy()
    environment.update(
        DB_BACKEND="sqlite",
        TT_OFFLINE_INSTALL="1",
        TT_APP_DATA_DIR=str(root / "_smoke_data"),
        PYTHONIOENCODING="utf-8",
    )
    checks = (
        (
            root / "runtime/py311/python.exe",
            "from pathlib import Path; "
            "import streamlit, sqlalchemy, bcrypt, cv2, torch; "
            "from ultralytics import YOLO; "
            "from src.db.connection import init_db; assert init_db(); "
            "root=Path.cwd(); YOLO(str(root/'runs/pose/yolo11s_pose_raton_v4/weights/best.pt'))",
        ),
        (
            root / "runtime/py310/python.exe",
            "from pathlib import Path; import pickle, simba, tables, cv2, sklearn; "
            "from tensorflow.keras.models import load_model; root=Path.cwd(); "
            "load_model(root/'data/models/lstm_grooming_yolo/grooming_lstm.keras'); "
            "[pickle.load(open(root/'data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models'/name,'rb')) "
            "for name in ('Grooming.sav','Thigmotaxis.sav')]",
        ),
    )
    for executable, expression in checks:
        print(f"[CHECK] {executable.parent.name}")
        subprocess.run(
            [str(executable), "-c", expression],
            cwd=root,
            env=environment,
            check=True,
            timeout=180,
        )

    print("[OK] Payload offline completo y runtimes importables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
