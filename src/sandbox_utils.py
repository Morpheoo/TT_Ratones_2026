"""Helpers para soportar sandboxes de SimBA.

Un "sandbox" es un proyecto SimBA paralelo al productivo
(`grooming_thigmotaxis_yolo`) donde se procesan videos de escenarios
experimentales sin contaminar las ROIs, features ni video_info del
proyecto principal. Los sandboxes los crea
`src/scripts/bootstrap_sandbox.py` y siguen la convencion de nombre
`sandbox_<nombre>`.

La eleccion entre productivo y sandbox vive en
`st.session_state["simba_project_choice"]` y se persiste via
`save_session()` (key registrada en `src/session_utils.py`).
"""
from __future__ import annotations

from pathlib import Path

PRODUCTIVO_KEY = "grooming_thigmotaxis_yolo"


def list_available_simba_projects(simba_root: Path) -> list[str]:
    """Devuelve los nombres de proyectos SimBA reconocidos por el selector.

    Un proyecto valido es una carpeta hija que contiene `project_folder/`
    Y cuyo nombre es el productivo o empieza con `sandbox_` (creados por
    `bootstrap_sandbox.py`). Eso filtra proyectos legacy (DLC, viejos
    sandboxes hechos a mano) del selector de la UI.

    El productivo siempre va primero; los sandboxes en orden alfabetico.
    """
    if not simba_root.exists():
        return []
    valid = [
        d.name
        for d in simba_root.iterdir()
        if d.is_dir() and (d / "project_folder").exists()
        and (d.name == PRODUCTIVO_KEY or d.name.startswith("sandbox_"))
    ]
    productivo = [n for n in valid if n == PRODUCTIVO_KEY]
    sandboxes = sorted(n for n in valid if n != PRODUCTIVO_KEY)
    return productivo + sandboxes


def get_active_simba_project_name(default: str = PRODUCTIVO_KEY) -> str:
    """Lee la eleccion del session_state. Default: productivo.

    Devuelve el `default` si Streamlit no esta disponible o la key no
    esta seteada (ej. en CLI o al primer arranque).
    """
    try:
        import streamlit as st
        return st.session_state.get("simba_project_choice") or default
    except Exception:
        return default


def get_active_simba_base(simba_root: Path) -> Path:
    """Path al base del proyecto SimBA activo (productivo o sandbox)."""
    return simba_root / get_active_simba_project_name()


def get_active_simba_project_dir(simba_root: Path) -> Path:
    """Path al `project_folder` del proyecto activo."""
    return get_active_simba_base(simba_root) / "project_folder"


def format_project_label(name: str) -> str:
    """Etiqueta amigable para el selectbox de Streamlit."""
    if name == PRODUCTIVO_KEY:
        return "Productivo (proyecto principal)"
    if name.startswith("sandbox_"):
        return f"Sandbox: {name[len('sandbox_'):]}"
    return name
