"""
Tests for incentive mechanisms: network status, continuity credits, benchmarking.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Clinic, Episode, clinics, episodes, compute_fingerprint
from logic import get_network_status, check_patient_match
from credits import (
    award_continuity_credits,
    get_clinic_credits,
    get_all_clinic_credits,
    get_recent_credit_events,
    reset_credits,
)
from benchmarking import (
    get_clinic_response_trend_distribution,
    get_network_average_response_trend_distribution,
    get_clinic_benchmark,
)
from seed import seed_data


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset seed data and credits before each test"""
    seed_data()
    reset_credits()
    yield
    reset_credits()


# =============================================================================
# Network Status / Badge
# =============================================================================
class TestNetworkStatus:
    """Tests for get_network_status (participation badge)"""
    
    def test_level_0_isolated(self):
        assert get_network_status(0) == "Isolated"
    
    def test_level_1_basic(self):
        assert get_network_status(1) == "Basic"
    
    def test_level_2_collaborative(self):
        assert get_network_status(2) == "Collaborative"
    
    def test_level_3_trusted_contributor(self):
        assert get_network_status(3) == "Trusted Contributor"
    
    def test_unknown_level_defaults_to_isolated(self):
        assert get_network_status(99) == "Isolated"
        assert get_network_status(-1) == "Isolated"


# =============================================================================
# Continuity Credits
# =============================================================================
class TestContinuityCredits:
    """Tests for continuity credit mechanism"""
    
    def test_credits_only_awarded_to_opted_in_contributors(self):
        """Credits only go to opted-in clinics with visible_level > 0"""
        # Award to A (Level 3) and C (Level 1) - both opted in
        events, _ = award_continuity_credits(
            fingerprint="john|1990-01-15|1234",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 3), ("C", 1)],
        )
        assert len(events) == 2
        assert get_clinic_credits("A") == 1
        assert get_clinic_credits("C") == 1
    
    def test_credits_not_awarded_when_visible_level_zero(self):
        """No credits when visible_level = 0"""
        events, _ = award_continuity_credits(
            fingerprint="test",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 0), ("C", 0)],
        )
        assert len(events) == 0
        assert get_clinic_credits("A") == 0
        assert get_clinic_credits("C") == 0
    
    def test_credits_awarded_to_multiple_contributors(self):
        """Multiple contributors in one history request each get a credit"""
        events, _ = award_continuity_credits(
            fingerprint="john|1990-01-15|1234",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 3), ("C", 1)],
        )
        assert len(events) == 2
        assert get_clinic_credits("A") == 1
        assert get_clinic_credits("C") == 1
        
        # Event structure
        assert all("patientId" in e and "fromClinic" in e and "toClinic" in e and "timestamp" in e for e in events)
    
    def test_mixed_visible_levels_only_awards_positive(self):
        """Only contributors with visible_level > 0 get credits"""
        events, _ = award_continuity_credits(
            fingerprint="test",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 3), ("X", 0), ("C", 1)],
        )
        assert len(events) == 2  # A and C only, not X
        assert get_clinic_credits("A") == 1
        assert get_clinic_credits("C") == 1
        assert get_clinic_credits("X") == 0
    
    def test_recent_events_ordered_most_recent_first(self):
        award_continuity_credits("fp1", "B", [("A", 1)])
        award_continuity_credits("fp2", "B", [("C", 1)])
        events = get_recent_credit_events(5)
        assert len(events) == 2
        # Most recent last in raw list, reversed so first in output
        assert events[0]["patientId"] == "fp2"
        assert events[1]["patientId"] == "fp1"


# =============================================================================
# Outcome Benchmarking
# =============================================================================
class TestBenchmarking:
    """Tests for outcome benchmarking module"""
    
    def test_benchmarking_never_includes_level_3_fields(self):
        """Benchmark output has only interventions/response trend - no red flags, timeline, lastSeenDate"""
        result = get_clinic_benchmark("A")
        assert "clinicDistribution" in result
        assert "networkAverage" in result
        # Only response trend keys
        assert set(result["clinicDistribution"].keys()) == {"improving", "plateau", "worse"}
        assert set(result["networkAverage"].keys()) == {"improving", "plateau", "worse"}
        # No Level 3 fields
        assert "redFlags" not in result
        assert "timeline" not in result
        assert "lastSeenDate" not in result
    
    def test_anonymization_no_clinic_names_in_network_average(self):
        """Network average output must not contain clinic names"""
        result = get_clinic_benchmark("A")
        import json
        result_str = json.dumps(result)
        # Clinic names from seed
        assert "Clinic A" not in result_str
        assert "Clinic B" not in result_str
        assert "Clinic C" not in result_str
    
    def test_clinic_distribution_sums_to_one_or_zero(self):
        """Clinic distribution values are proportions"""
        dist = get_clinic_response_trend_distribution("A")
        total = sum(dist.values())
        assert total <= 1.01  # Allow float rounding
        assert total >= 0
    
    def test_network_average_sums_to_one_or_zero(self):
        """Network average values are proportions"""
        dist = get_network_average_response_trend_distribution()
        total = sum(dist.values())
        assert total <= 1.01
        assert total >= 0

    def test_benchmarking_zero_participants_returns_zeros_or_ineligible(self):
        """When no clinics are participating (all opted out or level 0), return eligible=false, zeros."""
        seed_data()
        # All opted out -> not_opted_in, network zeros
        clinics["A"].optedIn = False
        clinics["B"].optedIn = False
        clinics["C"].optedIn = False
        result = get_clinic_benchmark("A")
        assert result["eligible"] is False
        assert result["reason"] == "not_opted_in"
        assert result["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
        # A opted in but level 0 (contributionPct < 10) -> locked_level_0, network zeros
        clinics["A"].optedIn = True
        clinics["A"].contributionPct = 5  # Level 0
        result2 = get_clinic_benchmark("A")
        assert result2["eligible"] is False
        assert result2["reason"] == "locked_level_0"
        assert result2["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
        # A opted in, level > 0, but A is the only participant -> no_participants
        clinics["A"].optedIn = True
        clinics["A"].contributionPct = 85
        clinics["B"].optedIn = False
        clinics["C"].optedIn = False
        result3 = get_clinic_benchmark("A")
        assert result3["eligible"] is False
        assert result3["reason"] == "no_participants"
        assert result3["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}

    def test_benchmarking_excludes_opted_out_clinics(self):
        """Network average must only include opted-in clinics with level > 0."""
        seed_data()
        # B is opted out. Add episode for B with responseTrend
        fp = compute_fingerprint("Unique Patient", "2000-01-01", "9999")
        episodes.append(
            Episode(
                episodeId="ep_b_only",
                clinicId="B",
                fingerprint=fp,
                startDate="2023-01-01",
                endDate="2023-06-30",
                conditions=["X"],
                interventions=["Y"],
                responseTrend="worse",
                redFlags=[],
                timeline=[],
            )
        )
        # B's "worse" must NOT be in network average (B is opted out)
        # Network = A (2 improving) + C (1 plateau) only
        result = get_clinic_benchmark("A")
        assert result["eligible"] is True
        navg = result["networkAverage"]
        # A + C: 2 improving, 1 plateau -> improving 2/3, plateau 1/3
        assert navg["improving"] + navg["plateau"] + navg["worse"] <= 1.01
        assert navg["worse"] < 0.5  # B's worse is excluded, so worse should be low/zero
        # Opt out A and C - network must be all zeros
        clinics["A"].optedIn = False
        clinics["C"].optedIn = False
        result_empty = get_clinic_benchmark("A")
        assert result_empty["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
        episodes[:] = [ep for ep in episodes if ep.episodeId != "ep_b_only"]

    def test_benchmarking_excludes_level_0_clinics_from_network_average(self):
        """Only clinics with level >= 1 count in network average. Level 0 clinics excluded."""
        seed_data()
        # A level 3, C level 1. Set B to opted in but level 0 (contributionPct=5)
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 5  # Level 0
        fp = compute_fingerprint("Unique Patient", "2000-01-01", "9999")
        episodes.append(
            Episode(
                episodeId="ep_b_only",
                clinicId="B",
                fingerprint=fp,
                startDate="2023-01-01",
                endDate="2023-06-30",
                conditions=["X"],
                interventions=["Y"],
                responseTrend="worse",
                redFlags=[],
                timeline=[],
            )
        )
        # B has "worse" but level 0 -> must NOT be in network average
        # Network = A + C only (both level >= 1)
        result = get_clinic_benchmark("A")
        assert result["eligible"] is True
        navg = result["networkAverage"]
        assert navg["worse"] < 0.5  # B's worse excluded
        episodes[:] = [ep for ep in episodes if ep.episodeId != "ep_b_only"]

    def test_benchmarking_locked_for_level_0_requester(self):
        """Requester with level 0 gets eligible=false, reason=locked_level_0, zero distributions."""
        seed_data()
        clinics["A"].optedIn = True
        clinics["A"].contributionPct = 5  # Level 0
        result = get_clinic_benchmark("A")
        assert result["eligible"] is False
        assert result["reason"] == "locked_level_0"
        assert result["clinicDistribution"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
        assert result["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}

    def test_benchmarking_no_participants_returns_ineligible(self):
        """When 0 other participating clinics (level >= 1), return eligible=false, reason=no_participants."""
        seed_data()
        clinics["A"].optedIn = True
        clinics["A"].contributionPct = 85
        clinics["B"].optedIn = False
        clinics["C"].optedIn = False
        result = get_clinic_benchmark("A")
        assert result["eligible"] is False
        assert result["reason"] == "no_participants"
        assert result["participating_count"] == 0
        assert result["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}

    def test_benchmarking_all_opted_in_contribution_zero_returns_no_network_average(self):
        """When all clinics opted_in but contribution_pct=0 (Level 0), no 67/33 — return zeros."""
        seed_data()
        clinics["A"].optedIn = True
        clinics["A"].contributionPct = 0
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 0
        clinics["C"].optedIn = True
        clinics["C"].contributionPct = 0
        result = get_clinic_benchmark("A")
        assert result["eligible"] is False
        assert result["reason"] == "locked_level_0"
        assert result["networkAverage"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}
        assert result["clinicDistribution"] == {"improving": 0.0, "plateau": 0.0, "worse": 0.0}


# =============================================================================
# API: Continue Care & Credits Dashboard
# =============================================================================
class TestContinueCareAPI:
    """Tests for POST /intake/continue-care and GET /credits/dashboard"""
    
    def test_continue_care_awards_credits(self):
        """Continue care awards credits to contributing clinics with visible_level > 0"""
        # First, get B to Level 2 so it can see history from A and C
        client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 45})
        
        # Check intake (match found, A and C contribute)
        check_resp = client.post(
            "/intake/check",
            json={"clinicId": "B", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "1234"},
        )
        assert check_resp.status_code == 200
        assert check_resp.json()["matchFound"] is True
        assert check_resp.json()["contributionGating"]["contributingClinicsCount"] == 2
        
        # Continue care
        cont_resp = client.post(
            "/intake/continue-care",
            json={"clinicId": "B", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "1234"},
        )
        assert cont_resp.status_code == 200
        data = cont_resp.json()
        assert data["status"] == "recorded"
        assert data["credited"] is True
        assert data["creditsAwarded"] == 2  # A and C
        assert len(data["events"]) == 2
        
        # Dashboard shows credits
        dash_resp = client.get("/credits/dashboard")
        assert dash_resp.status_code == 200
        credits = dash_resp.json()["clinicCredits"]
        assert credits.get("A", 0) == 1
        assert credits.get("C", 0) == 1
        
        # Reset
        client.post("/clinics/B/settings", json={"optedIn": False, "contributionPct": 0})

    def test_continue_care_is_idempotent_for_same_patient_and_clinic_pair(self):
        """Same payload twice: credits increase only once, event log grows only once."""
        client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 45})
        payload = {"clinicId": "B", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "1234"}

        # First call
        r1 = client.post("/intake/continue-care", json=payload)
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["status"] == "recorded"
        assert d1["credited"] is True
        assert d1["creditsAwarded"] == 2  # A and C

        dash1 = client.get("/credits/dashboard")
        credits1 = dash1.json()["clinicCredits"]
        events1 = dash1.json()["recentEvents"]
        assert credits1.get("A", 0) == 1
        assert credits1.get("C", 0) == 1
        assert len(events1) == 2

        # Second call - same payload, must be idempotent
        r2 = client.post("/intake/continue-care", json=payload)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["status"] == "already_recorded"
        assert d2["credited"] is False
        assert d2["creditsAwarded"] == 0
        assert len(d2["events"]) == 0

        dash2 = client.get("/credits/dashboard")
        credits2 = dash2.json()["clinicCredits"]
        events2 = dash2.json()["recentEvents"]
        assert credits2.get("A", 0) == 1  # unchanged
        assert credits2.get("C", 0) == 1  # unchanged
        assert len(events2) == 2  # no new events

        client.post("/clinics/B/settings", json={"optedIn": False, "contributionPct": 0})

    def test_continue_care_validates_phone_last4(self):
        """Continue care rejects invalid phoneLast4 (must be exactly 4 digits)."""
        resp = client.post(
            "/intake/continue-care",
            json={"clinicId": "B", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "123"},
        )
        assert resp.status_code == 400
        assert "phoneLast4" in resp.json().get("detail", "")
    
    def test_clinics_endpoint_includes_network_status(self):
        """GET /clinics returns networkStatus for each clinic"""
        resp = client.get("/clinics")
        assert resp.status_code == 200
        for clinic in resp.json():
            assert "networkStatus" in clinic
            assert clinic["networkStatus"] in ["Isolated", "Basic", "Collaborative", "Trusted Contributor"]
