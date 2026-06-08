from src.db.connection import get_db_engine
from sqlalchemy import text
import pandas as pd

def ejecutar_consulta_general():
    engine = get_db_engine()
    if not engine:
        print("ERROR: No se pudo conectar a la base de datos.")
        return

    with engine.connect() as conn:
        # 1. RESUMEN DE USUARIOS
        query1 = text("""
            SELECT 
                role AS categoria,
                COUNT(*) AS total,
                COUNT(CASE WHEN is_verified THEN 1 END) AS verificados,
                COUNT(CASE WHEN is_active THEN 1 END) AS activos
            FROM users
            GROUP BY role
            ORDER BY role;
        """)
        df1 = pd.read_sql(query1, conn)
        print(df1)
        print()

        # 2. TRATAMIENTOS DISPONIBLES
        query2 = text("""
            SELECT 
                t.name AS nombre,
                t.description AS descripcion,
                COUNT(e.id) AS num_experimentos,
                t.is_active AS activo
            FROM treatments t
            LEFT JOIN experiments e ON t.name = e.treatment
            GROUP BY t.id, t.name, t.description, t.is_active
            ORDER BY num_experimentos DESC;
        """)
        df2 = pd.read_sql(query2, conn)
        print(df2)
        print()

        # 3. RESUMEN DE EXPERIMENTOS POR USUARIO
        query3 = text("""
            SELECT 
                u.username AS usuario,
                u.role AS rol,
                COUNT(e.id) AS total_experimentos,
                COUNT(CASE WHEN e.processed THEN 1 END) AS procesados,
                COUNT(CASE WHEN NOT e.processed THEN 1 END) AS pendientes,
                ROUND(CAST(AVG(e.duration_seconds) AS NUMERIC), 2) AS duracion_promedio_seg
            FROM users u
            LEFT JOIN experiments e ON u.id = e.created_by
            GROUP BY u.id, u.username, u.role
            HAVING COUNT(e.id) > 0
            ORDER BY total_experimentos DESC;
        """)
        df3 = pd.read_sql(query3, conn)
        print(df3)
        print()

        # 4. ESTADO DE ANÁLISIS
        query4 = text("""
            SELECT 
                ar.status AS estado,
                COUNT(*) AS total,
                ROUND(CAST(AVG(ar.time_open_arms) AS NUMERIC), 2) AS promedio_brazos_abiertos,
                ROUND(CAST(AVG(ar.time_closed_arms) AS NUMERIC), 2) AS promedio_brazos_cerrados,
                ROUND(CAST(AVG(ar.grooming_duration) AS NUMERIC), 2) AS promedio_grooming,
                ROUND(CAST(AVG(ar.thigmotaxis_duration) AS NUMERIC), 2) AS promedio_thigmotaxis
            FROM analysis_results ar
            GROUP BY ar.status;
        """)
        df4 = pd.read_sql(query4, conn)
        print(df4)
        print()

        # 5. EXPERIMENTOS RECIENTES (ÚLTIMOS 10)
        query5 = text("""
            SELECT 
                e.id,
                e.rat_id AS raton,
                e.treatment AS tratamiento,
                e.experiment_date AS fecha,
                e.responsible AS responsable,
                ROUND(CAST(e.duration_seconds AS NUMERIC), 2) AS duracion_seg,
                e.processed AS procesado,
                ar.status AS estado_analisis,
                u.username AS creado_por
            FROM experiments e
            LEFT JOIN analysis_results ar ON e.id = ar.experiment_id
            LEFT JOIN users u ON e.created_by = u.id
            ORDER BY e.created_at DESC
            LIMIT 10;
        """)
        df5 = pd.read_sql(query5, conn)
        print(df5)
        print()

        # 6. CONFIGURACIONES DE ZONAS
        query6 = text("""
            SELECT 
                e.id AS experiment_id,
                e.rat_id AS raton,
                e.treatment AS tratamiento,
                COUNT(DISTINCT rc.zone_type) AS num_zonas_configuradas
            FROM experiments e
            LEFT JOIN roi_configurations rc ON e.id = rc.experiment_id
            WHERE rc.id IS NOT NULL
            GROUP BY e.id, e.rat_id, e.treatment
            ORDER BY e.id DESC
            LIMIT 10;
        """)
        df6 = pd.read_sql(query6, conn)
        print(df6)
        print()

        # 7. AUDITORÍA DE EDICIONES MANUALES
        query7 = text("""
            SELECT 
                be.experiment_id,
                be.edited_by_email AS editor,
                be.edited_role AS rol_editor,
                be.edited_at AS fecha_edicion,
                be.note AS nota
            FROM behavior_edits be
            ORDER BY be.edited_at DESC
            LIMIT 10;
        """)
        df7 = pd.read_sql(query7, conn)
        print(df7)
        print()

        # 8. LOG DE SEGURIDAD (EVENTOS RECIENTES)
        query8 = text("""
            SELECT 
                sal.event_type AS tipo_evento,
                sal.username AS usuario,
                sal.success AS exitoso,
                sal.message AS mensaje,
                sal.timestamp AS fecha
            FROM security_audit_log sal
            ORDER BY sal.timestamp DESC
            LIMIT 15;
        """)
        df8 = pd.read_sql(query8, conn)
        print(df8)
        print()

        # 9. ESTADÍSTICAS GLOBALES
        query9 = text("""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE is_active = TRUE) AS usuarios_activos,
                (SELECT COUNT(*) FROM experiments) AS total_experimentos,
                (SELECT COUNT(*) FROM experiments WHERE processed = TRUE) AS experimentos_procesados,
                (SELECT COUNT(*) FROM analysis_results WHERE status = 'completed') AS analisis_completados,
                (SELECT COUNT(*) FROM treatments WHERE is_active = TRUE) AS tratamientos_activos,
                (SELECT COUNT(DISTINCT experiment_id) FROM roi_configurations) AS experimentos_con_zonas,
                (SELECT ROUND(CAST(SUM(duration_seconds)/3600 AS NUMERIC), 2) FROM experiments) AS total_horas_video;
        """)
        df9 = pd.read_sql(query9, conn)
        print(df9)

if __name__ == "__main__":
    ejecutar_consulta_general()
