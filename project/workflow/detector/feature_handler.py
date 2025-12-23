import json
import pandas as pd
from supervision_handler.app.factory import socketio, db

# ============================================================
# FETCH EVENTS (BRUTS)
# ============================================================

def fetch_events_df(param) -> pd.DataFrame:
    sql = """
    SELECT
        ts,
        machine,
        level,
        code,
        message,
        cycle,
        step_id,
        step_name,
        duration,
        part_id
    FROM plc_events
    WHERE cycle IS NOT NULL
      AND machine != 'SYSTEM'
    ORDER BY cycle ASC, ts ASC
    """
    # limit a definir selon param cycle ( jours, semaines, mois ...)
    df = pd.read_sql(sql, db.engine)

    if df.empty:
        return df

    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["cycle"] = df["cycle"].astype(int)

    return df.reset_index(drop=True)


# ============================================================
# WORKFLOW HELPERS
# ============================================================

def get_last_step_of_last_machine(workflow_json: str) -> str:
    wf = json.loads(workflow_json)
    last_machine = wf["workflow_global"]["ordre_machines"][-1]
    steps = wf["machines"][last_machine]["steps"]
    return steps[-1]["id"]



def parse_workflow(workflow_json: str) -> dict:
    wf = json.loads(workflow_json)

    cycle_nominal = wf["ligne_industrielle"]["cycle_nominal_s"]
    machine_order = wf["workflow_global"]["ordre_machines"]
    nominal_durations = wf["workflow_global"]["durees_nominales_s"]

    steps_per_machine = {
        m: len(data.get("steps", []))
        for m, data in wf["machines"].items()
    }

    return {
        "cycle_nominal_s": cycle_nominal,
        "machine_order": machine_order,
        "nominal_durations": nominal_durations,
        "steps_per_machine": steps_per_machine,
    }
