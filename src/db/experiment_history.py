import json
import os
from typing import Any

from sqlalchemy import text

from .dialect import is_sqlite


def _normalize_zone_name(zone: dict[str, Any]) -> str:
    return (
        str(
            zone.get("Nombre Zona")
            or zone.get("id")
            or zone.get("zone_type")
            or zone.get("type")
            or "Zona"
        )
        .strip()
    )


def resolve_user_id(conn, username: str | None) -> int | None:
    if not username:
        return None

    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username LIMIT 1"),
        {"username": username},
    ).fetchone()
    return row[0] if row else None


def get_or_create_experiment_for_video(
    conn,
    *,
    video_path: str,
    rat_id: str,
    treatment: str,
    responsible: str,
    created_by: int | None = None,
) -> int | None:
    existing = conn.execute(
        text(
            """
            SELECT id
            FROM experiments
            WHERE video_path = :video_path
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"video_path": video_path},
    ).fetchone()
    if existing:
        return int(existing[0])

    created = conn.execute(
        text(
            """
            INSERT INTO experiments (
                rat_id,
                treatment,
                experiment_date,
                responsible,
                video_path,
                duration_seconds,
                created_by,
                processed
            )
            VALUES (
                :rat_id,
                :treatment,
                CURRENT_DATE,
                :responsible,
                :video_path,
                NULL,
                :created_by,
                FALSE
            )
            RETURNING id
            """
        ),
        {
            "rat_id": rat_id,
            "treatment": treatment,
            "responsible": responsible,
            "video_path": video_path,
            "created_by": created_by,
        },
    ).fetchone()
    return int(created[0]) if created else None


def replace_experiment_rois(
    conn,
    experiment_id: int,
    zonas: list[dict[str, Any]],
    *,
    scale_factor: float | None = None,
) -> int:
    conn.execute(
        text("DELETE FROM roi_configurations WHERE experiment_id = :experiment_id"),
        {"experiment_id": experiment_id},
    )

    saved = 0
    for zone in zonas:
        if not isinstance(zone, dict):
            continue
        coordinates_value = ":coordinates_json" if is_sqlite(conn) else "CAST(:coordinates_json AS JSONB)"
        conn.execute(
            text(
                f"""
                INSERT INTO roi_configurations (
                    experiment_id,
                    zone_type,
                    coordinates_json,
                    scale_factor
                )
                VALUES (
                    :experiment_id,
                    :zone_type,
                    {coordinates_value},
                    :scale_factor
                )
                """
            ),
            {
                "experiment_id": experiment_id,
                "zone_type": _normalize_zone_name(zone),
                "coordinates_json": json.dumps(zone, ensure_ascii=False),
                "scale_factor": scale_factor,
            },
        )
        saved += 1

    return saved


def persist_zones_for_video(
    engine,
    *,
    video_path: str,
    zonas: list[dict[str, Any]],
    rat_id: str,
    treatment: str,
    responsible: str,
    username: str | None = None,
    scale_factor: float | None = None,
) -> dict[str, Any]:
    if not engine:
        raise RuntimeError("No hay motor de base de datos disponible.")
    if not video_path:
        raise ValueError("video_path es obligatorio para persistir zonas.")

    with engine.connect() as conn:
        user_id = resolve_user_id(conn, username)
        experiment_id = get_or_create_experiment_for_video(
            conn,
            video_path=video_path,
            rat_id=rat_id,
            treatment=treatment,
            responsible=responsible,
            created_by=user_id,
        )
        if experiment_id is None:
            raise RuntimeError("No se pudo resolver un experimento para persistir ROIs.")

        saved_count = replace_experiment_rois(
            conn,
            experiment_id,
            zonas,
            scale_factor=scale_factor,
        )
        conn.commit()

    return {
        "experiment_id": experiment_id,
        "zones_saved": saved_count,
    }


def fetch_recent_experiments_with_zones(engine, limit: int = 20) -> list[dict[str, Any]]:
    if not engine:
        return []

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    e.id,
                    e.rat_id,
                    e.treatment,
                    e.experiment_date,
                    e.responsible,
                    e.video_path,
                    e.created_at,
                    COUNT(r.id) AS zone_count
                FROM experiments e
                INNER JOIN roi_configurations r
                    ON r.experiment_id = e.id
                GROUP BY e.id
                ORDER BY e.created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    history: list[dict[str, Any]] = []
    for row in rows:
        video_path = row["video_path"]
        if not video_path or not os.path.exists(video_path):
            continue
        if "_STREAMLIT_MULTIMODAL" in os.path.basename(video_path):
            continue
        history.append(dict(row))
    return history


def load_experiment_zones(engine, experiment_id: int) -> list[dict[str, Any]]:
    if not engine:
        return []

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT coordinates_json
                FROM roi_configurations
                WHERE experiment_id = :experiment_id
                ORDER BY id ASC
                """
            ),
            {"experiment_id": experiment_id},
        ).fetchall()

    zones: list[dict[str, Any]] = []
    for row in rows:
        payload = row[0]
        if isinstance(payload, dict):
            zones.append(payload)
            continue
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    zones.append(parsed)
            except json.JSONDecodeError:
                continue
    return zones
