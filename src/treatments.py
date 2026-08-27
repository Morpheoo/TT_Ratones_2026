"""
Módulo para gestión de tratamientos en el prototipo EPM
"""
from sqlalchemy import text
from src.db.connection import get_db_engine
from src.db.dialect import is_sqlite


def initialize_treatments_table():
    """Crea la tabla de tratamientos si no existe."""
    engine = get_db_engine()
    if not engine:
        return False
    
    with engine.connect() as conn:
        with conn.begin():
            id_definition = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite(conn) else "SERIAL PRIMARY KEY"
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS treatments (
                    id {id_definition},
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """))
            
            # Insertar tratamientos por defecto si la tabla está vacía
            result = conn.execute(text("SELECT COUNT(*) FROM treatments"))
            count = result.scalar()
            
            if count == 0:
                default_treatments = [
                    "Control",
                    "Diazepam 5mg",
                    "Diazepam 10mg",
                    "Cafeína 50mg",
                    "Estrés por restricción"
                ]
                for treatment in default_treatments:
                    conn.execute(text("""
                        INSERT INTO treatments (name, description, is_active)
                        VALUES (:name, :desc, TRUE)
                    """), {"name": treatment, "desc": f"Tratamiento: {treatment}"})
    
    return True


def get_all_treatments():
    """Obtiene todos los tratamientos activos."""
    engine = get_db_engine()
    if not engine:
        return []
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, name, description 
            FROM treatments 
            WHERE is_active = TRUE 
            ORDER BY name ASC
        """))
        return [{"id": row[0], "name": row[1], "description": row[2]} for row in result]


def add_treatment(name, description="", created_by=None):
    """Añade un nuevo tratamiento."""
    engine = get_db_engine()
    if not engine:
        return False, "Error de conexión a la base de datos"
    
    name = name.strip()
    if not name:
        return False, "El nombre del tratamiento no puede estar vacío"
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Verificar si ya existe
                result = conn.execute(
                    text("SELECT id FROM treatments WHERE LOWER(name) = LOWER(:name)"),
                    {"name": name}
                )
                if result.fetchone():
                    return False, "Este tratamiento ya existe"
                
                # Insertar nuevo tratamiento
                conn.execute(text("""
                    INSERT INTO treatments (name, description, created_by, is_active)
                    VALUES (:name, :desc, :creator, TRUE)
                """), {"name": name, "desc": description, "creator": created_by})
        
        return True, "Tratamiento añadido exitosamente"
    
    except Exception as e:
        return False, f"Error al añadir tratamiento: {str(e)}"


def delete_treatment(treatment_id):
    """Elimina (desactiva) un tratamiento."""
    engine = get_db_engine()
    if not engine:
        return False, "Error de conexión a la base de datos"
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Verificar si el tratamiento está en uso
                result = conn.execute(
                    text("SELECT COUNT(*) FROM experiments WHERE treatment = (SELECT name FROM treatments WHERE id = :tid)"),
                    {"tid": treatment_id}
                )
                count = result.scalar()
                
                if count > 0:
                    # Desactivar en lugar de eliminar si está en uso
                    conn.execute(
                        text("UPDATE treatments SET is_active = FALSE WHERE id = :tid"),
                        {"tid": treatment_id}
                    )
                    return True, f"Tratamiento desactivado (en uso en {count} experimento(s))"
                else:
                    # Eliminar completamente si no está en uso
                    conn.execute(
                        text("DELETE FROM treatments WHERE id = :tid"),
                        {"tid": treatment_id}
                    )
                    return True, "Tratamiento eliminado exitosamente"
        
    except Exception as e:
        return False, f"Error al eliminar tratamiento: {str(e)}"


def get_treatment_by_name(name):
    """Obtiene un tratamiento por nombre."""
    engine = get_db_engine()
    if not engine:
        return None
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name, description FROM treatments WHERE name = :name AND is_active = TRUE"),
            {"name": name}
        )
        row = result.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "description": row[2]}
    return None
