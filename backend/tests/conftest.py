"""
Shared pytest fixtures for cross-clinic patient history sharing tests.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from models import Clinic, Episode, clinics, episodes, compute_fingerprint
from seed import seed_data
from credits import reset_credits

# Patient P1 fingerprint - consistent minimal dataset
PATIENT_P1_FINGERPRINT = "p1|1990-01-15|1234"


@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def seeded_data():
    """
    Reset to seed data: A=level3, B=level0, C=level1.
    Patient 1 (John Doe) has episodes in A and C.
    """
    seed_data()
    reset_credits()
    yield
    reset_credits()


@pytest.fixture
def minimal_dataset(client):
    """
    Minimal dataset per spec:
    - P1: patient with fingerprint p1|1990-01-15|1234
    - ClinicA (A): level 3, episode includes all fields
    - ClinicB (B): level 1, episode includes L1-safe fields
    - ClinicC (C): level 0, episode exists but must be ignored (opted out)
    """
    seed_data()
    reset_credits()

    # Clear episodes and add P1 episodes
    episodes.clear()
    fp = compute_fingerprint("P1", "1990-01-15", "1234")

    # Clinic A: level 3 (85%), full episode
    clinics["A"].optedIn = True
    clinics["A"].contributionPct = 85
    episodes.append(Episode(
        episodeId="ep_p1_a",
        clinicId="A",
        fingerprint=fp,
        startDate="2023-01-15",
        endDate="2023-06-20",
        conditions=["Condition A"],
        interventions=["Intervention X"],
        responseTrend="improving",
        redFlags=["Flag 1"],
        timeline=["Event 1", "Event 2"],
    ))

    # Clinic B: level 1 (30%), L1-safe fields only
    clinics["B"].optedIn = True
    clinics["B"].contributionPct = 30
    episodes.append(Episode(
        episodeId="ep_p1_b",
        clinicId="B",
        fingerprint=fp,
        startDate="2023-07-01",
        endDate="2023-12-31",
        conditions=["Condition B"],
        interventions=["Intervention Y"],
        responseTrend="plateau",
        redFlags=[],
        timeline=[],
    ))

    # Clinic C: level 0 (opted out), episode exists but must be ignored
    clinics["C"].optedIn = False
    clinics["C"].contributionPct = 0
    episodes.append(Episode(
        episodeId="ep_p1_c",
        clinicId="C",
        fingerprint=fp,
        startDate="2024-01-01",
        endDate="2024-06-30",
        conditions=["Condition C"],
        interventions=["Intervention Z"],
        responseTrend="worse",
        redFlags=["Flag C"],
        timeline=["Event C"],
    ))

    # Clinic D: level 3 requester (for tests needing requester != A)
    clinics["D"] = Clinic(clinicId="D", name="Clinic D", optedIn=True, contributionPct=90)
    episodes.append(Episode(
        episodeId="ep_p1_d",
        clinicId="D",
        fingerprint=fp,
        startDate="2024-01-01",
        endDate="2024-06-30",
        conditions=["Condition D"],
        interventions=["Intervention D"],
        responseTrend="improving",
        redFlags=["Flag D"],
        timeline=["Event D"],
    ))

    yield fp
    clinics.pop("D", None)
    episodes[:] = [ep for ep in episodes if ep.episodeId != "ep_p1_d"]
    reset_credits()


def assert_summary_gate_level(summary, level: int):
    """Helper: assert presence/absence of keys per visible_level."""
    level_1_fields = {"conditions", "dateRanges"}
    level_2_fields = level_1_fields | {"interventions", "responseTrend"}
    level_3_fields = level_2_fields | {"redFlags", "timeline", "lastSeenDate"}
    forbidden = {"redFlags", "timeline", "lastSeenDate"}

    if level == 0:
        assert summary is None or (isinstance(summary, dict) and not any(
            summary.get(k) for k in level_3_fields
        ))
        return
    if summary is None:
        pytest.fail("Expected non-null summary for level > 0")

    if level >= 1:
        for k in level_1_fields:
            assert k in summary, f"Level 1: expected {k}"
    if level >= 2:
        for k in ["interventions", "responseTrend"]:
            assert k in summary, f"Level 2: expected {k}"
    if level >= 3:
        for k in ["redFlags", "timeline", "lastSeenDate"]:
            assert k in summary, f"Level 3: expected {k}"

    if level < 2:
        for k in ["interventions", "responseTrend"]:
            assert k not in summary, f"Level {level}: must not leak {k}"
    if level < 3:
        for k in forbidden:
            assert k not in summary, f"Level {level}: must not leak {k}"
