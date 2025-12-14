# Centralize SQL here.

PARTS_COUNT = """
SELECT COUNT(*)::bigint AS total
FROM part;
"""

PARTS_PAGE = """
SELECT
  external_part_id AS part_id,
  status,
  created_at,
  finished_at
FROM part
ORDER BY created_at DESC
LIMIT %s OFFSET %s;
"""

MACHINES_LIVE = """
WITH latest AS (
  SELECT DISTINCT ON (machine)
    machine,
    ts,
    part_id,
    level,
    code,
    message,
    cycle,
    step_id,
    step_name,
    duration,
    payload
  FROM plc_events
  ORDER BY machine, ts DESC
)
SELECT
  m.code AS machine,
  m.name AS machine_name,
  m.nominal_duration_s,
  latest.ts AS last_ts,
  latest.part_id AS last_part_id,
  latest.level AS last_level,
  latest.code AS last_code,
  latest.message AS last_message,
  latest.cycle AS last_cycle,
  latest.step_id AS last_step_id,
  latest.step_name AS last_step_name,
  latest.duration AS last_duration,
  latest.payload AS last_payload
FROM machine m
LEFT JOIN latest ON latest.machine = m.code
ORDER BY m.order_index ASC;
"""

PART_PRODUCTION_STEPS = """
SELECT
  r.plc_part_id AS part_id,
  r.machine AS machine,
  r.step_id AS step_id,
  r.step_name AS step_name,
  r.cycle AS cycle,
  r.start_time,
  r.end_time,
  r.real_duration_s
FROM v_real_machine_step_execution r
WHERE r.plc_part_id = %s
ORDER BY r.start_time ASC;
"""

PART_MACHINE_CYCLES = """
SELECT
  machine_code AS machine,
  cycle,
  real_cycle_time_s,
  nominal_duration_s,
  delta_s,
  status
FROM v_machine_nominal_vs_real
WHERE plc_part_id = %s
ORDER BY machine_code ASC;
"""

OEE_SUMMARY = """
WITH w AS (
  SELECT *
  FROM plc_events
  WHERE ts >= %s AND ts < %s
),
cycles AS (
  SELECT COUNT(*)::bigint AS total_cycles
  FROM w
  WHERE message ILIKE '%CYCLE_END%'
),
quality AS (
  SELECT
    COUNT(*) FILTER (
      WHERE (message ILIKE '%M5_OK%' OR code ILIKE '%M5_OK%' OR (payload ? 'result' AND payload->>'result' ILIKE 'OK'))
    )::bigint AS good_parts,
    COUNT(*) FILTER (
      WHERE (message ILIKE '%M5_NOK%' OR code ILIKE '%M5_NOK%' OR (payload ? 'result' AND payload->>'result' ILIKE 'NOK'))
    )::bigint AS bad_parts
  FROM w
),
downtime AS (
  SELECT COALESCE(SUM(duration), 0)::numeric AS downtime_s
  FROM w
  WHERE level = 'ERROR' AND duration IS NOT NULL
)
SELECT
  (SELECT total_cycles FROM cycles) AS total_cycles,
  (SELECT good_parts FROM quality) AS good_parts,
  (SELECT bad_parts FROM quality) AS bad_parts,
  (SELECT downtime_s FROM downtime) AS downtime_s;
"""
