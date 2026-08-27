PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'investigador'
        CHECK (role IN ('admin', 'investigador', 'Investigador', 'estudiante', 'Estudiante')),
    is_verified INTEGER NOT NULL DEFAULT 1,
    verification_code TEXT,
    verification_code_created_at TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    full_name TEXT,
    accepted_terms INTEGER NOT NULL DEFAULT 0,
    boleta TEXT,
    carrera TEXT,
    escuela TEXT,
    num_empleado TEXT,
    area TEXT,
    centro TEXT
);

CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rat_id TEXT NOT NULL,
    treatment TEXT NOT NULL,
    experiment_date DATE,
    responsible TEXT,
    video_path TEXT NOT NULL,
    duration_seconds REAL,
    created_by INTEGER REFERENCES users(id),
    processed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roi_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    zone_type TEXT NOT NULL,
    coordinates_json TEXT NOT NULL,
    scale_factor REAL
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_distance REAL DEFAULT 0.0,
    time_open_arms REAL DEFAULT 0.0,
    time_closed_arms REAL DEFAULT 0.0,
    time_center REAL DEFAULT 0.0,
    head_dips_count INTEGER DEFAULT 0,
    rearing_count INTEGER DEFAULT 0,
    grooming_duration REAL DEFAULT 0.0,
    thigmotaxis_duration REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    trajectory_path TEXT
);

CREATE TABLE IF NOT EXISTS security_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    username TEXT,
    ip_address TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    message TEXT,
    level TEXT DEFAULT 'INFO'
);

CREATE TABLE IF NOT EXISTS behavior_edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    edited_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    edited_by_email TEXT,
    edited_role TEXT,
    edited_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    before_open REAL,
    before_closed REAL,
    before_center REAL,
    before_grooming REAL,
    before_thigmo REAL,
    after_open REAL,
    after_closed REAL,
    after_center REAL,
    after_grooming REAL,
    after_thigmo REAL,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_username ON security_audit_log(username);
CREATE INDEX IF NOT EXISTS idx_audit_event ON security_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_behavior_edits_exp ON behavior_edits(experiment_id, edited_at DESC);
CREATE INDEX IF NOT EXISTS idx_experiments_video ON experiments(video_path);
CREATE INDEX IF NOT EXISTS idx_analysis_experiment ON analysis_results(experiment_id, timestamp DESC);
