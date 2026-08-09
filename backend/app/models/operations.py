"""Phase 2-4 models: operational intelligence, passenger app, booking marketplace.

All site-scoped tables carry site_id -> sites.id. All data is simulated/anonymized.
No biometric data, no PNR/payment data stored.
"""
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    flight_number: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    airline: Mapped[str] = mapped_column(String(80), nullable=False)
    origin: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    destination: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    scheduled_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    scheduled_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Scheduled")  # Scheduled/Boarding/Departed/Arrived/Delayed/Cancelled
    gate: Mapped[str | None] = mapped_column(String(16), nullable=True)
    terminal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    passenger_capacity: Mapped[int] = mapped_column(Integer, default=180)
    passengers_booked: Mapped[int] = mapped_column(Integer, default=0)


class Passenger(Base):
    __tablename__ = "passengers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    flight_id: Mapped[int | None] = mapped_column(ForeignKey("flights.id"), index=True, nullable=True)
    passenger_reference: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Checked In")


class BaggageScan(Base):
    __tablename__ = "baggage_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baggage_id: Mapped[int] = mapped_column(ForeignKey("baggage.id"), index=True, nullable=False)
    scan_event: Mapped[str] = mapped_column(String(40), nullable=False)  # Drop-off/Checked/Screening/Sorting/Loaded/Transferred/Arrived/Delivered
    location: Mapped[str] = mapped_column(String(80), nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=func.now())


class Baggage(Base):
    __tablename__ = "baggage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    flight_id: Mapped[int | None] = mapped_column(ForeignKey("flights.id"), index=True, nullable=True)
    bag_id: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    passenger_reference: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    origin: Mapped[str] = mapped_column(String(8), nullable=False)
    destination: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Processing")
    current_location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expected_location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    exception_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # Missing scan / Short transfer / Oversize ...
    transfer_time_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scans: Mapped[list["BaggageScan"]] = relationship(backref="baggage", cascade="all, delete-orphan")


class QueueSample(Base):
    __tablename__ = "queues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    queue_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # security/checkin/immigration
    location: Mapped[str] = mapped_column(String(80), nullable=False)
    current_length: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_wait_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    open_counters: Mapped[int] = mapped_column(Integer, default=1)
    processing_rate: Mapped[float] = mapped_column(Float, default=1.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=func.now())


class QueuePrediction(Base):
    __tablename__ = "queue_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    queue_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_length: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # LOW/MEDIUM/HIGH/CRITICAL
    model_run_id: Mapped[int | None] = mapped_column(ForeignKey("model_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelRun(Base):
    """Model version + evaluation metrics backing every 'accuracy: X%' claim in the UI."""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    training_samples: Mapped[int] = mapped_column(Integer, default=0)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_number: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)  # security/medical/fire/equipment/passenger issue/operational disruption/other
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Reported")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reported_by: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(16), index=True, default="Staff")  # Staff / Passenger
    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_logged: Mapped[bool] = mapped_column(Boolean, default=False)


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_number: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)  # toilet/water/electricity/lighting/escalator/elevator/HVAC/seating/signage/other
    priority: Mapped[str] = mapped_column(String(16), index=True, default="Medium")
    status: Mapped[str] = mapped_column(String(24), index=True, default="Reported")  # Reported/Assigned/In Progress/Resolved/Closed
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technician: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reported_by: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(16), index=True, default="Staff")  # Staff / Passenger
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    repeat_key: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)


class CargoShipment(Base):
    __tablename__ = "cargo_shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    awb_number: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Registered")
    origin: Mapped[str] = mapped_column(String(8), nullable=False)
    destination: Mapped[str] = mapped_column(String(8), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    volume_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Operational")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Active")
    trigger_key: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)  # deduplication key
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_number: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    passenger_reference: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Submitted")  # Submitted/Under Review/Resolved/Closed
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TravelAgencyPartner(Base):
    __tablename__ = "travel_agency_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    website: Mapped[str] = mapped_column(String(200), nullable=False)
    certified: Mapped[bool] = mapped_column(Boolean, default=False)
    security_endorsed: Mapped[bool] = mapped_column(Boolean, default=False)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BookingReferral(Base):
    """Affiliate referral logging. No PNR or payment data stored — booking happens on the airline's own checkout."""

    __tablename__ = "booking_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    passenger_reference: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("travel_agency_partners.id"), nullable=True)
    airline: Mapped[str] = mapped_column(String(80), nullable=False)
    flight_search: Mapped[dict] = mapped_column(JSON, default=dict)
    redirect_url: Mapped[str] = mapped_column(String(500), nullable=False)
    commission_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
