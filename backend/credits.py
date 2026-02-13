# Continuity credits - in-memory store for credits earned when shared history is used
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# In-memory store
_clinic_credits: Dict[str, int] = defaultdict(int)
_credit_events: List[dict] = []
_recorded_event_keys: Set[str] = set()


def _event_key(patient_key: str, from_clinic_id: str, to_clinic_id: str) -> str:
    """Deterministic key for idempotency: one credit per (patient, from_clinic, to_clinic)."""
    return f"{patient_key}:{from_clinic_id}:{to_clinic_id}"


def award_continuity_credits(
    fingerprint: str,
    to_clinic_id: str,
    contributing_clinics_with_visible_level: List[tuple[str, int]],
) -> Tuple[List[dict], bool]:
    """
    Award continuity credits to contributing clinics when Clinic Y uses shared history
    to continue care. Only clinics with visible_level > 0 receive credits.
    Idempotent: each event_key (patient:from:to) is credited at most once.

    Returns (events, credited) where credited=True if any new credits were awarded.
    """
    events = []
    timestamp = datetime.now(timezone.utc).isoformat()
    any_new = False

    for clinic_id, visible_level in contributing_clinics_with_visible_level:
        if visible_level <= 0:
            continue

        key = _event_key(fingerprint, clinic_id, to_clinic_id)
        if key in _recorded_event_keys:
            continue

        _recorded_event_keys.add(key)
        _clinic_credits[clinic_id] += 1
        event = {
            "patientId": fingerprint,
            "fromClinic": clinic_id,
            "toClinic": to_clinic_id,
            "timestamp": timestamp,
        }
        _credit_events.append(event)
        events.append(event)
        any_new = True

    return events, any_new


def get_clinic_credits(clinic_id: str) -> int:
    """Get total continuity credits for a clinic."""
    return _clinic_credits.get(clinic_id, 0)


def get_all_clinic_credits() -> Dict[str, int]:
    """Get credits for all clinics."""
    return dict(_clinic_credits)


def get_recent_credit_events(limit: int = 5) -> List[dict]:
    """Get last N credit events (most recent first)."""
    return list(reversed(_credit_events[-limit:]))


def reset_credits():
    """Reset credits and recorded keys (for testing)."""
    global _clinic_credits, _credit_events, _recorded_event_keys
    _clinic_credits = defaultdict(int)
    _credit_events = []
    _recorded_event_keys = set()
