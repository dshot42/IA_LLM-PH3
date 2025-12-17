from flask import Blueprint, jsonify, request, Response,send_file,abort
from datetime import datetime, timedelta, timezone
import time, json

from .connect import get_conn
from . import queries
from .security import jwt_required, create_token
from .config import API_USER, API_PASSWORD
import os

import os.path as op
import os
import sys
import ia.generate_repport


api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})

@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username != API_USER or password != API_PASSWORD:
        return jsonify({"error": "invalid_credentials"}), 401

    token = create_token(username)
    return jsonify({"access_token": token, "token_type": "Bearer"})

@api_bp.get("/parts")
@jwt_required
def list_parts():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 500)
    offset = (page - 1) * page_size

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.PARTS_COUNT)
        total = int(cur.fetchone()["total"])
        cur.execute(queries.PARTS_PAGE, (page_size, offset))
        items = cur.fetchall()

    return jsonify({"page": page, "page_size": page_size, "total": total, "items": items})

@api_bp.get("/parts/<part_id>")
@jwt_required
def part_detail(part_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.PART_PRODUCTION_STEPS, (part_id,))
        steps = cur.fetchall()
        cur.execute(queries.PART_MACHINE_CYCLES, (part_id,))
        machines = cur.fetchall()

    return jsonify({"part_id": part_id, "machines": machines, "steps": steps})

@api_bp.get("/machines/live")
@jwt_required
def machines_live():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.MACHINES_LIVE)
        rows = cur.fetchall()
    return jsonify(rows)

@api_bp.get("/oee")
@jwt_required
def oee():
    now = datetime.now(timezone.utc)
    default_from = now - timedelta(hours=1)

    from_s = request.args.get("from")
    to_s = request.args.get("to")
    nominal_cycle_s = float(request.args.get("line_nominal_s", "90"))

    def parse_ts(v: str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))

    t_from = parse_ts(from_s) if from_s else default_from
    t_to = parse_ts(to_s) if to_s else now
    elapsed_s = max((t_to - t_from).total_seconds(), 1.0)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.OEE_SUMMARY, (t_from, t_to))
        s = cur.fetchone()

    total_cycles = int(s["total_cycles"] or 0)
    good_parts = int(s["good_parts"] or 0)
    bad_parts = int(s["bad_parts"] or 0)
    downtime_s = float(s["downtime_s"] or 0.0)

    availability = max(min((elapsed_s - downtime_s) / elapsed_s, 1.0), 0.0)
    runtime_s = max(elapsed_s - downtime_s, 1.0)
    performance = max(min((nominal_cycle_s * total_cycles) / runtime_s, 1.5), 0.0)
    denom = good_parts + bad_parts
    quality = (good_parts / denom) if denom > 0 else None
    oee_val = (availability * performance * quality) if quality is not None else None

    return jsonify({
        "from": t_from.isoformat(),
        "to": t_to.isoformat(),
        "elapsed_s": elapsed_s,
        "nominal_cycle_s": nominal_cycle_s,
        "total_cycles": total_cycles,
        "good_parts": good_parts,
        "bad_parts": bad_parts,
        "downtime_s": downtime_s,
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "oee": oee_val
    })
    
@api_bp.get("/trs")
@jwt_required
def trs():
    # todo
    return jsonify({ })

@api_bp.get("/plc/stream")
@jwt_required
def plc_stream():
    since = request.args.get("since")
    start = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None

    def gen():
        last_ts = start
        sse_id = 0
        while True:
            with get_conn() as conn, conn.cursor() as cur:
                if last_ts is None:
                    cur.execute("SELECT ts FROM plc_events ORDER BY ts DESC LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        last_ts = row["ts"]

                cur.execute(
                    "SELECT ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload "
                    "FROM plc_events WHERE ts > %s ORDER BY ts ASC LIMIT 200",
                    (last_ts,)
                )
                rows = cur.fetchall()

            if rows:
                for r in rows:
                    last_ts = r["ts"]
                    sse_id += 1
                    payload = {
                        "ts": r["ts"].isoformat(),
                        "part_id": r["part_id"],
                        "machine": r["machine"],
                        "level": r["level"],
                        "code": r["code"],
                        "message": r["message"],
                        "cycle": r["cycle"],
                        "step_id": r["step_id"],
                        "step_name": r["step_name"],
                        "duration": float(r["duration"]) if r["duration"] is not None else None,
                        "payload": r["payload"],
                    }
                    yield f"id: {sse_id}\n"
                    yield "event: plc_event\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield "event: ping\n"
                yield "data: {}\n\n"

            time.sleep(0.5)

    return Response(gen(), mimetype="text/event-stream")

@api_bp.route("/download/<path:name>")
def download_report(name):

    return generate_repport.download_report(name)


@api_bp.get("/anomalies")
@jwt_required
def get_anomalies():
    """
    Source de vérité FRONT
    Retourne les anomalies persistées (ordre décroissant de gravité)
    """
    limit = min(int(request.args.get("limit", 25)), 1000)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.LIST_ANOMALIES, (limit,))

        rows = cur.fetchall()

    return jsonify(rows)


@api_bp.get("/anomalies/steps/<step_id>")
@jwt_required
def get_anomalies_by_step(step_id: str):
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 25)), 1), 500)
    offset = (page - 1) * page_size

    with get_conn() as conn, conn.cursor() as cur:
        # TOTAL
        cur.execute("""
            SELECT COUNT(*) AS total
            FROM plc_anomalies
            WHERE step_id = %s
        """, (step_id,))
        total = int(cur.fetchone()["total"])

        # ITEMS
        cur.execute("""
            SELECT *
            FROM plc_anomalies
            WHERE step_id = %s
            ORDER BY ts_detected DESC, anomaly_score DESC
            LIMIT %s OFFSET %s
        """, (step_id, page_size, offset))

        items = cur.fetchall()

    return jsonify({
        "step_id": step_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items
    })


@api_bp.get("/steps")
@jwt_required
def list_steps():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 500)
    offset = (page - 1) * page_size

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(queries.PRODUCTION_STEPS_COUNT)
        total = int(cur.fetchone()["total"])

        cur.execute(
            queries.PRODUCTION_STEPS_PAGE,
            (page_size, offset)
        )
        items = cur.fetchall()

    return jsonify({
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items
    })
