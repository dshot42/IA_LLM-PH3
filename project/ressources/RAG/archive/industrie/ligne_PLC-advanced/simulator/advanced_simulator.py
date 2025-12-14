
import threading
import time
import datetime
import json
import queue
# from opcua import Server  # à installer côté client : pip install opcua

LOG_TEXT_FILE = "events.log"
LOG_JSONL_FILE = "events.jsonl"

def ts():
    return datetime.datetime.utcnow().isoformat() + "Z"

def log_event(machine, level, code, message, extra=None, out_queue=None):
    evt = {
        "timestamp": ts(),
        "machine": machine,
        "level": level,
        "code": code,
        "message": message,
        "extra": extra or {}
    }
    line = f"{evt['timestamp']} [{machine}] {level} {code} {message} {extra or ''}"
    print(line)
    if out_queue is not None:
        out_queue.put(evt)

class MachineThread(threading.Thread):
    def __init__(self, name, config, event_queue, scenario="nominal"):
        super().__init__(daemon=True)
        self.name = name
        self.config = config
        self.event_queue = event_queue
        self.scenario = scenario
        self.running = True
        self.cycle_id = 1

    def run(self):
        while self.running:
            self.run_cycle(self.cycle_id)
            self.cycle_id += 1
            time.sleep(0.5)

    def run_cycle(self, cid):
        steps = self.config.get("steps", [])
        # Temps simplifiés par step (on pourrait les lier au JSON si besoin)
        base_step_sleep = 0.3
        # Scénarios
        for idx, step in enumerate(steps):
            time.sleep(base_step_sleep)
            step_id = step["id"]
            name = step["name"]
            # Nominal
            if self.scenario == "nominal":
                log_event(self.name, "EVENT", step_id,
                          f"{name} OK (cycle={cid})",
                          {"step": step, "cycle": cid},
                          self.event_queue)
            # Anomalies simples : sur certaines machines et steps
            elif self.scenario == "anomalies" and idx == max(1, len(steps)//2):
                err_code = f"E-{self.name}-SIM"
                log_event(self.name, "ERROR", err_code,
                          f"Erreur simulée sur {name} (cycle={cid})",
                          {"step": step, "cycle": cid},
                          self.event_queue)
            # Déphasage : temporisation plus longue
            elif self.scenario == "dephasage":
                time.sleep(base_step_sleep * (idx+1) * 0.2)
                log_event(self.name, "EVENT", step_id,
                          f"{name} avec déphasage (cycle={cid})",
                          {"step": step, "cycle": cid},
                          self.event_queue)
            # TRS / arrêt : machine se met DOWN après quelques cycles
            elif self.scenario == "trs_stop":
                if cid >= 3:
                    log_event(self.name, "STATUS", "DOWN",
                              "Machine arrêtée (TRS en baisse)",
                              {"cycle": cid},
                              self.event_queue)
                    time.sleep(2.0)
                    return
                else:
                    log_event(self.name, "EVENT", step_id,
                              f"{name} OK (cycle={cid})",
                              {"step": step, "cycle": cid},
                              self.event_queue)
            else:
                log_event(self.name, "EVENT", step_id,
                          f"{name} OK (cycle={cid})",
                          {"step": step, "cycle": cid},
                          self.event_queue)

class LogWriterThread(threading.Thread):
    def __init__(self, event_queue):
        super().__init__(daemon=True)
        self.event_queue = event_queue
        self.running = True

    def run(self):
        with open(LOG_TEXT_FILE, "a", encoding="utf-8") as ft,                  open(LOG_JSONL_FILE, "a", encoding="utf-8") as fj:
            while self.running:
                evt = self.event_queue.get()
                if evt is None:
                    break
                # texte
                line = f"{evt['timestamp']} [{evt['machine']}] {evt['level']} {evt['code']} {evt['message']} {evt['extra']}"
                ft.write(line + "\n")
                ft.flush()
                # jsonl
                fj.write(json.dumps(evt, ensure_ascii=False) + "\n")
                fj.flush()

# OPC-UA server skeleton (non démarré automatiquement, à adapter selon besoin)
def setup_opcua_server():
    """Exemple de squelette serveur OPC UA (désactivé par défaut).

    from opcua import Server
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    uri = "http://example.org/industrial_line"
    idx = server.register_namespace(uri)
    objects = server.get_objects_node()
    line_obj = objects.add_object(idx, "Ligne5Machines")
    trs_var = line_obj.add_variable(idx, "TRS", 100.0)
    trs_var.set_writable()
    # server.start()
    # return server, trs_var
    return None, None
    """
    return None, None

def main():
    with open("workflow.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    machines_cfg = cfg.get("machines", {})

    event_queue = queue.Queue()
    log_thread = LogWriterThread(event_queue)
    log_thread.start()

    # Scénarios possibles : nominal, anomalies, dephasage, trs_stop
    m1 = MachineThread("M1", machines_cfg["M1"], event_queue, scenario="nominal")
    m2 = MachineThread("M2", machines_cfg["M2"], event_queue, scenario="anomalies")
    m3 = MachineThread("M3", machines_cfg["M3"], event_queue, scenario="dephasage")
    m4 = MachineThread("M4", machines_cfg["M4"], event_queue, scenario="trs_stop")
    m5 = MachineThread("M5", machines_cfg["M5"], event_queue, scenario="nominal")

    threads = [m1, m2, m3, m4, m5]
    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt demandé par l’utilisateur.")
    finally:
        for t in threads:
            t.running = False
        event_queue.put(None)  # pour stopper le writer
        time.sleep(0.5)

if __name__ == "__main__":
    main()
