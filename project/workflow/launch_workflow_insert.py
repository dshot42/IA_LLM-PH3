import json
import psycopg2
from psycopg2.extras import execute_batch

# ==============================
# CONFIG
# ==============================
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "plc",
    "user": "postgres",
    "password": "postgres"
}

WORKFLOW_JSON_FILE = "workflow.json"
DRY_RUN = False   # True = print SQL only


# ==============================
# DB UTILS
# ==============================
def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def exec_sql(cur, sql, params=None):
    if DRY_RUN:
        print(cur.mogrify(sql, params).decode())
    else:
        cur.execute(sql, params)


# ==============================
# MAIN IMPORT
# ==============================
def main():
    with open(WORKFLOW_JSON_FILE, "r", encoding="utf-8") as f:
        wf = json.load(f)

    conn = get_conn()
    cur = conn.cursor()

    # --------------------------------------------------
    # 1. Industrial line
    # --------------------------------------------------
    line_name = wf["ligne_industrielle"]["nom"]
    cycle_nominal = wf["ligne_industrielle"]["cycle_nominal_s"]

    exec_sql(cur, """
        INSERT INTO industrial_line (name, cycle_nominal_s)
        VALUES (%s, %s)
        ON CONFLICT (name) DO NOTHING
    """, (line_name, cycle_nominal))

    # --------------------------------------------------
    # 2. Machines
    # --------------------------------------------------
    durations = wf["workflow_global"]["durees_nominales_s"]

    for idx, code in enumerate(wf["workflow_global"]["ordre_machines"], start=1):
        m = wf["machines"][code]

        exec_sql(cur, """
            INSERT INTO machine (
                code, name, description, ip_address,
                plc_protocol, opcua_endpoint,
                line_id, order_index, nominal_duration_s
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s,
                (SELECT id FROM industrial_line WHERE name=%s),
                %s, %s
            )
            ON CONFLICT (code) DO NOTHING
        """, (
            code,
            m["nom"],
            m["description"],
            m["ip"],
            m["communication"]["PLC"],
            m["communication"]["OPC_UA"],
            line_name,
            idx,
            durations[code]
        ))

    # --------------------------------------------------
    # 3. GRAFCET steps
    # --------------------------------------------------
    for step in wf["grafcet"]["steps"]:
        machine_code = step.get("machine")

        exec_sql(cur, """
            INSERT INTO production_step (
                step_code, name, description, machine_id, is_technical
            )
            VALUES (
                %s, %s, %s,
                (SELECT id FROM machine WHERE code=%s),
                %s
            )
            ON CONFLICT DO NOTHING
        """, (
            step["id"],
            step["id"],
            step["description"],
            machine_code,
            machine_code is None
        ))

    # --------------------------------------------------
    # 4. GRAFCET transitions
    # --------------------------------------------------
    for t in wf["grafcet"]["transitions"]:
        if t["from"] == "*":
            continue

        exec_sql(cur, """
            INSERT INTO step_transition (from_step_id, to_step_id, condition, is_error)
            VALUES (
                (SELECT id FROM production_step WHERE step_code=%s),
                (SELECT id FROM production_step WHERE step_code=%s),
                %s,
                %s
            )
        """, (
            t["from"],
            t["to"],
            t["condition"],
            "ERR" in t["to"]
        ))

    # --------------------------------------------------
    # 5. Machine micro-steps
    # --------------------------------------------------
    for machine_code, machine in wf["machines"].items():
        for order, step in enumerate(machine["steps"], start=1):
            exec_sql(cur, """
                INSERT INTO machine_step_definition (
                    machine_id, step_code, name, description, step_order
                )
                VALUES (
                    (SELECT id FROM machine WHERE code=%s),
                    %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
            """, (
                machine_code,
                step["id"],
                step["name"],
                step["description"],
                order
            ))

    if not DRY_RUN:
        conn.commit()

    cur.close()
    conn.close()
    print("✅ Workflow import terminé")


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    main()
