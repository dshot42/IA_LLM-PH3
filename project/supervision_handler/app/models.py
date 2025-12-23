from datetime import datetime
from .factory import db

from sqlalchemy.dialects.postgresql import JSONB, INET

class PlcEvent(db.Model):
    __tablename__ = "plc_events"
    ts = db.Column(db.DateTime(timezone=True), primary_key=True)
    part_id = db.Column(db.Text)
    machine = db.Column(db.Text, nullable=False)
    level = db.Column(db.Text, nullable=False)
    code = db.Column(db.Text)
    message = db.Column(db.Text)
    cycle = db.Column(db.Integer)
    step_id = db.Column(db.Text)
    step_name = db.Column(db.Text)
    duration = db.Column(db.Numeric)
    payload = db.Column(JSONB)

class IndustrialLine(db.Model):
    __tablename__ = "industrial_line"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    cycle_nominal_s = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Machine(db.Model):
    __tablename__ = "machine"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(INET)
    plc_protocol = db.Column(db.Text)
    opcua_endpoint = db.Column(db.Text)
    line_id = db.Column(db.Integer, db.ForeignKey("industrial_line.id"), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)
    nominal_duration_s = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductionStep(db.Model):
    __tablename__ = "production_step"
    id = db.Column(db.Integer, primary_key=True)
    step_code = db.Column(db.String(10), nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"))
    is_technical = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StepTransition(db.Model):
    __tablename__ = "step_transition"
    id = db.Column(db.Integer, primary_key=True)
    from_step_id = db.Column(db.Integer, db.ForeignKey("production_step.id"))
    to_step_id = db.Column(db.Integer, db.ForeignKey("production_step.id"))
    condition = db.Column(db.Text, nullable=False)
    is_error = db.Column(db.Boolean, default=False)

class Part(db.Model):
    __tablename__ = "part"
    id = db.Column(db.Integer, primary_key=True)
    external_part_id = db.Column(db.Text, unique=True, nullable=False)
    line_id = db.Column(db.Integer, db.ForeignKey("industrial_line.id"), nullable=False)
    status = db.Column(db.Text, default="IN_PROGRESS")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)

class PartStepExecution(db.Model):
    __tablename__ = "part_step_execution"
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey("part.id"), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey("production_step.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_s = db.Column(db.Integer)
    status = db.Column(db.Text, nullable=False)
    success_code = db.Column(db.Text)
    error_code = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MachineStepDefinition(db.Model):
    __tablename__ = "machine_step_definition"
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machine.id"), nullable=False)
    step_code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    step_order = db.Column(db.Integer, nullable=False)

class MachineStepExecution(db.Model):
    __tablename__ = "machine_step_execution"
    id = db.Column(db.Integer, primary_key=True)
    part_step_execution_id = db.Column(db.Integer, db.ForeignKey("part_step_execution.id"), nullable=False)
    machine_step_id = db.Column(db.Integer, db.ForeignKey("machine_step_definition.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_ms = db.Column(db.Integer)
    status = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlcAnomaly(db.Model):
    __tablename__ = "plc_anomalies"

    # ============================
    # PK
    # ============================
    id = db.Column(db.Integer, primary_key=True)

    # ============================
    # Identité industrielle
    # ============================
    ts_detected = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    event_ts = db.Column(
        db.DateTime(timezone=True)
    )
    part_id = db.Column(db.Text, nullable=False)
    cycle = db.Column(db.Integer, nullable=False)
    machine = db.Column(db.Text, nullable=False)

    step_id = db.Column(db.Text, nullable=True)
    step_name = db.Column(db.Text, nullable=True)

    # ============================
    # Détection
    # ============================
    anomaly_score = db.Column(db.Float, nullable=True)

    rule_anomaly = db.Column(db.Boolean, nullable=False, default=False)
    rule_reasons = db.Column(JSONB, nullable=True)

    # ============================
    # STEP (terrain)
    # ============================
    has_step_error = db.Column(db.Boolean, default=False)
    n_step_errors = db.Column(db.Integer, default=0)

    # ============================
    # Cycle
    # ============================
    cycle_duration_s = db.Column(db.Float, nullable=True)
    duration_overrun_s = db.Column(db.Float, nullable=True)

    # ============================
    # Prédictif
    # ============================
    events_count = db.Column(db.Integer, nullable=True)
    window_days = db.Column(db.Integer, nullable=True)

    ewma_ratio = db.Column(db.Float, nullable=True)
    rate_ratio = db.Column(db.Float, nullable=True)
    burstiness = db.Column(db.Float, nullable=True)

    hawkes_score = db.Column(db.Integer, nullable=True)
    confidence = db.Column(db.Text, nullable=True)

    # ============================
    # Métier
    # ============================
    status = db.Column(
        db.Text,
        nullable=False,
        default="OPEN"   # OPEN / ACK / CLOSED
    )

    severity = db.Column(
        db.Text,
        nullable=True    # INFO / WATCH / CRITICAL
    )

    # ============================
    # Métadonnées
    # ============================
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    report_path= db.Column(
        db.Text,
        nullable=True    # INFO / WATCH / CRITICAL
    )


from sqlalchemy.inspection import inspect

def model_to_dict(obj, exclude=None):
    if exclude is None:
        exclude = set()

    return {
        c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs
        if c.key not in exclude
    }