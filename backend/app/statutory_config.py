"""Statutory configuration service.

Single source of truth for Zambia statutory rates and labour-standards thresholds.
Rates live in the `statutory_config` table, versioned by effective date, so payroll
and leave read from configuration — never inline constants. Every row is labelled
with its legal source and effective date.

If the table is empty (fresh DB before seeding) the DEFAULT_RATES below are used so
the engines never crash on a missing row.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.hr import StatutoryConfig

DEFAULT_RATES: dict[str, dict] = {
    "napsa": {
        "employee": 0.05,
        "employer": 0.05,
        "cap": None,
        "source": "NAPSA Act (2026 review)",
        "effective": "2026-01-01",
        "description": "National Pension Scheme Authority contribution (5% employee / 5% employer).",
    },
    "nhima": {
        "employee": 0.01,
        "employer": 0.01,
        "cap": None,
        "source": "NHIMA Act (2026 review)",
        "effective": "2026-01-01",
        "description": "National Health Insurance Management Authority contribution (1% employee / 1% employer).",
    },
    "paye": {
        "bands": [
            {"floor": 0, "ceiling": 300, "rate": 0.00},
            {"floor": 300, "ceiling": 800, "rate": 0.25},
            {"floor": 800, "ceiling": 2000, "rate": 0.30},
            {"floor": 2000, "ceiling": 5000, "rate": 0.35},
            {"floor": 5000, "ceiling": None, "rate": 0.40},
        ],
        "source": "ZRA PAYE tax table (2026)",
        "effective": "2026-01-01",
        "description": "Progressive monthly PAYE bands applied to taxable pay (gross after NAPSA).",
    },
    "overtime": {
        "normal_multiplier": 1.25,
        "rest_day_multiplier": 1.50,
        "public_holiday_multiplier": 2.00,
        "weekly_threshold_hours": 48.0,
        "standard_daily_hours": 8.0,
        "monthly_hours": 208.0,
        "source": "Employment Code Act 2019 (fair labour standards)",
        "effective": "2026-01-01",
        "description": "Overtime is paid on hours beyond the 48-hour weekly threshold; public-holiday and rest-day work at a higher multiplier.",
    },
    "night_work": {
        "window_start": "18:00",
        "window_end": "06:00",
        "premium_rate": 0.10,
        "source": "Employment Code Act 2019 night work premium (10% typical)",
        "effective": "2026-01-01",
        "description": "Night work window 18:00-06:00; hours inside it earn a premium above base hourly rate.",
    },
    "leave_annual": {
        "days_per_month": 2.0,
        "eligible_after_months": 12,
        "max_carryover": 15.0,
        "paid_out_year_end": True,
        "working_days_per_month": 26.0,
        "source": "Employment Code Act 2019 s.33 (annual leave)",
        "effective": "2026-01-01",
        "description": "Annual leave accrues 2 days/month after 12 months; unpaid balance is paid out at year end, carryover capped at 15 days.",
    },
}

DISPLAY = {
    "napsa": ("NAPSA contribution", "statutory_deduction"),
    "nhima": ("NHIMA contribution", "statutory_deduction"),
    "paye": ("PAYE (income tax) bands", "taxation"),
    "overtime": ("Overtime / rest-day / holiday rules", "labour_standard"),
    "night_work": ("Night work window & premium", "labour_standard"),
    "leave_annual": ("Annual leave accrual", "leave"),
}


def _strip_meta(value: dict) -> dict:
    """Separate the editable payload from the label metadata."""
    out = {k: v for k, v in value.items() if k not in ("source", "effective", "description")}
    return out


def seed_statutory_config(db: Session) -> int:
    """Insert the default rate rows if none exist. Returns rows inserted."""
    if db.scalar(select(StatutoryConfig.id).limit(1)):
        return 0
    created = 0
    for key, payload in DEFAULT_RATES.items():
        display_name, category = DISPLAY.get(key, (key, "labour_standard"))
        db.add(
            StatutoryConfig(
                config_key=key,
                display_name=display_name,
                category=category,
                value=_strip_meta(payload),
                effective_date=date.fromisoformat(payload["effective"]),
                source=payload["source"],
                description=payload.get("description"),
            )
        )
        created += 1
    db.commit()
    return created


def get_effective_rates(db: Session, as_of: date | None = None) -> dict[str, dict]:
    """Latest effective config value per key (effective_date <= as_of). Falls back to
    DEFAULT_RATES for any key that has no row, so a fresh DB still works."""
    as_of = as_of or date.today()
    rows = db.scalars(
        select(StatutoryConfig).where(StatutoryConfig.effective_date <= as_of).order_by(
            StatutoryConfig.config_key, StatutoryConfig.effective_date.desc()
        )
    ).all()
    merged: dict[str, dict] = {}
    for key, defaults in DEFAULT_RATES.items():
        merged[key] = dict(defaults)
    for row in rows:
        merged[row.config_key] = {
            **row.value,
            "source": row.source,
            "effective": row.effective_date.isoformat(),
            "description": row.description or "",
        }
    return merged


def statutory_sources(db: Session) -> list[dict]:
    """Source + effective-date labels for every key (for the UI's rate tables)."""
    rows = db.scalars(select(StatutoryConfig).order_by(StatutoryConfig.config_key, StatutoryConfig.effective_date.desc())).all()
    seen: dict[str, dict] = {}
    for row in rows:
        if row.config_key not in seen:
            seen[row.config_key] = {
                "config_key": row.config_key,
                "display_name": row.display_name,
                "category": row.category,
                "source": row.source,
                "effective_date": row.effective_date.isoformat(),
                "value": row.value,
                "description": row.description or "",
            }
    return list(seen.values())


def upsert_config(db: Session, config_key: str, value: dict, source: str, effective_date: date) -> StatutoryConfig:
    """Admin update: insert a new version dated today (existing rows are kept for history)."""
    row = StatutoryConfig(
        config_key=config_key,
        display_name=DISPLAY.get(config_key, (config_key, "labour_standard"))[0],
        category=DISPLAY.get(config_key, (config_key, "labour_standard"))[1],
        value=value,
        effective_date=effective_date,
        source=source,
        description=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def paye_tax(taxable: float, bands: list[dict]) -> float:
    """Progressive PAYE across [floor, ceiling) bands with rate."""
    total = 0.0
    for band in bands:
        floor = float(band["floor"])
        rate = float(band["rate"])
        if taxable <= floor:
            continue
        if band.get("ceiling") is None:
            total += (taxable - floor) * rate
        else:
            ceiling = float(band["ceiling"])
            total += (min(taxable, ceiling) - floor) * rate
    return round(total, 2)


def paye_bands_from_rates(rates: dict) -> list[dict]:
    return [{"floor": b.get("floor"), "ceiling": b.get("ceiling"), "rate": b.get("rate")} for b in rates["paye"]["bands"]]
