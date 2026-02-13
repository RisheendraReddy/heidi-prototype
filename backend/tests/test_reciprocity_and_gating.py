"""
Tests for per-contributor detail gating by context level.
Old pct-based reciprocity matching was removed.
"""
import pytest
from models import Clinic, Episode, clinics, episodes, compute_fingerprint
from logic import (
    get_worst_response_trend,
    check_patient_match
)
from seed import seed_data


@pytest.fixture(autouse=True)
def reset_seed_data():
    """Reset seed data before each test"""
    seed_data()
    yield
    # Cleanup if needed


class TestContributorDetailCapping:
    """Per-contributor visibleLevel = min(requesterLevel, contributorLevel)."""

    def test_patient_1_seed_assumptions(self):
        """Patient 1 has episodes in Clinic A (Level 3) and Clinic C (Level 1)."""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        eps = [ep for ep in episodes if ep.fingerprint == fp]
        assert len(eps) == 2
        assert {ep.clinicId for ep in eps} == {"A", "C"}
        assert clinics["A"].get_context_level() == 3
        assert clinics["C"].get_context_level() == 1

    def test_medium_requester_level2_gets_both_but_c_capped_to_level1(self):
        """
        Medium (45%, Level 2) should receive from both A and C,
        but C’s data is Level 1-only (no interventions from C).
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")

        # Use Clinic B as requester to include both A and C as contributors
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 45  # Level 2

        result = check_patient_match(fp, "B")
        assert result["matchFound"] is True
        assert result["requestingClinic"]["contextLevel"] == 2
        assert result["contributionGating"]["contributingClinicsCount"] == 2
        assert result["contributionGating"]["detailCappedClinicsCount"] == 1  # C is capped (Level 1 < 2)

        summary = result["sharedSummary"]
        assert summary is not None

        # Level 2 requester should see interventions/responseTrend (from A)
        assert "interventions" in summary
        assert "responseTrend" in summary

        # Not Level 3 for requester
        assert "redFlags" not in summary
        assert "timeline" not in summary
        assert "lastSeenDate" not in summary

        # Reset Clinic B to seeded state
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0

    def test_high_requester_level3_gets_full_from_a_partial_from_c(self):
        """
        High (90%, Level 3) should receive full from A and partial from C (Level 1).
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")

        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3

        result = check_patient_match(fp, "B")
        assert result["matchFound"] is True
        assert result["requestingClinic"]["contextLevel"] == 3
        assert result["contributionGating"]["contributingClinicsCount"] == 2
        assert result["contributionGating"]["detailCappedClinicsCount"] == 1  # C capped

        summary = result["sharedSummary"]
        assert summary is not None

        # Level 3 requester sees redFlags/timeline/lastSeenDate, but only from Level>=3 contributors (A)
        assert "redFlags" in summary
        assert "timeline" in summary
        assert "lastSeenDate" in summary

        # Reset Clinic B to seeded state
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


class TestFieldGatingByContextLevel:
    """Test that sharedSummary fields are gated correctly by context level"""
    
    def test_level_0_shared_summary_is_null(self):
        """Level 0: sharedSummary must be null always"""
        fingerprint = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # Create a Level 0 clinic (opted out)
        test_clinic_id = "TEST_L0"
        test_clinic = Clinic(clinicId=test_clinic_id, name="Test L0", optedIn=False, contributionPct=0)
        clinics[test_clinic_id] = test_clinic
        
        result = check_patient_match(fingerprint, test_clinic_id)
        
        assert result["requestingClinic"]["contextLevel"] == 0
        assert result["matchFound"] is True  # raw episodes exist
        assert result["sharedSummary"] is None
        
        # Cleanup
        del clinics[test_clinic_id]
    
    def test_level_1_fields_only(self):
        """Level 1: sharedSummary contains only conditions, dateRanges, contributingClinicsCount"""
        fingerprint = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # Create a Level 1 clinic (30%)
        test_clinic_id = "TEST_L1"
        test_clinic = Clinic(clinicId=test_clinic_id, name="Test L1", optedIn=True, contributionPct=30)
        clinics[test_clinic_id] = test_clinic
        
        result = check_patient_match(fingerprint, test_clinic_id)
        
        assert result["requestingClinic"]["contextLevel"] == 1
        assert result["sharedSummary"] is not None
        
        summary = result["sharedSummary"]
        assert "conditions" in summary
        assert "dateRanges" in summary
        # contributingClinicsCount is now part of gating object, not sharedSummary
        assert "contributingClinicsCount" not in summary
        
        # Level 2 fields should NOT be present
        assert "interventions" not in summary
        assert "responseTrend" not in summary
        
        # Level 3 fields should NOT be present
        assert "redFlags" not in summary
        assert "timeline" not in summary
        assert "lastSeenDate" not in summary
        
        # Cleanup
        del clinics[test_clinic_id]
    
    def test_level_2_fields(self):
        """Level 2: adds interventions and responseTrend"""
        fingerprint = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # Create a Level 2 clinic (45%)
        test_clinic_id = "TEST_L2"
        test_clinic = Clinic(clinicId=test_clinic_id, name="Test L2", optedIn=True, contributionPct=45)
        clinics[test_clinic_id] = test_clinic
        
        result = check_patient_match(fingerprint, test_clinic_id)
        
        assert result["requestingClinic"]["contextLevel"] == 2
        assert result["sharedSummary"] is not None
        
        summary = result["sharedSummary"]
        # Level 1 fields
        assert "conditions" in summary
        assert "dateRanges" in summary
        assert "contributingClinicsCount" not in summary
        
        # Level 2 fields
        assert "interventions" in summary
        assert "responseTrend" in summary
        
        # Level 3 fields should NOT be present
        assert "redFlags" not in summary
        assert "timeline" not in summary
        assert "lastSeenDate" not in summary
        
        # Cleanup
        del clinics[test_clinic_id]
    
    def test_level_3_fields(self):
        """Level 3: adds redFlags, timeline, lastSeenDate"""
        # Use Clinic B as requester and set to Level 3 to include both contributors
        fingerprint = compute_fingerprint("John Doe", "1990-01-15", "1234")

        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3

        result = check_patient_match(fingerprint, "B")
        assert result["requestingClinic"]["contextLevel"] == 3
        assert result["sharedSummary"] is not None

        summary = result["sharedSummary"]
        assert "conditions" in summary
        assert "dateRanges" in summary
        assert "interventions" in summary
        assert "responseTrend" in summary
        assert "redFlags" in summary
        assert "timeline" in summary
        assert "lastSeenDate" in summary

        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_response_trend_ordering(self):
        """responseTrend aggregation must be worse > plateau > improving"""
        assert get_worst_response_trend(["improving"]) == "improving"
        assert get_worst_response_trend(["plateau"]) == "plateau"
        assert get_worst_response_trend(["worse"]) == "worse"
        
        assert get_worst_response_trend(["improving", "plateau"]) == "plateau"
        assert get_worst_response_trend(["plateau", "worse"]) == "worse"
        assert get_worst_response_trend(["improving", "worse"]) == "worse"
        assert get_worst_response_trend(["improving", "plateau", "worse"]) == "worse"
    
    def test_timeline_capped_at_5_items(self):
        """timeline length must be capped at 5 items"""
        # Create episodes with many timeline items
        fingerprint = compute_fingerprint("Test Patient", "2000-01-01", "9999")

        # Use Clinic B as requester at Level 3 so it can see Clinic A at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90

        # Create episode with 10 timeline items in Clinic A (Level 3)
        episode = Episode(
            episodeId="ep_timeline",
            clinicId="A",
            fingerprint=fingerprint,
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Test"],
            interventions=["Test"],
            responseTrend="improving",
            redFlags=[],
            timeline=[f"Item {i}" for i in range(10)]  # 10 items
        )
        episodes.append(episode)

        result = check_patient_match(fingerprint, "B")
        
        assert result["sharedSummary"] is not None
        timeline = result["sharedSummary"]["timeline"]
        assert len(timeline) <= 5
        
        # Cleanup
        episodes.remove(episode)
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
