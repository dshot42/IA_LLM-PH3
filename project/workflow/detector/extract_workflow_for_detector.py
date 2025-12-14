import re
import json
import pandas as pd


def build_workflow_features(workflow_json):
    """Construit toutes les features numériques possibles à partir du workflow JSON."""

    # ==============================
    # 1. Cycle nominal
    # ==============================
    cycle_nominal = workflow_json["ligne_industrielle"]["cycle_nominal_s"]

    # ==============================
    # 2. Durées nominales par machine
    # ==============================
    machine_nominal_times = workflow_json["workflow_global"]["durees_nominales_s"].copy()

    # ==============================
    # 3. Ordre nominal des machines
    # ==============================
    machine_order = {
        m: i for i, m in enumerate(workflow_json["workflow_global"]["ordre_machines"])
    }

    # ==============================
    # 4. Construction d’un dictionnaire step → machine
    # ==============================
    step_to_machine = {}
    step_order = {}
    expected_step_duration = {}

    for mname, mdata in workflow_json["machines"].items():
        steps = mdata["steps"]
        n_steps = len(steps)
        nom_mach_time = machine_nominal_times.get(mname, 0)
        nominal_step_duration = nom_mach_time / max(n_steps, 1)

        for idx, s in enumerate(steps):
            step_id = s["id"]
            step_to_machine[step_id] = mname
            step_order[step_id] = idx
            expected_step_duration[step_id] = nominal_step_duration

    # ==============================
    # 5. Criticalité des steps
    # ==============================
    criticality = {}
    for mname, mdata in workflow_json["machines"].items():
        # plus il y a d’erreurs, plus la machine est sensible
        crit = len(mdata.get("error_codes", []))
        for s in mdata["steps"]:
            criticality[s["id"]] = crit

    # ==============================
    # 6. Résultat final
    # ==============================
    return {
        "cycle_nominal": cycle_nominal,
        "machine_order": machine_order,
        "machine_nominal_times": machine_nominal_times,
        "step_to_machine": step_to_machine,
        "step_order": step_order,
        "expected_step_duration": expected_step_duration,
        "criticality": criticality,
    }


def add_features_to_events(df_events, wf):
    """
    Ajoute les features au DataFrame d’événements issus du PLC.
    df_events : DataFrame contenant au minimum:
        ts, machine, step_id, duration, cycle
    """

    df = df_events.copy()

    # ============ Features globales ============
    df["cycle_nominal_s"] = wf["cycle_nominal"]

    # ============ Features machine ============
    df["expected_machine_duration"] = df["machine"].map(wf["machine_nominal_times"])
    df["machine_order_id"] = df["machine"].map(wf["machine_order"])

    # ============ Features step ============
    df["step_order"] = df["step_id"].map(wf["step_order"])
    df["expected_step_duration"] = df["step_id"].map(wf["expected_step_duration"])

    # delta durée
    df["duration_delta"] = df["duration"] - df["expected_step_duration"]

    # ============ Criticité ============
    df["criticality_score"] = df["step_id"].map(wf["criticality"])

    # Séquence valide ?
    df["expected_machine"] = df["step_id"].map(wf["step_to_machine"])
    df["is_out_of_sequence"] = df["expected_machine"] != df["machine"]

    # Pourcentage d’avancement du cycle
    df["cycle_progress"] = df["duration"] / df["cycle_nominal_s"]

    return df
