-- ============================================================
-- PLC + MES + TIMESERIES FULL SCHEMA (WITH PART_ID)
-- PostgreSQL + TimescaleDB
-- ============================================================

-- ============================================================
-- 0. DATABASE
-- ============================================================
CREATE DATABASE plc;
\c plc;


CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- 2. PLC EVENTS (RAW TIME SERIES + PART_ID)
-- ============================================================
CREATE TABLE plc_events (
    ts          timestamptz NOT NULL,
    part_id     text,                  -- RFID / Datamatrix / UUID piece
    machine     text        NOT NULL,   -- M1..M5
    level       text        NOT NULL,   -- INFO / OK / ERROR
    code        text,
    message     text,
    cycle       integer,
    step_id     text,
    step_name   text,
    duration    NUMERIC,
    payload     jsonb
);

-- Index time-series
CREATE INDEX idx_plc_events_ts ON plc_events(ts);
CREATE INDEX idx_plc_events_part_ts ON plc_events(part_id, ts);
CREATE INDEX idx_plc_events_machine_ts ON plc_events(machine, ts);
CREATE INDEX idx_plc_events_cycle ON plc_events(cycle);
CREATE INDEX idx_plc_events_step ON plc_events(step_id);
CREATE INDEX idx_plc_events_level ON plc_events(level);
CREATE INDEX idx_plc_events_json ON plc_events USING gin(payload);

-- Hypertable
SELECT create_hypertable('plc_events', 'ts', if_not_exists => TRUE);


-- ============================================================
-- 3. MES STRUCTURE (NOMINAL)
-- ============================================================

-- 3.1 Industrial line
CREATE TABLE industrial_line (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    cycle_nominal_s INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- 3.2 Machine
CREATE TABLE machine (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    ip_address INET,
    plc_protocol TEXT,
    opcua_endpoint TEXT,
    line_id INTEGER NOT NULL REFERENCES industrial_line(id),
    order_index INTEGER NOT NULL,
    nominal_duration_s INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- 3.3 Production steps (GRAFCET)
CREATE TABLE production_step (
    id SERIAL PRIMARY KEY,
    step_code VARCHAR(10) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    machine_id INTEGER REFERENCES machine(id),
    is_technical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now()
);

-- 3.4 Step transitions
CREATE TABLE step_transition (
    id SERIAL PRIMARY KEY,
    from_step_id INTEGER REFERENCES production_step(id),
    to_step_id INTEGER REFERENCES production_step(id),
    condition TEXT NOT NULL,
    is_error BOOLEAN DEFAULT FALSE
);

-- 3.5 Part (logical MES part)
CREATE TABLE part (
    id SERIAL PRIMARY KEY,
    external_part_id TEXT UNIQUE NOT NULL,  -- match plc_events.part_id
    line_id INTEGER NOT NULL REFERENCES industrial_line(id),
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    created_at TIMESTAMP DEFAULT now(),
    finished_at TIMESTAMP
);

-- ============================================================
-- 4. EXECUTION (MES LOGIQUE)
-- ============================================================

-- 4.1 Part step execution (MES level)
CREATE TABLE part_step_execution (
    id SERIAL PRIMARY KEY,
    part_id INTEGER NOT NULL REFERENCES part(id),
    step_id INTEGER NOT NULL REFERENCES production_step(id),
    machine_id INTEGER REFERENCES machine(id),

    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_s INTEGER,

    status TEXT NOT NULL,
    success_code TEXT,
    error_code TEXT,

    created_at TIMESTAMP DEFAULT now()
);

-- 4.2 Machine internal step definition
CREATE TABLE machine_step_definition (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machine(id),
    step_code VARCHAR(20) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    step_order INTEGER NOT NULL
);

-- 4.3 Machine step execution (micro-steps)
CREATE TABLE machine_step_execution (
    id SERIAL PRIMARY KEY,
    part_step_execution_id INTEGER NOT NULL REFERENCES part_step_execution(id),
    machine_step_id INTEGER NOT NULL REFERENCES machine_step_definition(id),

    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_ms INTEGER,

    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- ============================================================
-- 5. BRIDGE PLC → MES (REAL TIME, PART AWARE)
-- ============================================================

-- 5.1 PLC events enriched with MES machine + part
CREATE VIEW v_plc_events_enriched AS
SELECT
    e.ts,
    p.id AS mes_part_id,
    e.part_id AS plc_part_id,
    e.machine,
    m.id AS machine_id,
    e.level,
    e.code,
    e.message,
    e.cycle,
    e.step_id,
    e.step_name,
    e.duration,
    e.payload
FROM plc_events e
JOIN machine m ON m.code = e.machine
LEFT JOIN part p ON p.external_part_id = e.part_id;

-- 5.2 Real machine step execution (from PLC)
CREATE VIEW v_real_machine_step_execution AS
SELECT
    mes_part_id,
    plc_part_id,
    machine_id,
    machine,
    step_id,
    step_name,
    cycle,
    MIN(ts) AS start_time,
    MAX(ts) AS end_time,
    EXTRACT(EPOCH FROM (MAX(ts) - MIN(ts))) AS real_duration_s
FROM v_plc_events_enriched
WHERE level IN ('INFO', 'OK')
GROUP BY mes_part_id, plc_part_id, machine_id, machine, step_id, step_name, cycle;

-- 5.3 Real machine cycle per part
CREATE VIEW v_real_machine_cycle_time AS
SELECT
    mes_part_id,
    plc_part_id,
    machine_id,
    machine AS machine_code,
    cycle,
    MIN(start_time) AS cycle_start,
    MAX(end_time)   AS cycle_end,
    SUM(real_duration_s) AS real_cycle_time_s
FROM v_real_machine_step_execution
GROUP BY mes_part_id, plc_part_id, machine_id, machine, cycle;

-- ============================================================
-- 6. NOMINAL vs REAL (PART + MACHINE)
-- ============================================================

CREATE VIEW v_machine_nominal_vs_real AS
SELECT
    r.mes_part_id,
    r.plc_part_id,
    r.machine_id,
    r.machine_code,
    r.cycle,
    r.cycle_start,

    m.nominal_duration_s,
    r.real_cycle_time_s,

    (r.real_cycle_time_s - m.nominal_duration_s) AS delta_s,

    CASE
        WHEN r.real_cycle_time_s <= m.nominal_duration_s THEN 'OK'
        WHEN r.real_cycle_time_s <= m.nominal_duration_s * 1.10 THEN 'WARNING'
        ELSE 'DRIFT'
    END AS status
FROM v_real_machine_cycle_time r
JOIN machine m ON m.id = r.machine_id;

-- ============================================================
-- 7. CONTINUOUS AGGREGATES (PART AWARE)
-- ============================================================

-- 7.1 Cycles completed
CREATE MATERIALIZED VIEW cycle_times
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    COUNT(*) FILTER (WHERE message ILIKE '%CYCLE_END%') AS cycles_completed
FROM plc_events
GROUP BY bucket
WITH NO DATA;

-- 7.2 Machine errors
CREATE MATERIALIZED VIEW machine_errors
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    machine,
    COUNT(*) FILTER (WHERE level='ERROR') AS errors
FROM plc_events
GROUP BY bucket, machine
WITH NO DATA;

-- 7.3 Machine cycle duration
CREATE MATERIALIZED VIEW machine_cycle_time_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    machine,
    AVG(duration) AS avg_step_duration,
    MAX(duration) AS max_step_duration
FROM plc_events
WHERE duration IS NOT NULL
GROUP BY bucket, machine
WITH NO DATA;

-- ============================================================
-- 8. CONTINUOUS AGGREGATE POLICIES
-- ============================================================

SELECT add_continuous_aggregate_policy('cycle_times',
    start_offset => INTERVAL '1 day',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');

SELECT add_continuous_aggregate_policy('machine_errors',
    start_offset => INTERVAL '1 day',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');

SELECT add_continuous_aggregate_policy('machine_cycle_time_1min',
    start_offset => INTERVAL '1 day',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');

-- ============================================================
-- 9. MACHINE DEPHASING (PART AWARE)
-- ============================================================

CREATE VIEW v_machine_dephasing AS
SELECT
    a.plc_part_id,
    a.cycle,
    a.machine AS machine_from,
    b.machine AS machine_to,
    b.ts - a.ts AS delta,
    CASE
        WHEN b.ts - a.ts > INTERVAL '200 milliseconds'
        THEN 'DEPHASAGE'
        ELSE 'OK'
    END AS status
FROM v_plc_events_enriched a
JOIN v_plc_events_enriched b
  ON a.cycle = b.cycle
 AND a.plc_part_id = b.plc_part_id
WHERE a.level='OK'
  AND b.level='OK';


CREATE TABLE plc_anomalies (
    id SERIAL PRIMARY KEY,
    -- Identité industrielle
    event_ts  timestamptz NOT NULL,
    part_id TEXT,
    ts_detected TIMESTAMPTZ NOT NULL DEFAULT now(),
    cycle INTEGER NOT NULL,
    machine TEXT NOT NULL,
    step_id TEXT,
    step_name TEXT,

    -- Détection
    anomaly_score DOUBLE PRECISION,
    rule_anomaly BOOLEAN NOT NULL,
    rule_reasons JSONB,

    -- STEP
    has_step_error BOOLEAN DEFAULT FALSE,
    n_step_errors INTEGER DEFAULT 0,

    -- Cycle
    cycle_duration_s DOUBLE PRECISION,
    duration_overrun_s DOUBLE PRECISION,

    -- Prédictif
    events_count INTEGER,
    window_days INTEGER,
    ewma_ratio DOUBLE PRECISION,
    rate_ratio DOUBLE PRECISION,
    burstiness DOUBLE PRECISION,
    hawkes_score INTEGER,
    confidence TEXT,

    -- Statut métier
    status TEXT DEFAULT 'OPEN',   -- OPEN / ACK / CLOSED
    severity TEXT,                -- INFO / WATCH / CRITICAL

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    report_path TEXT
);



  --- INSERT ---

  -- ============================================================
-- INSERT WORKFLOW NOMINAL - LIGNE 5 MACHINES
-- ============================================================

-- ============================================================
-- 1. INDUSTRIAL LINE
-- ============================================================
INSERT INTO industrial_line (name, cycle_nominal_s)
VALUES ('Ligne 5 machines - Usinage complet', 90);

-- ============================================================
-- 2. MACHINES
-- ============================================================
INSERT INTO machine (code, name, description, ip_address, plc_protocol, opcua_endpoint, line_id, order_index, nominal_duration_s)
VALUES
('M1', 'M1 - Chargement & Préparation',
 'Module d’alimentation avec convoyeur, alignement et serrage.',
 '192.168.10.11', 'Profinet', 'opc.tcp://M1-loader:4840',
 (SELECT id FROM industrial_line WHERE name='Ligne 5 machines - Usinage complet'),
 1, 8),

('M2', 'M2 - Usinage Ébauche',
 'Centre d’usinage pour l’ébauche de la pièce.',
 '192.168.10.12', 'Profinet', 'opc.tcp://M2-rough:4840',
 (SELECT id FROM industrial_line WHERE name='Ligne 5 machines - Usinage complet'),
 2, 28),

('M3', 'M3 - Usinage Finition',
 'Centre d’usinage finition pour tolérances serrées.',
 '192.168.10.13', 'Profinet', 'opc.tcp://M3-finish:4840',
 (SELECT id FROM industrial_line WHERE name='Ligne 5 machines - Usinage complet'),
 3, 18),

('M4', 'M4 - Perçage & Taraudage',
 'Module multi-outils pour perçage et taraudage.',
 '192.168.10.14', 'Profinet', 'opc.tcp://M4-drill:4840',
 (SELECT id FROM industrial_line WHERE name='Ligne 5 machines - Usinage complet'),
 4, 18),

('M5', 'M5 - Contrôle & Déchargement',
 'Module de vision, mesure, décision qualité et déchargement.',
 '192.168.10.15', 'Profinet', 'opc.tcp://M5-inspect:4840',
 (SELECT id FROM industrial_line WHERE name='Ligne 5 machines - Usinage complet'),
 5, 12);

-- ============================================================
-- 3. GRAFCET STEPS
-- ============================================================
INSERT INTO production_step (step_code, name, description, machine_id) VALUES
('M1.01','WAIT_ENTRY','Attente d’une pièce à l’entrée.',1),
('M1.02','CONVEY_IN','Convoyage de la pièce en zone de travail.',1),
('M1.03','DETECT_PIECE','Capteur confirme la présence pièce.',1),
('M1.04','SLOW_ALIGN','Alignement longitudinal fin.',1),
('M1.05','SIDE_ALIGNMENT','Alignement latéral.',1),
('M1.06','CLAMP_CLOSE','Commande serrage étau/pince.',1),
('M1.07','CLAMP_VERIFY','Contrôle pression / fin de course clamp.',1),
('M1.08','ID_READ','Lecture code Datamatrix/RFID.',1),
('M1.09','POSITION_CHECK','Vérification position X/Y/Z.',1),
('M1.10','READY_SIGNAL','Émission signal M1_READY_FOR_M2.',1);

INSERT INTO production_step (step_code, name, description, machine_id) VALUES
('M2.01','WAIT_M1_READY','Attente signal M1_READY_FOR_M2.',2),
('M2.02','FIXTURE_LOCK','Verrouillage pièce sur la table.',2),
('M2.03','TOOL_CHECK','Contrôle outil présent.',2),
('M2.04','SPINDLE_RAMP_UP','Montée en vitesse broche ébauche.',2),
('M2.05','COOLANT_ON','Ouverture arrosage.',2),
('M2.06','APPROACH_POS','Approche position usinage.',2),
('M2.07','ROUGH_PASS_1','Première passe d’ébauche.',2),
('M2.08','ROUGH_PASS_2','Deuxième passe d’ébauche.',2),
('M2.09','TOOLWEAR_CHECK','Contrôle usure outil.',2),
('M2.10','RETURN_SAFE_POS','Retour position sûre.',2),
('M2.11','SPINDLE_STOP','Arrêt broche.',2),
('M2.12','CHIP_CLEAN','Évacuation copeaux.',2),
('M2.13','DONE_SIGNAL','Émission signal M2_DONE.',2);

INSERT INTO production_step (step_code, name, description, machine_id) VALUES
('M3.01','WAIT_M2_DONE','Attente signal M2_DONE.',3),
('M3.02','FINE_FIXTURE_CHECK','Vérification montage précision.',3),
('M3.03','TOOL_VERIFY_FINISH','Contrôle outil finition.',3),
('M3.04','SPINDLE_FINE_RAMP','Montée vitesse finition.',3),
('M3.05','APPROACH_FINISH','Approche zone finition.',3),
('M3.06','FINISH_PASS_1','Première passe finition.',3),
('M3.07','FINISH_PASS_2','Deuxième passe finition.',3),
('M3.08','SURFACE_SENSOR_CHECK','Contrôle état surface.',3),
('M3.09','OPTIONAL_PROBE','Palpage dimensionnel.',3),
('M3.10','CLEAN_AIR','Soufflage final.',3),
('M3.11','DONE_SIGNAL','Émission signal M3_DONE.',3);

INSERT INTO production_step (step_code, name, description, machine_id) VALUES
('M4.01','WAIT_M3_DONE','Attente signal M3_DONE.',4),
('M4.02','TOOL_SELECT_DRILL','Sélection foret.',4),
('M4.03','DRILL_APPROACH','Approche perçage.',4),
('M4.04','DRILL_EXEC','Exécution perçage.',4),
('M4.05','DRILL_RETRACT','Retrait foret.',4),
('M4.06','TOOL_SELECT_TAP','Sélection taraud.',4),
('M4.07','TAP_ENGAGE','Engagement taraud.',4),
('M4.08','TAP_MONITOR_TORQUE','Surveillance couple.',4),
('M4.09','TAP_RETRACT','Sortie taraud.',4),
('M4.10','HOLE_CLEAN','Nettoyage trou.',4),
('M4.11','DONE_SIGNAL','Émission signal M4_DONE.',4);

INSERT INTO production_step (step_code, name, description, machine_id) VALUES
('M5.01','WAIT_M4_DONE','Attente signal M4_DONE.',5),
('M5.02','RECEIVE_PART','Réception pièce.',5),
('M5.03','VISION_TRIGGER','Déclenchement vision.',5),
('M5.04','ACQ_2D','Acquisition images 2D.',5),
('M5.05','ACQ_3D','Scan 3D.',5),
('M5.06','FEATURE_MEASURE','Mesure caractéristiques.',5),
('M5.07','COMPARE_SPECS','Comparaison tolérances.',5),
('M5.08','LIGHT_DEBURR','Ébavurage léger.',5),
('M5.09','UNCLAMP','Déverrouillage pièce.',5),
('M5.10','UNLOAD_TO_BIN','Déchargement bac.',5),
('M5.11','LOG_RESULT','Enregistrement résultat.',5);

ALTER TABLE production_step
ADD CONSTRAINT uq_production_step_code UNIQUE (step_code);

-- ============================================================
-- 4. GRAFCET TRANSITIONS
-- ============================================================
INSERT INTO step_transition (from_step_id, to_step_id, condition)
VALUES
((SELECT id FROM production_step WHERE step_code='S0'),
 (SELECT id FROM production_step WHERE step_code='S1'),
 'SAFETY_OK && START_CMD'),

((SELECT id FROM production_step WHERE step_code='S1'),
 (SELECT id FROM production_step WHERE step_code='S2'),
 'S-M1-005 (M1_READY_OK)'),

((SELECT id FROM production_step WHERE step_code='S2'),
 (SELECT id FROM production_step WHERE step_code='S3'),
 'S-M2-004 (M2_DONE_OK)'),

((SELECT id FROM production_step WHERE step_code='S3'),
 (SELECT id FROM production_step WHERE step_code='S4'),
 'S-M3-004 (M3_DONE_OK)'),

((SELECT id FROM production_step WHERE step_code='S4'),
 (SELECT id FROM production_step WHERE step_code='S5'),
 'S-M4-003 (M4_DONE_OK)'),

((SELECT id FROM production_step WHERE step_code='S5'),
 (SELECT id FROM production_step WHERE step_code='S6'),
 'S-M5-004 (UNLOAD_OK)'),

((SELECT id FROM production_step WHERE step_code='S6'),
 (SELECT id FROM production_step WHERE step_code='S1'),
 'NEXT_CYCLE_REQUIRED');

-- ============================================================
-- 5. MACHINE MICRO-STEPS (INTERNAL STEPS)
-- ============================================================

-- ---------- M1 ----------
INSERT INTO machine_step_definition (machine_id, step_code, name, description, step_order)
SELECT id, v.step_code, v.name, v.description, v.step_order
FROM machine m
JOIN (
    VALUES
    ('M1.01','WAIT_ENTRY','Attente d’une pièce à l’entrée.',1),
    ('M1.02','CONVEY_IN','Convoyage de la pièce.',2),
    ('M1.03','DETECT_PIECE','Détection pièce.',3),
    ('M1.04','SLOW_ALIGN','Alignement longitudinal.',4),
    ('M1.05','SIDE_ALIGNMENT','Alignement latéral.',5),
    ('M1.06','CLAMP_CLOSE','Fermeture clamp.',6),
    ('M1.07','CLAMP_VERIFY','Vérification clamp.',7),
    ('M1.08','ID_READ','Lecture ID.',8),
    ('M1.09','POSITION_CHECK','Contrôle position.',9),
    ('M1.10','READY_SIGNAL','Signal prêt.',10)
) v(step_code, name, description, step_order)
ON m.code='M1';

-- ---------- M2 ----------
INSERT INTO machine_step_definition (machine_id, step_code, name, description, step_order)
SELECT id, v.step_code, v.name, v.description, v.step_order
FROM machine m
JOIN (
    VALUES
    ('M2.01','WAIT_M1_READY','Attente M1 prêt.',1),
    ('M2.02','FIXTURE_LOCK','Verrouillage pièce.',2),
    ('M2.03','TOOL_CHECK','Contrôle outil.',3),
    ('M2.04','SPINDLE_RAMP_UP','Montée broche.',4),
    ('M2.05','COOLANT_ON','Arrosage ON.',5),
    ('M2.06','APPROACH_POS','Approche position.',6),
    ('M2.07','ROUGH_PASS_1','Passe rough 1.',7),
    ('M2.08','ROUGH_PASS_2','Passe rough 2.',8),
    ('M2.09','TOOLWEAR_CHECK','Contrôle usure.',9),
    ('M2.10','RETURN_SAFE_POS','Retour sécurité.',10),
    ('M2.11','SPINDLE_STOP','Arrêt broche.',11),
    ('M2.12','CHIP_CLEAN','Nettoyage copeaux.',12),
    ('M2.13','DONE_SIGNAL','Signal fin.',13)
) v(step_code, name, description, step_order)
ON m.code='M2';

-- ---------- M3 ----------
INSERT INTO machine_step_definition (machine_id, step_code, name, description, step_order)
SELECT id, v.step_code, v.name, v.description, v.step_order
FROM machine m
JOIN (
    VALUES
    ('M3.01','WAIT_M2_DONE','Attente M2.',1),
    ('M3.02','FINE_FIXTURE_CHECK','Contrôle montage.',2),
    ('M3.03','TOOL_VERIFY_FINISH','Contrôle outil.',3),
    ('M3.04','SPINDLE_FINE_RAMP','Montée broche.',4),
    ('M3.05','APPROACH_FINISH','Approche.',5),
    ('M3.06','FINISH_PASS_1','Passe finition 1.',6),
    ('M3.07','FINISH_PASS_2','Passe finition 2.',7),
    ('M3.08','SURFACE_SENSOR_CHECK','Contrôle surface.',8),
    ('M3.09','OPTIONAL_PROBE','Palpage.',9),
    ('M3.10','CLEAN_AIR','Soufflage.',10),
    ('M3.11','DONE_SIGNAL','Signal fin.',11)
) v(step_code, name, description, step_order)
ON m.code='M3';

-- ---------- M4 ----------
INSERT INTO machine_step_definition (machine_id, step_code, name, description, step_order)
SELECT id, v.step_code, v.name, v.description, v.step_order
FROM machine m
JOIN (
    VALUES
    ('M4.01','WAIT_M3_DONE','Attente M3.',1),
    ('M4.02','TOOL_SELECT_DRILL','Sélection foret.',2),
    ('M4.03','DRILL_APPROACH','Approche perçage.',3),
    ('M4.04','DRILL_EXEC','Perçage.',4),
    ('M4.05','DRILL_RETRACT','Retrait foret.',5),
    ('M4.06','TOOL_SELECT_TAP','Sélection taraud.',6),
    ('M4.07','TAP_ENGAGE','Engagement taraud.',7),
    ('M4.08','TAP_MONITOR_TORQUE','Surveillance couple.',8),
    ('M4.09','TAP_RETRACT','Retrait taraud.',9),
    ('M4.10','HOLE_CLEAN','Nettoyage trou.',10),
    ('M4.11','DONE_SIGNAL','Signal fin.',11)
) v(step_code, name, description, step_order)
ON m.code='M4';

-- ---------- M5 ----------
INSERT INTO machine_step_definition (machine_id, step_code, name, description, step_order)
SELECT id, v.step_code, v.name, v.description, v.step_order
FROM machine m
JOIN (
    VALUES
    ('M5.01','WAIT_M4_DONE','Attente M4.',1),
    ('M5.02','RECEIVE_PART','Réception pièce.',2),
    ('M5.03','VISION_TRIGGER','Déclenche caméra.',3),
    ('M5.04','ACQ_2D','Acquisition 2D.',4),
    ('M5.05','ACQ_3D','Scan 3D.',5),
    ('M5.06','FEATURE_MEASURE','Mesure cotes.',6),
    ('M5.07','COMPARE_SPECS','Comparaison specs.',7),
    ('M5.08','LIGHT_DEBURR','Ébavurage.',8),
    ('M5.09','UNCLAMP','Déverrouillage.',9),
    ('M5.10','UNLOAD_TO_BIN','Déchargement.',10),
    ('M5.11','LOG_RESULT','Log résultat.',11)
) v(step_code, name, description, step_order)
ON m.code='M5';

