"""Interfaces for every ML/CV component so a stronger model can be swapped in later
without touching calling code."""

from dataclasses import dataclass, field


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0


@dataclass
class BoundingBoxes:
    boxes: list[BoundingBox] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.boxes)


@dataclass
class QueueForecast:
    horizon_minutes: int
    predicted_length: float
    congestion_level: str  # LOW / MEDIUM / HIGH / CRITICAL
    model_name: str
    metrics: dict  # evaluation metrics backing the displayed "accuracy" claim
    features: dict  # input features used


@dataclass
class BaggageRiskResult:
    risk_score: float  # 0..1
    reasons: list[str]
    model_label: str = "Prototype risk model — not validated against real mishandling data"
