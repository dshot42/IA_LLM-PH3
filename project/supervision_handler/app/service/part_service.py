from datetime import datetime, timezone, timedelta
import json
import os
# imports internes supervision_handler
from supervision_handler.app.models import Part, PlcEvent
from supervision_handler.app.factory import socketio, db
from workflow.detector.launch_detection import check_anomalies

# import config global (racine projet)
from config import Config


def load_workflow() -> dict:
    workflow_file = os.path.join(
        Config.folder_workflow,
        "workflow.json"
    )

    with open(workflow_file, "r", encoding="utf-8") as f:
        return json.load(f)  
    
def get_last_step_of_last_machine(workflow) -> str:
    last_machine = workflow["workflow_global"]["ordre_machines"][-1]
    last_step = workflow["machines"][last_machine]["steps"][-1]["id"]
    return last_step
        
def get_last_machine(workflow: dict) -> str:
    return workflow["workflow_global"]["ordre_machines"][-1]


def get_last_step_of_machine(workflow: dict, machine: str) -> str:
    return workflow["machines"][machine]["steps"][-1]["id"]


def get_final_success_codes(workflow: dict, machine: str) -> set[str]:
    return {
        c["code"]
        for c in workflow["machines"][machine]["success_codes"]
    }
    
def partIsFinish(workflow, event):
    last_machine = get_last_machine(workflow)
    last_step = get_last_step_of_machine(workflow, last_machine)
    success_codes = get_final_success_codes(workflow, last_machine)

    # 🔍 Condition STRICTE : dernier step + dernier machine + succès
    if (
        event.machine != last_machine
        or event.step_id != last_step
       # or event.code not in success_codes
    ):
        return False

    part = Part.query.filter_by(
        external_part_id=event.part_id
    ).one_or_none()

    if not part or part.status in ("FINISHED", "SCRAPPED"):
        return False

    part.status = "FINISHED"
    part.finished_at = event.ts or datetime.now(timezone.utc)

    db.session.commit()
    check_anomalie_on_detector(event.part_id)
    return True


def update_part_from_event(event: PlcEvent) -> bool:
    if not event.part_id:
        return False

    workflow = load_workflow()

    if try_reject_part_from_step_error(event):
        return True

    if scrap_handler(event):
        return True

    return partIsFinish(workflow, event)

   
def scrap_handler(event:PlcEvent) -> bool:
    
    CRITICAL_SCRAP_CODES = {
    "E-M2-013",  # TOOL_BREAK
    "E-M3-021",  # ROUGHNESS_NOK
    "E-M4-031",  # TOOL_BREAKAGE
    }

    if not event.part_id:
        return False

    part = Part.query.filter_by(
        external_part_id = event.part_id
    ).one_or_none()

    if not part or part.status in ("FINISHED", "SCRAPPED"):
        return False  

    # 🔴 SCRAP IMMÉDIAT
    if event.code in CRITICAL_SCRAP_CODES:
        part.status = "SCRAPPED"
        part.finished_at = event.ts or datetime.now(timezone.utc)
        db.session.commit()
        check_anomalie_on_detector(event.part_id)
        return True
    return False


def is_rejecting_error(event:PlcEvent) -> bool:
    if event.code and (event.code.startswith("E-") or event.code.startswith("ERROR")) :
        return True
    if event.level == "ERROR":
        return True
    return False


def try_reject_part_from_step_error(event) -> bool:
    """
    Rejette immédiatement une pièce
    si une erreur step est détectée.
    """

    if not event.part_id:
        return False

    if not is_rejecting_error(event):
        return False

    part = Part.query.filter_by(
        external_part_id=event.part_id
    ).one_or_none()

    if not part:
        return False

    # 🔒 idempotence
    if part.status in ("REJECTED", "SCRAPPED", "FINISHED"):
        return False

    part.status = "REJECTED"
    part.finished_at = event.ts or datetime.now(timezone.utc)

    db.session.commit()
    check_anomalie_on_detector(event.part_id)
    return True

def check_anomalie_on_detector(part_id):
    param = {
        "only_last": False,
        "start":  datetime.now(timezone.utc) - timedelta(days=2),
        "end": datetime.now(timezone.utc),
        "part_id": part_id,
        "ligne": "",
        "LLM_RESULT" : True
    }

    check_anomalies(param)     