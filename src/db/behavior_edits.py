"""
Capa de auditoria para ediciones manuales de tiempos conductuales.

Cada vez que un investigador o admin corrige los segundos de
Abiertos / Cerrados / Grooming / Thigmotaxis en la página 05,
guardamos un snapshot before/after en la tabla `behavior_edits`.

Asi se puede revertir y trazar quien, cuando y por que hubo
una correccion sobre la salida cruda del modelo.
"""

from sqlalchemy import text


def ensure_behavior_edits_schema(conn):
    """Crea la tabla on-demand para que la primera carga no rompa
    si la migracion no se corrio manualmente."""
    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS behavior_edits (
            id              SERIAL PRIMARY KEY,
            experiment_id   INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
            edited_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            edited_by_email TEXT,
            edited_role     TEXT,
            edited_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            before_open     FLOAT,
            before_closed   FLOAT,
            before_grooming FLOAT,
            before_thigmo   FLOAT,
            after_open      FLOAT,
            after_closed    FLOAT,
            after_grooming  FLOAT,
            after_thigmo    FLOAT,
            note            TEXT
        );
        """
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_behavior_edits_exp "
        "ON behavior_edits(experiment_id, edited_at DESC);"
    ))
    conn.commit()


def fetch_user_id_by_email(conn, email):
    if not email:
        return None
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :email LIMIT 1"),
        {"email": email},
    ).fetchone()
    return int(row[0]) if row else None


def record_behavior_edit(engine, *, experiment_id, before, after,
                         user_email=None, user_role=None, note=None):
    """Guarda un snapshot before/after de los tiempos editados.
    `before` y `after` son dicts con keys: open, closed, grooming, thigmo.
    """
    if not engine:
        return False, "No hay conexion a la base de datos."

    try:
        with engine.connect() as conn:
            ensure_behavior_edits_schema(conn)
            user_id = fetch_user_id_by_email(conn, user_email)
            conn.execute(
                text(
                    """
                    INSERT INTO behavior_edits (
                        experiment_id, edited_by, edited_by_email, edited_role,
                        before_open, before_closed, before_center,
                        before_grooming, before_thigmo,
                        after_open,  after_closed,  after_center,
                        after_grooming,  after_thigmo,
                        note
                    ) VALUES (
                        :exp_id, :user_id, :user_email, :user_role,
                        :b_open, :b_closed, :b_center, :b_groom, :b_thigmo,
                        :a_open, :a_closed, :a_center, :a_groom, :a_thigmo,
                        :note
                    )
                    """
                ),
                {
                    "exp_id": int(experiment_id),
                    "user_id": user_id,
                    "user_email": user_email,
                    "user_role": user_role,
                    "b_open":  float(before.get("open", 0.0) or 0.0),
                    "b_closed": float(before.get("closed", 0.0) or 0.0),
                    "b_center": float(before.get("center", 0.0) or 0.0),
                    "b_groom":  float(before.get("grooming", 0.0) or 0.0),
                    "b_thigmo": float(before.get("thigmo", 0.0) or 0.0),
                    "a_open":  float(after.get("open", 0.0) or 0.0),
                    "a_closed": float(after.get("closed", 0.0) or 0.0),
                    "a_center": float(after.get("center", 0.0) or 0.0),
                    "a_groom":  float(after.get("grooming", 0.0) or 0.0),
                    "a_thigmo": float(after.get("thigmo", 0.0) or 0.0),
                    "note": note,
                },
            )
            conn.commit()
        return True, "Edicion registrada en historial."
    except Exception as exc:
        return False, f"No se pudo registrar la edicion: {exc}"


def load_behavior_edits(engine, experiment_id):
    """Devuelve la lista de ediciones para un experimento, mas reciente primero."""
    if not engine:
        return []
    try:
        with engine.connect() as conn:
            ensure_behavior_edits_schema(conn)
            rows = conn.execute(
                text(
                    """
                    SELECT id, edited_by_email, edited_role, edited_at,
                           before_open, before_closed, before_center,
                           before_grooming, before_thigmo,
                           after_open,  after_closed,  after_center,
                           after_grooming,  after_thigmo,
                           note
                    FROM behavior_edits
                    WHERE experiment_id = :exp_id
                    ORDER BY edited_at DESC, id DESC
                    """
                ),
                {"exp_id": int(experiment_id)},
            ).mappings().all()
        return [dict(row) for row in rows]
    except Exception:
        return []


def count_behavior_edits(engine, experiment_id):
    edits = load_behavior_edits(engine, experiment_id)
    return len(edits)


def revert_to_before_snapshot(engine, edit_id):
    """Restaura `analysis_results` al estado before del edit indicado.
    El revert tambien queda registrado como una nueva edicion (con note='revert')."""
    if not engine:
        return False, "No hay conexion a la base de datos."

    try:
        with engine.connect() as conn:
            ensure_behavior_edits_schema(conn)
            row = conn.execute(
                text(
                    """
                    SELECT experiment_id,
                           before_open, before_closed, before_center,
                           before_grooming, before_thigmo,
                           after_open,  after_closed,  after_center,
                           after_grooming,  after_thigmo
                    FROM behavior_edits
                    WHERE id = :edit_id
                    """
                ),
                {"edit_id": int(edit_id)},
            ).mappings().fetchone()

            if not row:
                return False, f"No se encontro la edicion #{edit_id}."

            exp_id = int(row["experiment_id"])
            target = conn.execute(
                text(
                    """
                    SELECT id FROM analysis_results
                    WHERE experiment_id = :exp_id
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                ),
                {"exp_id": exp_id},
            ).fetchone()

            if not target:
                return False, f"El experimento #{exp_id} no tiene un registro de analysis_results."

            conn.execute(
                text(
                    """
                    UPDATE analysis_results
                    SET time_open_arms = :open_t,
                        time_closed_arms = :closed_t,
                        time_center = :center_t,
                        grooming_duration = :groom_t,
                        thigmotaxis_duration = :thigmo_t,
                        timestamp = CURRENT_TIMESTAMP
                    WHERE id = :analysis_id
                    """
                ),
                {
                    "open_t":  float(row["before_open"] or 0.0),
                    "closed_t": float(row["before_closed"] or 0.0),
                    "center_t": float(row["before_center"] or 0.0),
                    "groom_t":  float(row["before_grooming"] or 0.0),
                    "thigmo_t": float(row["before_thigmo"] or 0.0),
                    "analysis_id": int(target[0]),
                },
            )
            conn.commit()

        return True, f"Tiempos del experimento #{exp_id} restaurados al estado anterior."
    except Exception as exc:
        return False, f"No se pudo revertir: {exc}"
