"""Sanea y vuelve portatil el project_config.ini incluido en el instalador."""

from __future__ import annotations

import argparse
import configparser
from pathlib import Path


RELATIVE_CONFIG = Path(
    "data/simba_projects/grooming_thigmotaxis_yolo/project_folder/project_config.ini"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    root = args.payload.resolve()
    config_path = root / RELATIVE_CONFIG

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    with config_path.open("r", encoding="utf-8") as handle:
        config.read_file(handle)

    # No grabar la ruta ni el usuario de la PC que construye el instalador.
    # fix_simba_paths.py sustituye este marcador por {app} antes del analisis.
    base = Path("__TT_INSTALL_ROOT__") / "data" / "simba_projects" / "grooming_thigmotaxis_yolo"
    project_folder = base / "project_folder"
    generated_models = base / "models" / "generated_models"
    config["General settings"]["project_path"] = str(project_folder)
    config["SML settings"]["model_dir"] = str(base / "models")
    config["SML settings"]["model_path_1"] = str(generated_models / "Thigmotaxis.sav")
    config["SML settings"]["model_path_2"] = str(generated_models / "Grooming.sav")

    if config.has_section("Last saved frames"):
        config.remove_section("Last saved frames")
    config.add_section("Last saved frames")

    with config_path.open("w", encoding="utf-8", newline="\n") as handle:
        config.write(handle, space_around_delimiters=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
