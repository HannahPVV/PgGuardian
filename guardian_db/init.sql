-- BD PgGuardian

--Snapshots
CREATE TABLE IF NOT EXISTS snapshots (
    id          SERIAL PRIMARY KEY,
    taken_at    TIMESTAMP DEFAULT NOW(),
    db_name     TEXT NOT NULL,        -- Nombre de la BD auditada (TiendaDB)
    db_host     TEXT NOT NULL        -- IP o Host del cliente
);

-- Hallazgos: problemas detectados
CREATE TABLE IF NOT EXISTS findings (
    id            SERIAL PRIMARY KEY,
    snapshot_id   INT REFERENCES snapshots(id) ON DELETE CASCADE,
    problem_code  VARCHAR(10) NOT NULL,
    category      TEXT NOT NULL,        
    severity      TEXT NOT NULL,       
    title         TEXT NOT NULL,        
    description   TEXT,                 
    table_name    TEXT,                 
    evidence_sql  TEXT,                 -- La prueba
    fix_sql       TEXT,                 -- La solución
    is_resolved   BOOLEAN DEFAULT FALSE,
    detected_at   TIMESTAMP DEFAULT NOW()
);

-- Reportes:  resumen para el Dashboard y el PDF
CREATE TABLE IF NOT EXISTS reports (
    id            SERIAL PRIMARY KEY,
    snapshot_id   INT REFERENCES snapshots(id) ON DELETE CASCADE,
    created_at    TIMESTAMP DEFAULT NOW(),
    report_path   TEXT,                 -- Ruta del archivo PDF generado
    total_high    INT DEFAULT 0,
    total_medium  INT DEFAULT 0,
    total_low     INT DEFAULT 0
);

-- Consultas eficientes para el Dashboard
-- Buscar auditorías por nombre y ver la más reciente arriba
CREATE INDEX IF NOT EXISTS idx_snapshots_db_search 
    ON snapshots(db_name, taken_at DESC);

-- hallazgos con su snapshot
CREATE INDEX IF NOT EXISTS idx_findings_snapshot 
    ON findings(snapshot_id);

