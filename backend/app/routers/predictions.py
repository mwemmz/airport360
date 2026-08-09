from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..ml import QueueForecast
from ..ml.queue_model import build_training_rows, predict_queue, train_model
from ..models.operations import Flight, ModelRun, QueuePrediction, QueueSample
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/predictions", tags=["predictions"])

PRED_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


def _flights_in_window(db: DbSession, site_id: int) -> int:
    now = datetime.now()
    return db.scalar(
        select(func.count(Flight.id)).where(
            Flight.site_id == site_id,
            Flight.scheduled_departure.between(now - timedelta(hours=1), now + timedelta(hours=3)),
        )
    ) or 0


def _train_and_store(db: DbSession, site_id: int) -> tuple[ModelRun, object]:
    samples = db.scalars(
        select(QueueSample).where(QueueSample.site_id == site_id).order_by(QueueSample.recorded_at)
    ).all()
    if len(samples) < 20:
        raise HTTPException(status_code=409, detail="Not enough queue history to train (need >= 20 samples)")

    flights_window = _flights_in_window(db, site_id)
    rows = build_training_rows(samples, {site_id: flights_window})
    model, metrics = train_model(rows)

    run = ModelRun(
        model_name="queue_prediction",
        version=f"v{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        metrics=metrics,
        training_samples=len(rows),
    )
    db.add(run)
    db.flush()
    db.commit()
    db.refresh(run)
    return run, model


@router.get("/queue")
def predict_queue_endpoint(
    queue_type: str = "security",
    horizon_minutes: int = 30,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*PRED_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")

    run, model = _train_and_store(db, site_id)

    latest = db.scalar(
        select(QueueSample).where(QueueSample.site_id == site_id).order_by(QueueSample.recorded_at.desc()).limit(1)
    )
    current_length = latest.current_length if latest else 15
    open_counters = latest.open_counters if latest else 1
    processing_rate = latest.processing_rate if latest else 1.0

    forecast: QueueForecast = predict_queue(
        model,
        run.metrics,
        {
            "hour": datetime.now().hour,
            "flights_in_window": _flights_in_window(db, site_id),
            "volume": float(current_length + (latest.avg_wait_minutes if latest else 10)),
            "open_counters": open_counters,
            "processing_rate": processing_rate,
            "current_length": float(current_length),
            "horizon_minutes": horizon_minutes,
            "surge": queue_type == "security",
        },
    )

    pred = QueuePrediction(
        site_id=site_id,
        queue_type=queue_type,
        horizon_minutes=horizon_minutes,
        predicted_length=forecast.predicted_length,
        congestion_level=forecast.congestion_level,
        model_run_id=run.id,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)

    return {
        "id": pred.id,
        "predicted_length": forecast.predicted_length,
        "congestion_level": forecast.congestion_level,
        "horizon_minutes": horizon_minutes,
        "model_name": run.model_name,
        "model_version": run.version,
        "metrics": run.metrics,
        "features": forecast.features,
        "tag": "Prediction — prototype model trained on simulated data",
        "created_at": pred.created_at.isoformat(),
    }
