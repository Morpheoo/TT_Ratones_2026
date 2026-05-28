-- Tabla de Usuarios
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) CHECK (role IN ('admin', 'investigador', 'Investigador', 'estudiante', 'Estudiante')) DEFAULT 'investigador',
    is_verified BOOLEAN DEFAULT FALSE,
    verification_code VARCHAR(6),
    verification_code_created_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Tratamientos
CREATE TABLE IF NOT EXISTS treatments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Tabla de Experimentos
CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,
    rat_id VARCHAR(50) NOT NULL,
    treatment VARCHAR(50) NOT NULL,
    experiment_date DATE,
    responsible VARCHAR(100),
    video_path TEXT NOT NULL,
    duration_seconds FLOAT,
    created_by INTEGER REFERENCES users(id),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuración de Zonas (ROIs)
CREATE TABLE IF NOT EXISTS roi_configurations (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    zone_type VARCHAR(50) NOT NULL, -- 'Brazo Abierto', 'Brazo Cerrado', 'Centro'
    coordinates_json JSONB NOT NULL, -- {x, y, w, h}
    scale_factor FLOAT
);

-- Resultados de Análisis IA
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_distance FLOAT DEFAULT 0.0,
    time_open_arms FLOAT DEFAULT 0.0,
    time_closed_arms FLOAT DEFAULT 0.0,
    time_center FLOAT DEFAULT 0.0,
    head_dips_count INTEGER DEFAULT 0,
    rearing_count INTEGER DEFAULT 0,
    grooming_duration FLOAT DEFAULT 0.0,
    thigmotaxis_duration FLOAT DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'pending'
);

-- ─────────────────────────────────────────────
-- Tabla de Auditoría de Seguridad
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS security_audit_log (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    event_type  VARCHAR(50)  NOT NULL,
    username    VARCHAR(100),
    ip_address  VARCHAR(45),
    success     BOOLEAN DEFAULT TRUE,
    message     TEXT,
    level       VARCHAR(10)  DEFAULT 'INFO'
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON security_audit_log (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_username
    ON security_audit_log (username);

CREATE INDEX IF NOT EXISTS idx_audit_event
    ON security_audit_log (event_type);

-- Columnas extendidas de perfil (idempotente para DBs existentes)
-- Estas columnas las agrega register_user() en el INSERT, asi que deben
-- existir antes del primer registro.
-- Comunes:
ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS accepted_terms BOOLEAN DEFAULT FALSE;
-- Especificos de ESTUDIANTE (@alumno.ipn.mx):
ALTER TABLE users ADD COLUMN IF NOT EXISTS boleta VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS carrera VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS escuela VARCHAR(100);
-- Especificos de INVESTIGADOR/DOCENTE (@ipn.mx):
ALTER TABLE users ADD COLUMN IF NOT EXISTS num_empleado VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS area VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS centro VARCHAR(100);

-- NOTA: no se inserta ningun usuario admin inicial via SQL porque el
-- hash bcrypt requiere generarse desde Python. La promocion a admin
-- se hace automaticamente cuando un email de la lista ADMIN_EMAILS
-- (definida en src/auth.py) se registra a traves de la UI.

-- ─────────────────────────────────────────────
-- Tabla de Auditoria de Ediciones Manuales de Tiempos Conductuales
-- ─────────────────────────────────────────────
-- Cada vez que un usuario corrige los segundos de Abiertos/Cerrados/
-- Centro/Grooming/Thigmotaxis en la pagina 05, guardamos snapshot
-- before/after para trazabilidad y posible reversion.
CREATE TABLE IF NOT EXISTS behavior_edits (
    id              SERIAL PRIMARY KEY,
    experiment_id   INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    edited_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    edited_by_email TEXT,
    edited_role     TEXT,
    edited_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    before_open     FLOAT,
    before_closed   FLOAT,
    before_center   FLOAT,
    before_grooming FLOAT,
    before_thigmo   FLOAT,
    after_open      FLOAT,
    after_closed    FLOAT,
    after_center    FLOAT,
    after_grooming  FLOAT,
    after_thigmo    FLOAT,
    note            TEXT
);

CREATE INDEX IF NOT EXISTS idx_behavior_edits_exp
    ON behavior_edits(experiment_id, edited_at DESC);

-- Upgrade idempotente para DBs creadas con la migration vieja
-- (add_behavior_edits.py) que no incluia las columnas _center.
ALTER TABLE behavior_edits ADD COLUMN IF NOT EXISTS before_center FLOAT;
ALTER TABLE behavior_edits ADD COLUMN IF NOT EXISTS after_center FLOAT;
