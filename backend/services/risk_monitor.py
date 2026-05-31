"""Weighted risk scoring from recent vitals + fall override.

Computes a 0–100 score and CTAS-aligned severity from the latest wearable
readings. A recent fall_suspected / fall_confirmed instantly forces critical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlmodel import Session, select

from backend.db.models import SeverityTier, Vital

RiskLevel = Literal["low", "moderate", "high", "critical"]

WEIGHT_HR = 0.30
WEIGHT_SPO2 = 0.30
WEIGHT_BP = 0.20
WEIGHT_FRESHNESS = 0.20

METRIC_WINDOW = timedelta(minutes=30)
FALL_WINDOW = timedelta(minutes=30)
FRESH_OK = timedelta(minutes=5)
FRESH_STALE = timedelta(minutes=30)

# Stale data is a data-quality concern, not a clinical emergency. Cap the
# freshness factor so a wearable that simply stopped syncing can never, on its
# own, push the composite score into "high"/"critical" (i.e. call an ambulance).
FRESH_MAX_SCORE = 50.0


@dataclass(frozen=True)
class RiskFactor:
    name: str
    score: float  # 0–100 contribution for this factor
    weight: float
    detail: str


@dataclass(frozen=True)
class RiskSnapshot:
    score: float
    level: RiskLevel
    severity_tier: SeverityTier
    factors: list[RiskFactor] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "severity_tier": self.severity_tier.value,
            "factors": [
                {
                    "name": f.name,
                    "score": f.score,
                    "weight": f.weight,
                    "detail": f.detail,
                }
                for f in self.factors
            ],
            "updated_at": self.updated_at.isoformat(),
        }


def _level_from_score(score: float) -> RiskLevel:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "moderate"
    return "low"


def _severity_for_level(level: RiskLevel) -> SeverityTier:
    return {
        "low": SeverityTier.WHISPER,
        "moderate": SeverityTier.NUDGE,
        "high": SeverityTier.ALARM,
        "critical": SeverityTier.CALL,
    }[level]


def _score_hr(bpm: float) -> tuple[float, str]:
    if 60 <= bpm <= 100:
        return 0.0, f"{bpm:.0f} bpm (normal)"
    if bpm > 100:
        if bpm <= 120:
            excess = (bpm - 100) / 20
            return min(100.0, excess * 50), f"{bpm:.0f} bpm (elevated)"
        excess = (bpm - 120) / 40
        return min(100.0, 50 + excess * 50), f"{bpm:.0f} bpm (high)"
    if bpm >= 50:
        deficit = (60 - bpm) / 10
        return min(100.0, deficit * 50), f"{bpm:.0f} bpm (low)"
    deficit = (50 - bpm) / 20
    return min(100.0, 50 + deficit * 50), f"{bpm:.0f} bpm (very low)"


def _score_spo2(pct: float) -> tuple[float, str]:
    if pct >= 95:
        return 0.0, f"{pct:.0f}% (normal)"
    if pct >= 92:
        return (95 - pct) / 3 * 40, f"{pct:.0f}% (mildly low)"
    if pct >= 88:
        return 40 + (92 - pct) / 4 * 40, f"{pct:.0f}% (low)"
    return min(100.0, 80 + (88 - pct) * 5), f"{pct:.0f}% (critical)"


def _score_bp(systolic: float, diastolic: float | None = None) -> tuple[float, str]:
    detail = f"{systolic:.0f}/{diastolic:.0f} mmHg" if diastolic else f"{systolic:.0f} mmHg"
    if 90 <= systolic <= 140:
        return 0.0, f"{detail} (normal)"
    if systolic > 140:
        if systolic <= 160:
            excess = (systolic - 140) / 20
            return min(100.0, excess * 50), f"{detail} (elevated)"
        excess = (systolic - 160) / 40
        return min(100.0, 50 + excess * 50), f"{detail} (high)"
    if systolic >= 90:
        return 0.0, detail
    deficit = (90 - systolic) / 30
    return min(100.0, deficit * 100), f"{detail} (hypotension)"


def _score_freshness(age: timedelta) -> tuple[float, str]:
    if age <= FRESH_OK:
        mins = int(age.total_seconds() // 60)
        return 0.0, f"updated {mins} min ago"
    if age >= FRESH_STALE:
        return FRESH_MAX_SCORE, "no recent vitals (>30 min)"
    span = (age - FRESH_OK).total_seconds()
    window = (FRESH_STALE - FRESH_OK).total_seconds()
    score = min(FRESH_MAX_SCORE, span / window * FRESH_MAX_SCORE)
    mins = int(age.total_seconds() // 60)
    return score, f"last reading {mins} min ago"


def _latest_vital(
    session: Session,
    patient_id: int,
    kind: str,
    cutoff: datetime,
) -> Vital | None:
    stmt = (
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.kind == kind)
        .where(Vital.ts >= cutoff)
        .order_by(Vital.ts.desc())  # type: ignore[arg-type]
    )
    return session.exec(stmt).first()


def _active_fall(
    session: Session,
    patient_id: int,
    cutoff: datetime,
) -> Vital | None:
    """Most recent fall event in window; cancelled clears a prior suspected."""
    stmt = (
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.kind.like("fall%"))
        .where(Vital.ts >= cutoff)
        .order_by(Vital.ts.desc())  # type: ignore[arg-type]
    )
    rows = session.exec(stmt).all()
    for row in rows:
        if row.kind == "fall_cancelled":
            return None
        if row.kind in ("fall_suspected", "fall_confirmed"):
            return row
    return None


def compute_risk(session: Session, patient_id: int) -> RiskSnapshot:
    """Score the patient from recent vitals; fall override wins."""
    now = datetime.utcnow()
    cutoff = now - METRIC_WINDOW

    fall = _active_fall(session, patient_id, now - FALL_WINDOW)
    if fall is not None:
        label = "Fall confirmed" if fall.kind == "fall_confirmed" else "Possible fall detected"
        return RiskSnapshot(
            score=100.0,
            level="critical",
            severity_tier=SeverityTier.CALL,
            factors=[
                RiskFactor(
                    name="Fall detected",
                    score=100.0,
                    weight=1.0,
                    detail=f"{label} · peak {fall.value:.1f} g",
                ),
            ],
            updated_at=now.replace(tzinfo=UTC),
        )

    factors: list[RiskFactor] = []
    latest_ts: datetime | None = None

    hr_row = _latest_vital(session, patient_id, "hr", cutoff)
    if hr_row is not None:
        hr_score, detail = _score_hr(hr_row.value)
        factors.append(
            RiskFactor(name="Heart rate", score=hr_score, weight=WEIGHT_HR, detail=detail),
        )
        latest_ts = hr_row.ts

    spo2_row = _latest_vital(session, patient_id, "spo2", cutoff)
    if spo2_row is not None:
        spo2_score, detail = _score_spo2(spo2_row.value)
        factors.append(
            RiskFactor(name="SpO₂", score=spo2_score, weight=WEIGHT_SPO2, detail=detail),
        )
        if latest_ts is None or spo2_row.ts > latest_ts:
            latest_ts = spo2_row.ts

    bp_row = _latest_vital(session, patient_id, "bp_systolic", cutoff)
    if bp_row is None:
        bp_row = _latest_vital(session, patient_id, "bp", cutoff)
    if bp_row is not None:
        bp_score, detail = _score_bp(bp_row.value)
        factors.append(
            RiskFactor(name="Blood pressure", score=bp_score, weight=WEIGHT_BP, detail=detail),
        )
        if latest_ts is None or bp_row.ts > latest_ts:
            latest_ts = bp_row.ts

    if latest_ts is not None:
        age = now - latest_ts
        fresh_score, detail = _score_freshness(age)
        factors.append(
            RiskFactor(
                name="Data freshness",
                score=fresh_score,
                weight=WEIGHT_FRESHNESS,
                detail=detail,
            ),
        )
    else:
        factors.append(
            RiskFactor(
                name="Data freshness",
                score=FRESH_MAX_SCORE,
                weight=WEIGHT_FRESHNESS,
                detail="no vitals in the last 30 min — sensor may be offline",
            ),
        )

    if not factors:
        return RiskSnapshot(
            score=0.0,
            level="low",
            severity_tier=SeverityTier.WHISPER,
            factors=[],
            updated_at=now.replace(tzinfo=UTC),
        )

    weighted = sum(f.score * f.weight for f in factors)
    total_weight = sum(f.weight for f in factors)
    score = round(weighted / total_weight, 1) if total_weight else 0.0
    level = _level_from_score(score)

    return RiskSnapshot(
        score=score,
        level=level,
        severity_tier=_severity_for_level(level),
        factors=factors,
        updated_at=now.replace(tzinfo=UTC),
    )


class RiskMonitor:
    """Holds last snapshot per patient for SSE dedup."""

    def __init__(self) -> None:
        self._last: dict[int, RiskSnapshot] = {}

    def compute(self, session: Session, patient_id: int) -> tuple[RiskSnapshot, bool]:
        snapshot = compute_risk(session, patient_id)
        changed = self.changed(patient_id, snapshot)
        self._last[patient_id] = snapshot
        return snapshot, changed

    def last(self, patient_id: int) -> RiskSnapshot | None:
        return self._last.get(patient_id)

    def changed(self, patient_id: int, snapshot: RiskSnapshot) -> bool:
        prev = self._last.get(patient_id)
        if prev is None:
            return True
        return (
            prev.score != snapshot.score
            or prev.level != snapshot.level
            or len(prev.factors) != len(snapshot.factors)
        )
