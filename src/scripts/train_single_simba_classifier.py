"""
Train a single SimBA Random Forest classifier using the current project config.

Usage:
    .\venv_310\Scripts\python.exe src\scripts\train_single_simba_classifier.py ^
        --config "data/simba_projects/New folder/thigmotaxis_optimizado/project_folder/project_config.ini" ^
        --behavior Grooming
"""

from __future__ import annotations

import argparse
import configparser
import os
import sys
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train one SimBA classifier in generated_models.")
    parser.add_argument("--config", required=True, help="Path to project_config.ini")
    parser.add_argument("--behavior", required=True, help="Classifier name, e.g. Grooming or Thigmotaxis")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = os.path.abspath(args.config)
    behavior = args.behavior.strip()

    if not os.path.exists(config_path):
        print(f"[ERROR] Config not found: {config_path}")
        return 1

    config = configparser.ConfigParser()
    config.read(config_path)
    config.set("create ensemble settings", "classifier", behavior)

    with open(config_path, "w", encoding="utf-8") as config_file:
        config.write(config_file)

    print(f"[CONFIG] Updated training config: {config_path}")
    print(f"[CONFIG] classifier={behavior}")
    print(f"[START] {datetime.now().isoformat(timespec='seconds')}")

    from simba.model.train_rf import TrainRandomForestClassifier

    trainer = TrainRandomForestClassifier(config_path=config_path)
    trainer.run()
    trainer.save()

    model_dir = config.get("SML settings", "model_dir")
    output_model = os.path.join(model_dir, "generated_models", f"{behavior}.sav")
    print(f"[OUTPUT] Expected model path: {output_model}")
    if os.path.exists(output_model):
        print(f"[OUTPUT] Model exists: {output_model}")
    else:
        print(f"[ERROR] Model was not created: {output_model}")
        return 2

    print(f"[DONE] {behavior} single-model training finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
