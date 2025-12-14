import threading
import time
import datetime
import json
import queue
import os
import os.path as op
import os
import sys


LOG_TEXT_FILE = "./log/events.log"
LOG_JSONL_FILE = "./log/events.jsonl"


# ============================================================
# 1) TIMESTAMP GLOBAL FIXE — CRÉÉ UNE SEULE FOIS
# ============================================================
SIMULATION_START_TS = datetime.datetime.utcnow()


def compute_timestamp(start_at: int, cycle_id: int, cycle_nominal: int) -> str:
    """
    timestamp = SIMULATION_START_TS + start_at + (cycle_id - 1) * cycle_nominal
    """
    ts = SIMULATION_START_TS \
         + datetime.timedelta(seconds=start_at) \
         + datetime.timedelta(seconds=(cycle_id - 1) * cycle_nominal)
    return ts.isoformat() + "Z"


# ============================================================
# 2) FORMATAGE ÉVÈNEMENT POUR BDD
# ============================================================
def log_event(machine, level, code, message, cycle, step, duration, timestamp, out_queue):
    evt = {
        "ts": timestamp,
        "machine": machine,
        "level": level,
        "code": code,
        "message": message,
        "cycle": cycle,
        "step_id": step.get("id") if step else None,
        "step_name": step.get("name") if step else None,
        "duration": duration,
        "payload": {
            "cycle": cycle,
            "step": step
        }
    }

    print(
        f"{evt['ts']} [{evt['machine']}] {evt['level']} {evt['code']} "
        f"{evt['message']} cycle={evt['cycle']} step={evt['step_id']}:{evt['step_name']} "
        f"duration={evt['duration']}"
    )

    out_queue.put(evt)


# ============================================================
# 3) THREAD MACHINE
# ============================================================
class MachineThread(threading.Thread):
    def __init__(self, name, config, scenario_info, event_queue, cycle_nominal, scenario="nominal"):
        super().__init__(daemon=True)
        self.name = name
        self.config = config
        self.event_queue = event_queue
        self.scenario = scenario

        self.start_at = scenario_info["start_at"]
        self.duration = scenario_info["end_at"] - scenario_info["start_at"]  # duration = end_at
        self.cycle_nominal = cycle_nominal

        self.running = True
        self.cycle_id = 1

    def run(self):
        while self.running:
            self.run_cycle(self.cycle_id)
            self.cycle_id += 1
            time.sleep(0.5)

    def run_cycle(self, cid):
        steps = self.config.get("steps", [])
        base_sleep = 0.3

        # timestamp unique pour TOUT le cycle
        timestamp = compute_timestamp(self.start_at, cid, self.cycle_nominal)

        for idx, step in enumerate(steps):
            time.sleep(base_sleep)

            step_id = step["id"]
            step_name = step["name"]

            # SCENARIOS

            if self.scenario == "nominal":
                log_event(
                    self.name, "EVENT", step_id, f"{step_name} OK (cycle={cid})",
                    cid, step, self.duration, timestamp, self.event_queue
                )

            elif self.scenario == "anomalies" and idx == max(1, len(steps) // 2):
                err_code = f"E-{self.name}-SIM"
                log_event(
                    self.name, "ERROR", err_code, f"Erreur simulée sur {step_name} (cycle={cid})",
                    cid, step, self.duration, timestamp, self.event_queue
                )

            elif self.scenario == "dephasage":
                time.sleep(base_sleep * (idx + 1) * 0.2)
                log_event(
                    self.name, "EVENT", step_id, f"{step_name} avec déphasage (cycle={cid})",
                    cid, step, self.duration, timestamp, self.event_queue
                )

            elif self.scenario == "trs_stop":
                if cid >= 3:
                    log_event(
                        self.name, "STATUS", "DOWN", "Machine arrêtée (TRS en baisse)",
                        cid, step, self.duration, timestamp, self.event_queue
                    )
                    return
                else:
                    log_event(
                        self.name, "EVENT", step_id, f"{step_name} OK (cycle={cid})",
                        cid, step, self.duration, timestamp, self.event_queue
                    )

            else:
                log_event(
                    self.name, "EVENT", step_id, f"{step_name} OK (cycle={cid})",
                    cid, step, self.duration, timestamp, self.event_queue
                )


# ============================================================
# 4) THREAD D’ÉCRITURE LOGS
# ============================================================
class LogWriterThread(threading.Thread):
    def __init__(self, event_queue):
        super().__init__(daemon=True)
        self.event_queue = event_queue

    def run(self):
        with open(LOG_TEXT_FILE, "a", encoding="utf-8") as ft, \
             open(LOG_JSONL_FILE, "a", encoding="utf-8") as fj:

            while True:
                evt = self.event_queue.get()
                if evt is None:
                    break

                line = (
                    f"{evt['ts']} [{evt['machine']}] {evt['level']} {evt['code']} "
                    f"{evt['message']} cycle={evt['cycle']} "
                    f"step={evt['step_id']}:{evt['step_name']} duration={evt['duration']}"
                )
                ft.write(line + "\n")
                ft.flush()

                fj.write(json.dumps(evt, ensure_ascii=False) + "\n")
                fj.flush()


# ============================================================
# 5) MAIN
# ============================================================
def main():
    # Reset logs
    for f in (LOG_TEXT_FILE, LOG_JSONL_FILE):
        if os.path.exists(f):
            os.remove(f)

    # Load workflow JSON
    with open("../workflow/workflow.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cycle_nominal = cfg["ligne_industrielle"]["cycle_nominal_s"]
    machines_cfg = cfg["machines"]

    # Extract start_at / end_at
    scenario_info = {
        seq["machine"]: {
            "start_at": seq["start_at"],
            "end_at": seq["end_at"]
        }
        for seq in cfg["scenario_nominal"]["sequence"]
    }

    event_queue = queue.Queue()
    LogWriterThread(event_queue).start()

    threads = [
        MachineThread("M1", machines_cfg["M1"], scenario_info["M1"], event_queue, cycle_nominal, "nominal"),
        MachineThread("M2", machines_cfg["M2"], scenario_info["M2"], event_queue, cycle_nominal, "anomalies"),
        MachineThread("M3", machines_cfg["M3"], scenario_info["M3"], event_queue, cycle_nominal, "dephasage"),
        MachineThread("M4", machines_cfg["M4"], scenario_info["M4"], event_queue, cycle_nominal, "trs_stop"),
        MachineThread("M5", machines_cfg["M5"], scenario_info["M5"], event_queue, cycle_nominal, "nominal"),
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt demandé")
    finally:
        for t in threads:
            t.running = False
        event_queue.put(None)


if __name__ == "__main__":
    main()
