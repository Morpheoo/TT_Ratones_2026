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

-- Insertar usuario admin inicial si no existe
INSERT INTO users (username, password_hash, role)
VALUES ('admin', 'pbkdf2:sha256:260000$....', 'admin') -- La contraseña real se generará desde Python
ON CONFLICT (username) DO NOTHING;
