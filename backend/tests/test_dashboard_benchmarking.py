"""
Reviewer-requested tests for Dashboard benchmarking, credits, idempotency, and demo reset.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from seed import seed_data
from credits import reset_credits

# -------------------------
# Fixtures
# -------------------------

@pytest.fixture(autouse=True)
def _reset():
    """Reset to seed baseline before each test."""
    seed_data()
    reset_credits()
    yield
    reset_credits()


@pytest.fixture
def client():
    return TestClient(app)


# -------------------------
# Helpers
# -------------------------

def update_clinic(client, clinic_id: str, opted_in: bool, contribution_pct: int):
    resp = client.post(
        f"/clinics/{clinic_id}/settings",
        json={"optedIn": opted_in, "contributionPct": contribution_pct},
    )
    assert resp.status_code in (200, 204), resp.text


def get_benchmark(client, clinic_id: str):
    resp = client.get(f"/clinics/{clinic_id}/benchmark")
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_credits_dashboard(client):
    resp = client.get("/credits/dashboard")
    assert resp.status_code == 200, resp.text
    return resp.json()


def post_continue_care(client, payload: dict):
    resp = client.post("/intake/continue-care", json=payload)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# -------------------------
# Benchmarking (Dashboard) tests
# -------------------------

def test_benchmark_locked_when_not_opted_in(client):
    update_clinic(client, "A", opted_in=False, contribution_pct=85)
    data = get_benchmark(client, "A")
    assert data["eligible"] is False
    assert data["reason"] in ("not_opted_in", "locked_level_0")
    assert data["networkAverage"]["improving"] == 0.0
    assert data["networkAverage"]["plateau"] == 0.0
    assert data["networkAverage"]["worse"] == 0.0


def test_benchmark_locked_when_opted_in_but_level0(client):
    update_clinic(client, "A", opted_in=True, contribution_pct=0)
    data = get_benchmark(client, "A")
    assert data["eligible"] is False
    assert data["reason"] == "locked_level_0"
    assert data["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}


def test_benchmark_no_participants_when_no_level1_plus_clinics_exist(client):
    update_clinic(client, "A", opted_in=True, contribution_pct=0)
    update_clinic(client, "B", opted_in=True, contribution_pct=0)
    update_clinic(client, "C", opted_in=True, contribution_pct=0)

    data = get_benchmark(client, "A")

    assert data["eligible"] is False
    assert data["reason"] in ("locked_level_0", "no_participants")
    assert data["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
    assert data.get("participating_count", 0) == 0


def test_benchmark_eligible_when_requester_level1_and_network_has_other_level1(client):
    update_clinic(client, "A", opted_in=True, contribution_pct=10)  # Level 1
    update_clinic(client, "C", opted_in=True, contribution_pct=10)  # Level 1
    update_clinic(client, "B", opted_in=False, contribution_pct=0)

    data = get_benchmark(client, "A")
    assert data["eligible"] is True
    assert data["reason"] is None
    assert data.get("participating_count", 0) == 1
    you_sum = sum(data["clinicDistribution"].values())
    net_sum = sum(data["networkAverage"].values())
    assert you_sum == 0.0 or abs(you_sum - 1.0) < 0.02
    assert net_sum == 0.0 or abs(net_sum - 1.0) < 0.02


# -------------------------
# Credits Dashboard tests
# -------------------------

def test_credits_dashboard_structure(client):
    dash = get_credits_dashboard(client)
    assert "clinicCredits" in dash
    assert "recentEvents" in dash
    assert isinstance(dash["clinicCredits"], dict)
    assert isinstance(dash["recentEvents"], list)


def test_credits_dashboard_recent_events_max_5(client):
    # B requests continue-care for different patients; A and C are contributors
    update_clinic(client, "B", opted_in=True, contribution_pct=45)

    for i in range(7):
        post_continue_care(client, {
            "clinicId": "B",
            "fullName": f"Patient Number {i}",
            "dob": f"199{i}-01-15",
            "phoneLast4": f"{1000 + i}",
        })

    dash = get_credits_dashboard(client)
    assert len(dash["recentEvents"]) <= 5


def test_continue_care_is_idempotent_no_credit_inflation(client):
    """Key exploit test: duplicate clicks must NOT inflate credits."""
    update_clinic(client, "B", opted_in=True, contribution_pct=45)

    payload = {
        "clinicId": "B",
        "fullName": "John Doe",
        "dob": "1990-01-15",
        "phoneLast4": "1234",
    }

    dash_before = get_credits_dashboard(client)
    before_a = dash_before["clinicCredits"].get("A", 0)
    before_c = dash_before["clinicCredits"].get("C", 0)

    r1 = post_continue_care(client, payload)
    assert r1["credited"] is True

    r2 = post_continue_care(client, payload)  # duplicate click
    assert r2["credited"] is False

    dash_after = get_credits_dashboard(client)
    after_a = dash_after["clinicCredits"].get("A", 0)
    after_c = dash_after["clinicCredits"].get("C", 0)

    # Only +1 each, not +2
    assert after_a == before_a + 1
    assert after_c == before_c + 1

    # Event log must be stable (no phantom events from duplicate click)
    dash_after2 = get_credits_dashboard(client)
    assert dash_after2["recentEvents"][0] == dash_after["recentEvents"][0]


# -------------------------
# Demo reset
# -------------------------

def test_demo_reset_resets_credits_and_benchmark(client):
    # Generate some credits first
    update_clinic(client, "B", opted_in=True, contribution_pct=45)
    post_continue_care(client, {
        "clinicId": "B",
        "fullName": "John Doe",
        "dob": "1990-01-15",
        "phoneLast4": "1234",
    })

    resp = client.post("/demo/reset")
    if resp.status_code in (403, 404):
        pytest.skip("Demo reset disabled in this environment")
    assert resp.status_code == 200

    dash = get_credits_dashboard(client)
    assert all(v == 0 for v in dash["clinicCredits"].values()) or dash["clinicCredits"] == {}

    bench = get_benchmark(client, "A")
    assert "eligible" in bench
    assert "clinicDistribution" in bench
    assert "networkAverage" in bench


def test_adoption_scaling_participation_increases_and_benchmark_unlocks(client):
    """
    Proves the mechanism that drives 19% -> 80%:
    as more clinics cross Level 1 (>=10%), the network becomes more valuable
    (participating_count increases) and benchmarking unlocks for those clinics.
    """

    # Step 0: Start from a "low participation" world:
    # only Clinic A is Level>=1; others are Level0 or opted out.
    update_clinic(client, "A", opted_in=True, contribution_pct=10)   # Level 1
    update_clinic(client, "B", opted_in=True, contribution_pct=0)    # Level 0
    update_clinic(client, "C", opted_in=True, contribution_pct=0)    # Level 0

    # A is eligible (Level1), but has no other Level>=1 participants => no_participants
    a0 = get_benchmark(client, "A")
    assert a0["eligible"] is False
    assert a0["reason"] == "no_participants"
    assert a0.get("participating_count", 0) == 0  # no other participants

    # Step 1: Raise one more clinic above 10% (Clinic C becomes Level1)
    update_clinic(client, "C", opted_in=True, contribution_pct=10)   # Level 1

    a1 = get_benchmark(client, "A")
    assert a1["eligible"] is True
    assert a1["reason"] is None
    assert a1.get("participating_count", 0) == 1  # C is now a participant

    # Step 2: Raise the third clinic above 10% (Clinic B becomes Level1)
    update_clinic(client, "B", opted_in=True, contribution_pct=10)   # Level 1

    a2 = get_benchmark(client, "A")
    assert a2["eligible"] is True
    assert a2["reason"] is None
    assert a2.get("participating_count", 0) == 2  # B and C now participate

    # Optional: show that benchmarking also unlocks for the newly participating clinic
    b2 = get_benchmark(client, "B")
    assert b2["eligible"] is True
    assert b2["reason"] is None

    # Sanity: distributions should be valid (sum to ~1 or 0 if no episodes)
    for payload in (a1, a2, b2):
        you_sum = sum(payload["clinicDistribution"].values())
        net_sum = sum(payload["networkAverage"].values())
        assert you_sum == 0.0 or abs(you_sum - 1.0) < 0.02
        assert net_sum == 0.0 or abs(net_sum - 1.0) < 0.02
