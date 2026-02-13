"""
Comprehensive tests for cross-clinic patient history sharing prototype.

Covers: network status, reciprocity/capping, opt-in filtering, aggregation gates,
continuity credits, benchmarking safety.
"""
import json
import pytest
from models import Clinic, Episode, clinics, episodes, compute_fingerprint
from logic import get_network_status, check_patient_match
from credits import award_continuity_credits, get_clinic_credits, reset_credits
from benchmarking import get_clinic_benchmark, get_network_average_response_trend_distribution

from tests.conftest import (
    client,
    minimal_dataset,
    seeded_data,
    assert_summary_gate_level,
)


# Preset-to-settings mapping (matches frontend ClinicConsole PRESET_SETTINGS)
PRESET_SETTINGS = {
    "level0": {"optedIn": False, "contributionPct": 0},
    "level1": {"optedIn": True, "contributionPct": 20},
    "level2": {"optedIn": True, "contributionPct": 60},
    "level3": {"optedIn": True, "contributionPct": 85},
}
PRESET_EXPECTED = {
    "level0": {"contextLevel": 0, "networkStatus": "Isolated"},
    "level1": {"contextLevel": 1, "networkStatus": "Basic"},
    "level2": {"contextLevel": 2, "networkStatus": "Collaborative"},
    "level3": {"contextLevel": 3, "networkStatus": "Trusted Contributor"},
}


# =============================================================================
# Clinic Settings Presets (Level-based)
# =============================================================================
class TestClinicPresets:
    """Preset selection must result in correct computed level and network_status."""

    def test_preset_level0_result(self, client):
        """Level 0 preset: optedIn=false, contributionPct=0 → Isolated."""
        resp = client.post(
            "/clinics/B/settings",
            json=PRESET_SETTINGS["level0"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contextLevel"] == PRESET_EXPECTED["level0"]["contextLevel"]
        assert data["networkStatus"] == PRESET_EXPECTED["level0"]["networkStatus"]
        assert data["optedIn"] is False
        assert data["contributionPct"] == 0

    def test_preset_level1_result(self, client):
        """Level 1 preset: optedIn=true, contributionPct=20 → Basic."""
        resp = client.post(
            "/clinics/B/settings",
            json=PRESET_SETTINGS["level1"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contextLevel"] == PRESET_EXPECTED["level1"]["contextLevel"]
        assert data["networkStatus"] == PRESET_EXPECTED["level1"]["networkStatus"]
        assert data["optedIn"] is True
        assert data["contributionPct"] == 20

    def test_preset_level2_result(self, client):
        """Level 2 preset: optedIn=true, contributionPct=60 → Collaborative."""
        resp = client.post(
            "/clinics/B/settings",
            json=PRESET_SETTINGS["level2"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contextLevel"] == PRESET_EXPECTED["level2"]["contextLevel"]
        assert data["networkStatus"] == PRESET_EXPECTED["level2"]["networkStatus"]
        assert data["optedIn"] is True
        assert data["contributionPct"] == 60

    def test_preset_level3_result(self, client):
        """Level 3 preset: optedIn=true, contributionPct=85 → Trusted Contributor."""
        resp = client.post(
            "/clinics/B/settings",
            json=PRESET_SETTINGS["level3"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contextLevel"] == PRESET_EXPECTED["level3"]["contextLevel"]
        assert data["networkStatus"] == PRESET_EXPECTED["level3"]["networkStatus"]
        assert data["optedIn"] is True
        assert data["contributionPct"] == 85

    def test_all_presets_produce_correct_network_status(self, client):
        """Each preset produces the expected network_status."""
        for preset_name, settings in PRESET_SETTINGS.items():
            resp = client.post(
                "/clinics/B/settings",
                json=settings,
            )
            assert resp.status_code == 200
            data = resp.json()
            expected = PRESET_EXPECTED[preset_name]
            assert data["contextLevel"] == expected["contextLevel"]
            assert data["networkStatus"] == expected["networkStatus"]


# =============================================================================
# A) Network Status
# =============================================================================
class TestNetworkStatus:
    """Network status mapping: 0=Isolated, 1=Basic, 2=Collaborative, 3=Trusted Contributor"""

    def test_network_status_level_0_is_isolated(self):
        assert get_network_status(0) == "Isolated"

    def test_network_status_level_1_is_basic(self):
        assert get_network_status(1) == "Basic"

    def test_network_status_level_2_is_collaborative(self):
        assert get_network_status(2) == "Collaborative"

    def test_network_status_level_3_is_trusted_contributor(self):
        assert get_network_status(3) == "Trusted Contributor"


# =============================================================================
# B) Reciprocity + Capping (regression)
# =============================================================================
class TestReciprocityAndCapping:
    """visible_level = min(requester, contributor); is_capped = contributor < requester"""

    @pytest.fixture(autouse=True)
    def _seed(self, seeded_data):
        pass

    def test_visible_level_is_min_of_requester_and_contributor(self):
        from seed import seed_data

        seed_data()
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")

        # requester=3 contributor=1 -> visible=1
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3
        result = check_patient_match(fp, "B")
        c_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "C")
        assert c_detail["contributorLevel"] == 1
        assert c_detail["visibleLevel"] == 1  # min(3,1)=1

        # requester=1 contributor=3 -> visible=1
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 25  # Level 1
        result = check_patient_match(fp, "B")
        a_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A")
        assert a_detail["contributorLevel"] == 3
        assert a_detail["visibleLevel"] == 1  # min(1,3)=1

        # requester=2 contributor=2 -> visible=2
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 45  # Level 2
        result = check_patient_match(fp, "B")
        a_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A")
        c_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "C")
        assert a_detail["visibleLevel"] == 2  # min(2,3)=2
        assert c_detail["visibleLevel"] == 1  # min(2,1)=1

        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0

    def test_capping_true_when_contributor_lower_than_requester(self):
        from seed import seed_data

        seed_data()
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3
        result = check_patient_match(fp, "B")
        c_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "C")
        assert c_detail["contributorLevel"] == 1
        assert c_detail["visibleLevel"] == 1
        assert c_detail["isCapped"] is True  # 1 < 3
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0

    def test_capping_false_when_contributor_greater_or_equal(self):
        from seed import seed_data

        seed_data()
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 45  # Level 2
        result = check_patient_match(fp, "B")
        a_detail = next(c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A")
        assert a_detail["contributorLevel"] == 3
        assert a_detail["visibleLevel"] == 2
        assert a_detail["isCapped"] is False  # 3 >= 2
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# C) Opt-in Filtering
# =============================================================================
class TestOptInFiltering:
    """Level 0 contributors excluded; no prior context when no opted-in contributors"""

    def test_level_0_contributors_never_returned(self, minimal_dataset):
        """Contributor level 0 has an episode; should not appear in contributors."""
        fp = minimal_dataset
        result = check_patient_match(fp, "A")  # A is requester, level 3
        contributor_ids = {c["clinicId"] for c in result["contributionGating"]["contributingClinics"]}
        assert "C" not in contributor_ids  # C is level 0 (opted out)
        assert "A" not in contributor_ids  # A is requester
        assert "B" in contributor_ids  # B is level 1, opted in

    def test_no_prior_context_message_when_no_opted_in_contributors(self, client):
        """When all contributors opted out or no episodes -> matchFound False or contributors empty."""
        from seed import seed_data

        seed_data()
        reset_credits()
        # Opt out A and C - only B has no episodes for this patient
        clinics["A"].optedIn = False
        clinics["C"].optedIn = False
        # Patient 2 (Jane) has episode only in A - so with A opted out, no contributors
        resp = client.post(
            "/intake/check",
            json={"clinicId": "B", "fullName": "Jane Smith", "dob": "1985-03-22", "phoneLast4": "5678"},
        )
        data = resp.json()
        assert data["matchFound"] is True  # raw episodes exist
        assert data["contributionGating"]["contributingClinicsCount"] == 0
        assert data["sharedSummary"] is None
        clinics["A"].optedIn = True
        clinics["C"].optedIn = True


# =============================================================================
# D) Aggregation Gates / No Leakage
# =============================================================================
class TestAggregationGates:
    """Helper asserts presence/absence of keys per visible_level."""

    def test_gate_level_1_only_returns_level_1_fields(self, minimal_dataset):
        """Level 1: conditions, dateRanges only. Not: interventions, response_trend, red_flags, timeline, last_seen_date."""
        fp = minimal_dataset
        # Requester A at level 3, but we need requester at level 1
        test_id = "TEST_L1"
        clinics[test_id] = Clinic(clinicId=test_id, name="Test L1", optedIn=True, contributionPct=30)
        try:
            result = check_patient_match(fp, test_id)
            assert_summary_gate_level(result["sharedSummary"], 1)
            summary = result["sharedSummary"]
            assert "conditions" in summary
            assert "dateRanges" in summary
            assert "interventions" not in summary
            assert "responseTrend" not in summary
            assert "redFlags" not in summary
            assert "timeline" not in summary
            assert "lastSeenDate" not in summary
        finally:
            del clinics[test_id]

    def test_gate_level_2_only_returns_level_1_and_2_fields(self, minimal_dataset):
        """Level 2: includes interventions, responseTrend. Not: redFlags, timeline, lastSeenDate."""
        fp = minimal_dataset
        test_id = "TEST_L2"
        clinics[test_id] = Clinic(clinicId=test_id, name="Test L2", optedIn=True, contributionPct=45)
        try:
            result = check_patient_match(fp, test_id)
            assert_summary_gate_level(result["sharedSummary"], 2)
            summary = result["sharedSummary"]
            assert "interventions" in summary
            assert "responseTrend" in summary
            assert "redFlags" not in summary
            assert "timeline" not in summary
            assert "lastSeenDate" not in summary
        finally:
            del clinics[test_id]

    def test_gate_level_3_returns_all_fields(self, minimal_dataset):
        """Level 3: all fields including redFlags, timeline, lastSeenDate."""
        fp = minimal_dataset
        result = check_patient_match(fp, "A")  # A is level 3
        assert_summary_gate_level(result["sharedSummary"], 3)
        summary = result["sharedSummary"]
        assert "conditions" in summary
        assert "dateRanges" in summary
        assert "interventions" in summary
        assert "responseTrend" in summary
        assert "redFlags" in summary
        assert "timeline" in summary
        assert "lastSeenDate" in summary

    def test_gate_level_0_returns_null_or_empty_summary(self, minimal_dataset):
        """Level 0: sharedSummary must be null."""
        fp = minimal_dataset
        test_id = "TEST_L0"
        clinics[test_id] = Clinic(clinicId=test_id, name="Test L0", optedIn=False, contributionPct=0)
        try:
            result = check_patient_match(fp, test_id)
            assert result["requestingClinic"]["contextLevel"] == 0
            assert result["sharedSummary"] is None
        finally:
            del clinics[test_id]


# =============================================================================
# E) Continuity Credits
# =============================================================================
class TestContinuityCredits:
    """Credits awarded to visible contributors; event log structure."""

    def test_continue_care_awards_credits_to_all_visible_contributors(self, client):
        """Setup: A,B visible_level>0, C visible_level=0. Action: continue-care. Expect: A+1, B+1, C unchanged."""
        from seed import seed_data

        seed_data()
        reset_credits()
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        episodes.append(
            Episode(
                episodeId="ep_john_b",
                clinicId="B",
                fingerprint=fp,
                startDate="2023-01-01",
                endDate="2023-06-30",
                conditions=["C1"],
                interventions=["I1"],
                responseTrend="improving",
                redFlags=[],
                timeline=[],
            )
        )
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 30  # Level 1
        clinics["C"].optedIn = True
        clinics["C"].contributionPct = 5  # Level 0 (opted in but <10%)
        clinics["D"] = Clinic(clinicId="D", name="Clinic D", optedIn=True, contributionPct=90)
        resp = client.post(
            "/intake/continue-care",
            json={"clinicId": "D", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "1234"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["creditsAwarded"] == 2  # A and B (C has visible_level=0)
        assert get_clinic_credits("A") == 1
        assert get_clinic_credits("B") == 1
        assert get_clinic_credits("C") == 0
        clinics.pop("D", None)
        episodes[:] = [ep for ep in episodes if ep.episodeId != "ep_john_b"]
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
        clinics["C"].optedIn = True
        clinics["C"].contributionPct = 30
        reset_credits()

    def test_continue_care_does_not_award_for_opted_out_contributors(self):
        """Contributor level 0 should never receive credit."""
        reset_credits()
        events, _ = award_continuity_credits(
            fingerprint="p1|1990-01-15|1234",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 3), ("C", 0)],  # C visible=0
        )
        assert len(events) == 1  # Only A
        assert get_clinic_credits("A") == 1
        assert get_clinic_credits("C") == 0

    def test_credit_event_log_created_with_required_fields(self):
        """Event includes patient_id, from_clinic_id, to_clinic_id, timestamp."""
        reset_credits()
        events, _ = award_continuity_credits(
            fingerprint="p1|1990-01-15|1234",
            to_clinic_id="B",
            contributing_clinics_with_visible_level=[("A", 1)],
        )
        assert len(events) == 1
        e = events[0]
        assert "patientId" in e
        assert "fromClinic" in e
        assert "toClinic" in e
        assert "timestamp" in e
        assert e["patientId"] == "p1|1990-01-15|1234"
        assert e["fromClinic"] == "A"
        assert e["toClinic"] == "B"
        assert e["timestamp"]  # non-empty


# =============================================================================
# F) Benchmarking Safety + Anonymization
# =============================================================================
class TestBenchmarkingSafety:
    """Benchmarking uses only safe fields; no clinic identifiers; excludes level 0."""

    @pytest.fixture(autouse=True)
    def _seed(self, seeded_data):
        pass

    def test_benchmarking_uses_only_safe_fields(self):
        """Response contains only counts/percentages for response_trend. NOT: raw_notes, red_flags, timeline, last_seen_date."""
        result = get_clinic_benchmark("A")
        assert "clinicDistribution" in result
        assert "networkAverage" in result
        for section in [result["clinicDistribution"], result["networkAverage"]]:
            assert set(section.keys()) == {"improving", "plateau", "worse"}
        forbidden = ["raw_notes", "red_flags", "redFlags", "timeline", "last_seen_date", "lastSeenDate"]
        result_str = json.dumps(result)
        for f in forbidden:
            assert f not in result_str, f"Benchmark must not contain {f}"

    def test_benchmarking_network_average_has_no_clinic_identifiers(self):
        """Network average section must not include clinic_id/clinic_name lists."""
        result = get_clinic_benchmark("A")
        result_str = json.dumps(result)
        assert "Clinic A" not in result_str
        assert "Clinic B" not in result_str
        assert "Clinic C" not in result_str
        # networkAverage must not contain per-clinic breakdown
        assert "networkAverage" in result
        navg = result["networkAverage"]
        assert set(navg.keys()) == {"improving", "plateau", "worse"}

    def test_benchmarking_excludes_level_0_clinics_from_network_average(self):
        """Episodes from opted-out clinics must not be counted."""
        from seed import seed_data

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
        # Network average aggregates only opted-in clinics (A, C). B is opted out.
        dist_before = get_network_average_response_trend_distribution()
        # B's episode has "worse" - if B were included, worse would be higher
        # With only A and C: A has improving, plateau, worse; C has plateau. So trend mix doesn't include B's "worse" prominently.
        # Simpler: opt out A and C, then network has no opted-in clinics -> empty
        clinics["A"].optedIn = False
        clinics["C"].optedIn = False
        dist_empty = get_network_average_response_trend_distribution()
        assert dist_empty["improving"] == 0.0
        assert dist_empty["plateau"] == 0.0
        assert dist_empty["worse"] == 0.0
        clinics["A"].optedIn = True
        clinics["C"].optedIn = True
        episodes[:] = [ep for ep in episodes if ep.episodeId != "ep_b_only"]
