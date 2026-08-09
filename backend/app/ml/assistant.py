"""AI Airport Assistant — retrieval over structured data only.

Answers queries using the platform's own database/analytics. Responses are structurally
split into Fact / Prediction / Recommendation. Every value is retrieved from the DB or a
model run — nothing is invented, and no external LLM is required (template-based phrasing
keeps the context strictly to data actually retrieved for the query).
"""
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.operations import (
    Alert,
    Baggage,
    CargoShipment,
    Flight,
    Incident,
    MaintenanceRequest,
    QueuePrediction,
    QueueSample,
)
from ..models.core import Employee, Expense, PurchaseRequisition


class AssistantAnswer:
    def __init__(self) -> None:
        self.facts: list[str] = []
        self.predictions: list[str] = []
        self.recommendations: list[str] = []

    def to_dict(self) -> dict:
        return {
            "answer": self.facts[0] if self.facts else "I found no data to answer that.",
            "facts": self.facts,
            "predictions": self.predictions,
            "recommendations": self.recommendations,
            "tagging": "Fact / Prediction / Recommendation — all values retrieved from the platform database (simulated data).",
        }


def _latest_model_run(db: Session, model_name: str) -> dict | None:
    from ..models.operations import ModelRun

    run = db.scalar(
        select(ModelRun).where(ModelRun.model_name == model_name).order_by(ModelRun.trained_at.desc()).limit(1)
    )
    if not run:
        return None
    return {"version": run.version, "metrics": run.metrics, "trained_at": run.trained_at}


def answer_question(db: Session, site_id: int, question: str) -> AssistantAnswer:
    q = question.lower()
    a = AssistantAnswer()

    active_incidents = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.site_id == site_id, Incident.status.notin_(["Resolved", "Closed"])
        )
    ) or 0
    critical = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.site_id == site_id, Incident.severity == "CRITICAL",
            Incident.status.notin_(["Resolved", "Closed"]),
        )
    ) or 0
    open_maintenance = db.scalar(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.site_id == site_id,
            MaintenanceRequest.status.notin_(["Resolved", "Closed"]),
        )
    ) or 0
    active_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.site_id == site_id, Alert.status == "Active")
    ) or 0
    delayed_bags = db.scalar(
        select(func.count(Baggage.id)).where(
            Baggage.site_id == site_id, Baggage.status.in_(["Missing", "Delayed"]),
        )
    ) or 0
    cargo_processing = db.scalar(
        select(func.count(CargoShipment.id)).where(
            CargoShipment.site_id == site_id, CargoShipment.status.notin_(["Released", "Delivered"])
        )
    ) or 0
    arrivals = db.scalar(
        select(func.count(Flight.id)).where(
            Flight.site_id == site_id, Flight.status.in_(["Scheduled", "Delayed"])
        )
    ) or 0

    if "prediction" in q or "forecast" in q or "queue" in q or "wait" in q:
        run = _latest_model_run(db, "queue_prediction")
        pred = db.scalar(
            select(QueuePrediction).where(QueuePrediction.site_id == site_id)
            .order_by(QueuePrediction.created_at.desc()).limit(1)
        )
        current = db.scalar(
            select(func.avg(QueueSample.current_length)).where(QueueSample.site_id == site_id)
        )
        a.facts.append(
            f"Current average queue length: {round(current, 1) if current else 'no data'} people (Fact)."
        )
        if pred:
            a.predictions.append(
                f"Queue model {run['version'] if run else 'baseline'} predicts "
                f"{pred.predicted_length} people in the {pred.queue_type} queue in {pred.horizon_minutes} min "
                f"(Prediction, metric {run['metrics'] if run else 'n/a'})."
            )
            if pred.congestion_level in ("HIGH", "CRITICAL"):
                a.recommendations.append(
                    f"Recommendation: open an additional {pred.queue_type} lane — rule: predicted congestion is "
                    f"{pred.congestion_level}."
                )
        else:
            a.predictions.append("No saved prediction yet (Prediction data unavailable).")

    elif "what" in q and ("happen" in q or "prioriti" in q or "status" in q or "overview" in q):
        a.facts.append(
            f"Current status at this site: {active_incidents} open incidents ({critical} critical), "
            f"{open_maintenance} open maintenance requests, {active_alerts} active alerts, "
            f"{delayed_bags} delayed/missing bags, {cargo_processing} cargo shipments in processing, "
            f"{arrivals} flights scheduled/delayed."
        )
        if critical:
            a.recommendations.append(
                f"Prioritize the {critical} CRITICAL incident(s): per escalation rule, CRITICAL incidents unassigned "
                f">5 minutes auto-notify the Operations Manager. Assign staff and resolve before lower-severity work."
            )
        elif active_alerts:
            a.recommendations.append("Acknowledge active alerts and confirm response owners for each.")
        else:
            a.recommendations.append("No critical work — continue routine monitoring and close low-priority tickets.")

    elif "baggage" in q or "bag" in q:
        high_risk = db.scalars(
            select(Baggage).where(Baggage.site_id == site_id, Baggage.risk_score >= 0.5).limit(5)
        ).all()
        a.facts.append(f"{delayed_bags} bags are in delayed/missing status; {len(high_risk)} high-risk bags (>=0.5).")
        for b in high_risk[:3]:
            a.recommendations.append(
                f"Bag {b.bag_id} risk {b.risk_score} — apply expedited transfer handling."
            )

    elif "cargo" in q or "freight" in q:
        avg_clear = db.scalar(
            select(func.avg((CargoShipment.cleared_at - CargoShipment.registered_at).label("d")))
            .where(CargoShipment.site_id == site_id, CargoShipment.cleared_at.isnot(None))
        )
        a.facts.append(f"{cargo_processing} shipments in processing; delayed: "
                       f"{db.scalar(select(func.count(CargoShipment.id)).where(CargoShipment.site_id == site_id, CargoShipment.delayed))}.")
        if avg_clear is not None:
            a.facts.append(f"Average clearance time: ~{avg_clear.total_seconds() / 3600:.1f} hours.")
        a.recommendations.append("Clear shipments older than 48h first (bottleneck rule).")

    elif "budget" in q or "finance" in q or "spend" in q:
        total_spend = db.scalar(select(func.sum(Expense.amount)).where(Expense.site_id == site_id)) or 0
        pending = db.scalar(
            select(func.count(PurchaseRequisition.id)).where(
                PurchaseRequisition.site_id == site_id, PurchaseRequisition.status == "Submitted"
            )
        ) or 0
        a.facts.append(f"Total recorded spend: {round(total_spend, 2)} (Fact); {pending} requisitions awaiting approval (Fact).")
        if pending:
            a.recommendations.append("Approve or reject the pending requisitions to keep budget data current.")

    elif "headcount" in q or "staff" in q or "employee" in q:
        headcount = db.scalar(
            select(func.count(Employee.id)).where(Employee.site_id == site_id, Employee.employment_status == "Active")
        ) or 0
        a.facts.append(f"Active headcount at this site: {headcount} (Fact).")

    else:
        a.facts.append(
            "I can answer about: current status/priorities, queue predictions, baggage risk, cargo, "
            "finance/budget, and headcount — using only this platform's (simulated) data."
        )

    return a


def generate_recommendations(db: Session, site_id: int) -> list[dict]:
    """Rule/data/model-driven recommendations. Each is traceable to the rule that fired."""
    recs: list[dict] = []

    critical = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.site_id == site_id, Incident.severity == "CRITICAL",
            Incident.status.notin_(["Resolved", "Closed"]), Incident.assigned_to.is_(None),
        )
    ) or 0
    if critical:
        recs.append({
            "recommendation": "Assign owners to CRITICAL incidents immediately",
            "rule": "CRITICAL severity unassigned >5 min → auto-notify Operations Manager + log escalation",
            "triggered_by": {"critical_unassigned": critical},
            "type": "Recommendation",
        })

    queue = db.scalar(
        select(func.max(QueueSample.current_length)).where(
            QueueSample.site_id == site_id, QueueSample.recorded_at >= date.today()
        )
    )
    if queue and queue >= 40:
        recs.append({
            "recommendation": "Open an additional lane at the congested queue",
            "rule": "predicted/observed queue length >= 40 → HIGH congestion → open lane",
            "triggered_by": {"observed_queue_length": queue},
            "type": "Recommendation",
        })

    high_risk_bags = db.scalar(
        select(func.count(Baggage.id)).where(Baggage.site_id == site_id, Baggage.risk_score >= 0.5)
    ) or 0
    if high_risk_bags:
        recs.append({
            "recommendation": f"Expedite {high_risk_bags} high-risk bag(s) through transfer handling",
            "rule": "baggage risk_score >= 0.5 → expedite",
            "triggered_by": {"high_risk_bags": high_risk_bags},
            "type": "Recommendation",
        })

    overdue = db.scalar(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.site_id == site_id, MaintenanceRequest.status.notin_(["Resolved", "Closed"]),
            MaintenanceRequest.priority == "High",
        )
    ) or 0
    if overdue:
        recs.append({
            "recommendation": "Prioritize high-priority maintenance requests",
            "rule": "high priority + not resolved → overdue maintenance alert",
            "triggered_by": {"high_priority_open": overdue},
            "type": "Recommendation",
        })

    if not recs:
        recs.append({
            "recommendation": "No urgent action required",
            "rule": "no rule thresholds met",
            "triggered_by": {},
            "type": "Recommendation",
        })
    return recs
