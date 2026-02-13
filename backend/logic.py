# Business logic - incentive design implementation
from __future__ import annotations

from models import Clinic, Episode, clinics, episodes
from typing import Dict, List, Optional, Tuple, DefaultDict
from collections import defaultdict

def get_clinic(clinic_id: str) -> Optional[Clinic]:
    """Get clinic by ID"""
    return clinics.get(clinic_id)


def get_network_status(context_level: int) -> str:
    """Get network status label for a given context level (incentive badge)."""
    status_map = {0: "Isolated", 1: "Basic", 2: "Collaborative", 3: "Trusted Contributor"}
    return status_map.get(context_level, "Isolated")

def update_clinic_settings(clinic_id: str, opted_in: bool, contribution_pct: int) -> Optional[Clinic]:
    """Update clinic settings. When opted_in is False, contribution_pct is always stored as 0."""
    clinic = clinics.get(clinic_id)
    if clinic:
        clinic.optedIn = opted_in
        if opted_in:
            clinic.contributionPct = max(0, min(100, contribution_pct))  # Clamp 0-100
        else:
            clinic.contributionPct = 0  # Guard: opted out must always be 0
    return clinic

def get_raw_episodes_from_other_clinics(fingerprint: str, requesting_clinic_id: str) -> List[Episode]:
    """Get all episodes for a fingerprint from other clinics (no filtering)."""
    return [ep for ep in episodes if ep.fingerprint == fingerprint and ep.clinicId != requesting_clinic_id]

def get_locked_preview(context_level: int) -> List[str]:
    """Get preview of what unlocks at next level"""
    if context_level == 0:
        return [
            "Conditions and date ranges",
            "Contributing clinics count"
        ]
    elif context_level == 1:
        return [
            "Intervention categories",
            "Response trend (improving/plateau/worse)"
        ]
    elif context_level == 2:
        return [
            "Red flags",
            "Timeline (short bullets)",
            "Last seen date"
        ]
    else:  # Level 3
        return []  # No more unlocks

def get_level_for_contribution(opted_in: bool, contribution_pct: int) -> int:
    """Calculate context level for a given contribution percentage"""
    if not opted_in or contribution_pct < 10:
        return 0
    elif contribution_pct < 40:
        return 1
    elif contribution_pct < 80:
        return 2
    else:
        return 3

def get_what_if_unlocks(current_pct: int, opted_in: bool) -> List[Dict]:
    """Get what-if scenarios showing what unlocks at different contribution levels"""
    current_level = get_level_for_contribution(opted_in, current_pct)
    
    scenarios = []
    
    # Level thresholds and their unlocks
    level_thresholds = [
        (10, 1, ["Conditions and date ranges", "Contributing clinics"]),
        (40, 2, ["Intervention categories", "Response trend"]),
        (80, 3, ["Red flags", "Timeline", "Last seen date"]),
    ]
    
    for threshold, level, unlocks in level_thresholds:
        if level > current_level:
            scenarios.append({
                "targetPct": threshold,
                "targetLevel": level,
                "unlocks": unlocks,
                "increaseNeeded": max(0, threshold - current_pct)
            })
    
    return scenarios

def get_worst_response_trend(trends: List[str]) -> str:
    """Choose worst severity: worse > plateau > improving"""
    if "worse" in trends:
        return "worse"
    elif "plateau" in trends:
        return "plateau"
    elif "improving" in trends:
        return "improving"
    return ""

def contributor_summary_for_visible_level(
    contributor_episodes: List[Episode],
    visible_level: int,
) -> Optional[Dict]:
    """
    Build a contributorSummary filtered by visible_level.
    Level 1: conditions + dateRanges
    Level 2: + interventions + responseTrend (worst)
    Level 3: + redFlags + timeline (cap 5) + lastSeenDate
    """
    if visible_level <= 0 or not contributor_episodes:
        return None

    summary: Dict = {}

    # Level 1
    if visible_level >= 1:
        conditions: List[str] = []
        date_ranges: List[Dict[str, str]] = []
        for ep in contributor_episodes:
            conditions.extend(ep.conditions)
            if ep.startDate and ep.endDate:
                date_ranges.append({"start": ep.startDate, "end": ep.endDate})
        summary["conditions"] = list(set(conditions))
        summary["dateRanges"] = date_ranges

    # Level 2
    if visible_level >= 2:
        interventions: List[str] = []
        trends: List[str] = []
        for ep in contributor_episodes:
            interventions.extend(ep.interventions)
            if ep.responseTrend:
                trends.append(ep.responseTrend)
        summary["interventions"] = list(set(interventions))
        summary["responseTrend"] = get_worst_response_trend(trends)

    # Level 3
    if visible_level >= 3:
        red_flags: List[str] = []
        timeline: List[str] = []
        last_seen_date = ""
        for ep in contributor_episodes:
            red_flags.extend(ep.redFlags)
            timeline.extend(ep.timeline)
            if ep.endDate > last_seen_date:
                last_seen_date = ep.endDate
        summary["redFlags"] = list(set(red_flags))
        summary["timeline"] = timeline[:5]
        summary["lastSeenDate"] = last_seen_date

    return summary

def aggregate_shared_summary_from_contributors(
    contributor_summaries: Dict[str, Tuple[int, Dict]],
) -> Optional[Dict]:
    """
    Aggregate contributorSummaries into sharedSummary:
    - conditions: union
    - dateRanges: list
    - interventions: union (only from visibleLevel>=2 contributors)
    - responseTrend: worst across visibleLevel>=2 contributors
    - redFlags/timeline/lastSeenDate: only from visibleLevel>=3 contributors
    """
    if not contributor_summaries:
        return None

    conditions: set[str] = set()
    date_ranges: List[Dict[str, str]] = []
    interventions: set[str] = set()
    trends: List[str] = []
    red_flags: set[str] = set()
    timeline: List[str] = []
    last_seen_date = ""

    for _clinic_id, (visible_level, summary) in contributor_summaries.items():
        if visible_level >= 1:
            conditions.update(summary.get("conditions", []) or [])
            date_ranges.extend(summary.get("dateRanges", []) or [])

        if visible_level >= 2:
            interventions.update(summary.get("interventions", []) or [])
            if summary.get("responseTrend"):
                trends.append(summary["responseTrend"])

        if visible_level >= 3:
            red_flags.update(summary.get("redFlags", []) or [])
            timeline.extend(summary.get("timeline", []) or [])
            lsd = summary.get("lastSeenDate") or ""
            if lsd > last_seen_date:
                last_seen_date = lsd

    aggregated: Dict = {
        "conditions": sorted(list(conditions)),
        "dateRanges": date_ranges,
    }

    if interventions:
        aggregated["interventions"] = sorted(list(interventions))
    if trends:
        aggregated["responseTrend"] = get_worst_response_trend(trends)

    if red_flags:
        aggregated["redFlags"] = sorted(list(red_flags))
    if timeline:
        aggregated["timeline"] = timeline[:5]
    if last_seen_date:
        aggregated["lastSeenDate"] = last_seen_date

    return aggregated

def check_patient_match(
    fingerprint: str, 
    requesting_clinic_id: str
) -> Dict:
    """
    Check for patient matches with per-contributor detail gating.
    """
    clinic = get_clinic(requesting_clinic_id)
    if not clinic:
        return {"error": "Clinic not found"}
    
    requester_level = clinic.get_context_level()

    # raw episodes (other clinics) BEFORE filtering
    raw_episodes = get_raw_episodes_from_other_clinics(fingerprint, requesting_clinic_id)
    match_found = len(raw_episodes) > 0

    # Only opted-in contributor clinics are eligible
    opted_in_episodes: List[Episode] = []
    for ep in raw_episodes:
        contributor = get_clinic(ep.clinicId)
        if contributor and contributor.optedIn:
            opted_in_episodes.append(ep)

    # Group by contributor clinicId
    by_contributor: DefaultDict[str, List[Episode]] = defaultdict(list)
    for ep in opted_in_episodes:
        by_contributor[ep.clinicId].append(ep)

    contributing_clinics_count = len(by_contributor.keys())
    detail_capped_clinics_count = 0
    contributing_clinic_details: List[Dict] = []

    contributor_summaries: Dict[str, Tuple[int, Dict]] = {}
    for contributor_id, eps in by_contributor.items():
        contributor_clinic = get_clinic(contributor_id)
        if not contributor_clinic:
            continue
        contributor_level = contributor_clinic.get_context_level()
        visible_level = min(requester_level, contributor_level)
        is_capped = contributor_level < requester_level
        if is_capped:
            detail_capped_clinics_count += 1
        
        # Add clinic details for display (including network_status for badge)
        contributing_clinic_details.append({
            "clinicId": contributor_id,
            "clinicName": contributor_clinic.name,
            "contributorLevel": contributor_level,
            "visibleLevel": visible_level,
            "isCapped": is_capped,
            "networkStatus": get_network_status(contributor_level)
        })
        
        contrib_summary = contributor_summary_for_visible_level(eps, visible_level)
        if contrib_summary is not None:
            contributor_summaries[contributor_id] = (visible_level, contrib_summary)
    
    # Build response
    result = {
        "matchFound": match_found,
        "fingerprint": fingerprint,
        "requestingClinic": {
            "clinicId": clinic.clinicId,
            "optedIn": clinic.optedIn,
            "contributionPct": clinic.contributionPct,
            "contextLevel": requester_level
        },
        "networkStats": {
            "participatingClinicsCount": sum(1 for c in clinics.values() if c.optedIn),
            "participatingClinicsPct": round(sum(1 for c in clinics.values() if c.optedIn) / len(clinics) * 100) if clinics else 0
        },
        "contributionGating": {
            "contributingClinicsCount": contributing_clinics_count,
            "detailCappedClinicsCount": detail_capped_clinics_count,
            "contributingClinics": contributing_clinic_details,
            "reason": "Detail is capped by the contributor clinic's participation level (min(context levels))."
        },
        "lockedPreview": {
            "nextLevelUnlocks": get_locked_preview(requester_level)
        },
        "whatIf": get_what_if_unlocks(clinic.contributionPct, clinic.optedIn)
    }

    # sharedSummary behavior
    if not match_found or requester_level == 0:
        # If requesterLevel == 0: sharedSummary must be null, but keep matchFound true if rawEpisodes exist.
        result["sharedSummary"] = None
    else:
        result["sharedSummary"] = aggregate_shared_summary_from_contributors(contributor_summaries)
    
    return result
