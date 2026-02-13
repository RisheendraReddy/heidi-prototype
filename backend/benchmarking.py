# Outcome benchmarking - anonymized, safe fields only (interventions, response trend)
# NEVER includes Level 3 fields (red flags, timeline, last seen)
from __future__ import annotations

from collections import Counter
from typing import Dict, List
from models import clinics, episodes
from logic import get_level_for_contribution

ZERO_DIST = {"improving": 0.0, "plateau": 0.0, "worse": 0.0}


def _participating_clinic_ids() -> List[str]:
    """Clinics that count in network average: computed_level >= 1 only. Do NOT use opted_in alone."""
    return [
        c.clinicId
        for c in clinics.values()
        if get_level_for_contribution(c.optedIn, c.contributionPct) >= 1
    ]


def get_clinic_response_trend_distribution(clinic_id: str, n: int = 100) -> Dict[str, float]:
    """
    Get distribution of response trends for a clinic's last N episodes.
    Uses only safe fields: responseTrend (improving/plateau/worse).
    """
    clinic_episodes = [ep for ep in episodes if ep.clinicId == clinic_id]
    trends = [ep.responseTrend for ep in clinic_episodes[-n:] if ep.responseTrend]
    
    if not trends:
        return dict(ZERO_DIST)
    
    total = len(trends)
    counter = Counter(trends)
    return {
        "improving": round(counter.get("improving", 0) / total, 2),
        "plateau": round(counter.get("plateau", 0) / total, 2),
        "worse": round(counter.get("worse", 0) / total, 2),
    }


def get_network_average_response_trend_distribution(
    participating_ids: List[str] | None = None,
    n: int = 500,
) -> Dict[str, float]:
    """
    Get anonymized network average distribution of response trends.
    Aggregates across participating clinics only (optedIn AND level > 0).
    """
    ids = participating_ids if participating_ids is not None else _participating_clinic_ids()
    all_trends: List[str] = []

    for clinic_id in ids:
        clinic_episodes = [ep for ep in episodes if ep.clinicId == clinic_id]
        trends = [ep.responseTrend for ep in clinic_episodes[-n:] if ep.responseTrend]
        all_trends.extend(trends)
    
    if not all_trends:
        return dict(ZERO_DIST)
    
    total = len(all_trends)
    counter = Counter(all_trends)
    return {
        "improving": round(counter.get("improving", 0) / total, 2),
        "plateau": round(counter.get("plateau", 0) / total, 2),
        "worse": round(counter.get("worse", 0) / total, 2),
    }


def get_clinic_benchmark(clinic_id: str) -> Dict:
    """
    Get benchmark for a clinic: clinic vs network average.
    Returns eligible=false when: clinic is opted out/level 0, or no participating clinics.
    """
    clinic = clinics.get(clinic_id)
    if not clinic:
        return {
            "eligible": False,
            "reason": "clinic_not_found",
            "clinicDistribution": dict(ZERO_DIST),
            "networkAverage": dict(ZERO_DIST),
            "you": dict(ZERO_DIST),
            "network": dict(ZERO_DIST),
            "participating_count": 0,
        }

    participating = _participating_clinic_ids()
    level = get_level_for_contribution(clinic.optedIn, clinic.contributionPct)

    # Requester must have level >= 1 to view benchmarking
    if not clinic.optedIn:
        reason = "not_opted_in"
    elif level < 1:
        reason = "locked_level_0"
    else:
        reason = None

    if reason is not None:
        return {
            "eligible": False,
            "reason": reason,
            "clinicDistribution": dict(ZERO_DIST),
            "networkAverage": dict(ZERO_DIST),
            "you": dict(ZERO_DIST),
            "network": dict(ZERO_DIST),
            "participating_count": len(participating),
        }

    # Network = other participating clinics (exclude self). No "others" -> no_participants.
    other_participants = [pid for pid in participating if pid != clinic_id]
    if not other_participants:
        clinic_dist = get_clinic_response_trend_distribution(clinic_id)
        return {
            "eligible": False,
            "reason": "no_participants",
            "clinicDistribution": clinic_dist,
            "networkAverage": dict(ZERO_DIST),
            "you": clinic_dist,
            "network": dict(ZERO_DIST),
            "participating_count": 0,
        }

    clinic_dist = get_clinic_response_trend_distribution(clinic_id)
    network_dist = get_network_average_response_trend_distribution(other_participants)
    return {
        "eligible": True,
        "reason": None,
        "clinicDistribution": clinic_dist,
        "networkAverage": network_dist,
        "you": clinic_dist,
        "network": network_dist,
        "participating_count": len(other_participants),
    }
