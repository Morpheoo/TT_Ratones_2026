"""Helpers pequenos para SQL compatible con PostgreSQL y SQLite."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, text


def is_sqlite(bind) -> bool:
    dialect = getattr(bind, "dialect", None)
    if dialect is None:
        dialect = getattr(getattr(bind, "engine", None), "dialect", None)
    return bool(dialect and dialect.name == "sqlite")


def ensure_column(conn, table_name: str, column_name: str, sql_type: str) -> None:
    """Agrega una columna solo cuando no existe, sin SQL especifico de Postgres."""
    columns = {column["name"] for column in inspect(conn).get_columns(table_name)}
    if column_name not in columns:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}"))


def minutes_since(value) -> float:
    """Calcula edad de timestamps entregados por cualquiera de los dos drivers."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError:
            return 0.0
    if not isinstance(value, datetime):
        return 0.0
    now = datetime.now(timezone.utc if value.tzinfo else None)
    return max(0.0, (now - value).total_seconds() / 60.0)


def latest_analysis_join_sql() -> str:
    """Subconsulta portable para obtener el resultado mas reciente por experimento."""
    return """
        SELECT experiment_id, status, timestamp, id
        FROM (
            SELECT experiment_id, status, timestamp, id,
                   ROW_NUMBER() OVER (
                       PARTITION BY experiment_id
                       ORDER BY timestamp DESC, id DESC
                   ) AS row_number
            FROM analysis_results
        ) ranked_results
        WHERE row_number = 1
    """
