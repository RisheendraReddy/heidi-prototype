"""
Comprehensive tests for logic.py - Business logic validation

Tests are organized to:
1. Generate tests for all functions
2. Point out failures with clear explanations
3. Highlight incorrect conditions (e.g., visibleLevel, aggregation gates, contributor filtering)
"""
import pytest
from models import Clinic, Episode, clinics, episodes, compute_fingerprint
from logic import (
    get_clinic,
    update_clinic_settings,
    get_raw_episodes_from_other_clinics,
    get_locked_preview,
    get_level_for_contribution,
    get_what_if_unlocks,
    get_worst_response_trend,
    contributor_summary_for_visible_level,
    aggregate_shared_summary_from_contributors,
    check_patient_match,
)
from seed import seed_data


@pytest.fixture(autouse=True)
def reset_seed_data():
    """Reset seed data before each test"""
    seed_data()
    yield
    # Cleanup after test


# =============================================================================
# TEST: get_clinic()
# =============================================================================
class TestGetClinic:
    """Tests for get_clinic function"""
    
    def test_get_existing_clinic(self):
        """Should return clinic when it exists"""
        clinic = get_clinic("A")
        assert clinic is not None
        assert clinic.clinicId == "A"
        assert clinic.name == "Clinic A"
    
    def test_get_nonexistent_clinic(self):
        """Should return None for non-existent clinic"""
        clinic = get_clinic("NONEXISTENT")
        assert clinic is None
    
    def test_get_all_seeded_clinics(self):
        """Should return all seeded clinics"""
        for clinic_id in ["A", "B", "C"]:
            clinic = get_clinic(clinic_id)
            assert clinic is not None
            assert clinic.clinicId == clinic_id


# =============================================================================
# TEST: update_clinic_settings()
# =============================================================================
class TestUpdateClinicSettings:
    """Tests for update_clinic_settings function"""
    
    def test_update_opted_in(self):
        """Should update optedIn status"""
        clinic = update_clinic_settings("A", opted_in=False, contribution_pct=50)
        assert clinic is not None
        assert clinic.optedIn is False
        assert clinic.contributionPct == 0  # Opt-out forces contribution to 0

        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=50)
        assert clinic.optedIn is True

    def test_opt_out_forces_contribution_zero(self):
        """When opted_in is False, contribution_pct must always be stored as 0."""
        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=85)
        assert clinic.contributionPct == 85

        clinic = update_clinic_settings("A", opted_in=False, contribution_pct=50)
        assert clinic.optedIn is False
        assert clinic.contributionPct == 0

        clinic = update_clinic_settings("A", opted_in=False, contribution_pct=99)
        assert clinic.contributionPct == 0

    def test_re_enabling_opt_in_allows_nonzero_contribution(self):
        """Re-enabling opt-in must allow non-zero contribution to be stored."""
        update_clinic_settings("A", opted_in=False, contribution_pct=50)
        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=60)
        assert clinic.optedIn is True
        assert clinic.contributionPct == 60
    
    def test_update_contribution_pct(self):
        """Should update contributionPct"""
        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=75)
        assert clinic is not None
        assert clinic.contributionPct == 75
    
    def test_clamp_contribution_pct_min(self):
        """Should clamp contributionPct to minimum 0"""
        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=-10)
        assert clinic.contributionPct == 0
    
    def test_clamp_contribution_pct_max(self):
        """Should clamp contributionPct to maximum 100"""
        clinic = update_clinic_settings("A", opted_in=True, contribution_pct=150)
        assert clinic.contributionPct == 100
    
    def test_update_nonexistent_clinic(self):
        """Should return None for non-existent clinic"""
        result = update_clinic_settings("NONEXISTENT", opted_in=True, contribution_pct=50)
        assert result is None


# =============================================================================
# TEST: get_raw_episodes_from_other_clinics()
# =============================================================================
class TestGetRawEpisodesFromOtherClinics:
    """Tests for get_raw_episodes_from_other_clinics function"""
    
    def test_excludes_requesting_clinic(self):
        """Should exclude episodes from the requesting clinic"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # John Doe has episodes in A and C
        episodes_for_a = get_raw_episodes_from_other_clinics(fp, "A")
        clinic_ids = {ep.clinicId for ep in episodes_for_a}
        
        assert "A" not in clinic_ids
        assert "C" in clinic_ids
    
    def test_returns_all_other_clinics(self):
        """Should return episodes from ALL other clinics (not just opted-in)"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # Request from B (no episodes), should get A and C
        episodes_for_b = get_raw_episodes_from_other_clinics(fp, "B")
        clinic_ids = {ep.clinicId for ep in episodes_for_b}
        
        # Should include both A and C regardless of opt-in status
        assert "A" in clinic_ids
        assert "C" in clinic_ids
    
    def test_no_match_returns_empty(self):
        """Should return empty list when no matches found"""
        fp = compute_fingerprint("Unknown Person", "2000-01-01", "0000")
        episodes_list = get_raw_episodes_from_other_clinics(fp, "A")
        assert len(episodes_list) == 0


# =============================================================================
# TEST: get_level_for_contribution()
# =============================================================================
class TestGetLevelForContribution:
    """Tests for get_level_for_contribution function - CRITICAL LEVEL THRESHOLDS"""
    
    def test_not_opted_in_always_level_0(self):
        """Not opted in should always return Level 0 regardless of pct"""
        assert get_level_for_contribution(opted_in=False, contribution_pct=0) == 0
        assert get_level_for_contribution(opted_in=False, contribution_pct=50) == 0
        assert get_level_for_contribution(opted_in=False, contribution_pct=100) == 0
    
    def test_level_0_boundary(self):
        """Level 0: opted_in but contributionPct < 10"""
        assert get_level_for_contribution(opted_in=True, contribution_pct=0) == 0
        assert get_level_for_contribution(opted_in=True, contribution_pct=9) == 0
    
    def test_level_1_boundary(self):
        """Level 1: 10 <= contributionPct < 40"""
        assert get_level_for_contribution(opted_in=True, contribution_pct=10) == 1  # Exact boundary
        assert get_level_for_contribution(opted_in=True, contribution_pct=39) == 1  # Upper boundary
        assert get_level_for_contribution(opted_in=True, contribution_pct=25) == 1  # Middle
    
    def test_level_2_boundary(self):
        """Level 2: 40 <= contributionPct < 80"""
        assert get_level_for_contribution(opted_in=True, contribution_pct=40) == 2  # Exact boundary
        assert get_level_for_contribution(opted_in=True, contribution_pct=79) == 2  # Upper boundary
        assert get_level_for_contribution(opted_in=True, contribution_pct=60) == 2  # Middle
    
    def test_level_3_boundary(self):
        """Level 3: contributionPct >= 80"""
        assert get_level_for_contribution(opted_in=True, contribution_pct=80) == 3  # Exact boundary
        assert get_level_for_contribution(opted_in=True, contribution_pct=100) == 3  # Max
        assert get_level_for_contribution(opted_in=True, contribution_pct=90) == 3  # Middle


# =============================================================================
# TEST: get_locked_preview()
# =============================================================================
class TestGetLockedPreview:
    """Tests for get_locked_preview function"""
    
    def test_level_0_preview(self):
        """Level 0 should show what Level 1 unlocks"""
        preview = get_locked_preview(0)
        assert "Conditions and date ranges" in preview
        assert "Contributing clinics count" in preview
    
    def test_level_1_preview(self):
        """Level 1 should show what Level 2 unlocks"""
        preview = get_locked_preview(1)
        assert "Intervention categories" in preview
        assert "Response trend (improving/plateau/worse)" in preview
    
    def test_level_2_preview(self):
        """Level 2 should show what Level 3 unlocks"""
        preview = get_locked_preview(2)
        assert "Red flags" in preview
        assert "Timeline (short bullets)" in preview
        assert "Last seen date" in preview
    
    def test_level_3_preview(self):
        """Level 3 should show nothing (max level)"""
        preview = get_locked_preview(3)
        assert preview == []


# =============================================================================
# TEST: get_what_if_unlocks()
# =============================================================================
class TestGetWhatIfUnlocks:
    """Tests for get_what_if_unlocks function"""
    
    def test_level_0_shows_all_scenarios(self):
        """Level 0 user should see all 3 what-if scenarios"""
        scenarios = get_what_if_unlocks(current_pct=0, opted_in=True)
        assert len(scenarios) == 3
        
        targets = [s["targetPct"] for s in scenarios]
        assert 10 in targets  # Level 1
        assert 40 in targets  # Level 2
        assert 80 in targets  # Level 3
    
    def test_level_1_shows_level_2_and_3_scenarios(self):
        """Level 1 user should see Level 2 and 3 scenarios"""
        scenarios = get_what_if_unlocks(current_pct=30, opted_in=True)
        assert len(scenarios) == 2
        
        targets = [s["targetPct"] for s in scenarios]
        assert 40 in targets  # Level 2
        assert 80 in targets  # Level 3
    
    def test_level_2_shows_level_3_scenario(self):
        """Level 2 user should see only Level 3 scenario"""
        scenarios = get_what_if_unlocks(current_pct=60, opted_in=True)
        assert len(scenarios) == 1
        assert scenarios[0]["targetPct"] == 80
    
    def test_level_3_shows_no_scenarios(self):
        """Level 3 user should see no scenarios (already max)"""
        scenarios = get_what_if_unlocks(current_pct=90, opted_in=True)
        assert len(scenarios) == 0
    
    def test_increase_needed_calculation(self):
        """increaseNeeded should be calculated correctly"""
        scenarios = get_what_if_unlocks(current_pct=25, opted_in=True)
        
        # At 25%, current level is 1
        # To reach Level 2 (40%), need 40-25=15 more
        level_2_scenario = next(s for s in scenarios if s["targetLevel"] == 2)
        assert level_2_scenario["increaseNeeded"] == 15
        
        # To reach Level 3 (80%), need 80-25=55 more
        level_3_scenario = next(s for s in scenarios if s["targetLevel"] == 3)
        assert level_3_scenario["increaseNeeded"] == 55


# =============================================================================
# TEST: get_worst_response_trend()
# =============================================================================
class TestGetWorstResponseTrend:
    """Tests for get_worst_response_trend function"""
    
    def test_single_trend(self):
        """Single trend should return itself"""
        assert get_worst_response_trend(["improving"]) == "improving"
        assert get_worst_response_trend(["plateau"]) == "plateau"
        assert get_worst_response_trend(["worse"]) == "worse"
    
    def test_priority_worse_wins(self):
        """'worse' should always win"""
        assert get_worst_response_trend(["improving", "worse"]) == "worse"
        assert get_worst_response_trend(["plateau", "worse"]) == "worse"
        assert get_worst_response_trend(["improving", "plateau", "worse"]) == "worse"
    
    def test_priority_plateau_over_improving(self):
        """'plateau' should beat 'improving'"""
        assert get_worst_response_trend(["improving", "plateau"]) == "plateau"
    
    def test_empty_list(self):
        """Empty list should return empty string"""
        assert get_worst_response_trend([]) == ""


# =============================================================================
# TEST: contributor_summary_for_visible_level()
# CRITICAL: This tests the per-contributor detail gating
# =============================================================================
class TestContributorSummaryForVisibleLevel:
    """Tests for contributor_summary_for_visible_level function
    
    IMPORTANT: This function builds a summary filtered by visibleLevel.
    - Level 0: returns None (no data visible)
    - Level 1: conditions + dateRanges
    - Level 2: + interventions + responseTrend
    - Level 3: + redFlags + timeline + lastSeenDate
    """
    
    def test_level_0_returns_none(self):
        """Level 0 should return None - no data visible"""
        episode = Episode(
            episodeId="ep1",
            clinicId="A",
            fingerprint="test",
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Condition A"],
            interventions=["Intervention X"],
            responseTrend="improving",
            redFlags=["Red Flag 1"],
            timeline=["Event 1"]
        )
        
        result = contributor_summary_for_visible_level([episode], visible_level=0)
        assert result is None
    
    def test_level_1_only_conditions_and_dateranges(self):
        """Level 1 should return only conditions and dateRanges"""
        episode = Episode(
            episodeId="ep1",
            clinicId="A",
            fingerprint="test",
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Condition A", "Condition B"],
            interventions=["Intervention X"],
            responseTrend="improving",
            redFlags=["Red Flag 1"],
            timeline=["Event 1"]
        )
        
        result = contributor_summary_for_visible_level([episode], visible_level=1)
        
        assert result is not None
        assert "conditions" in result
        assert set(result["conditions"]) == {"Condition A", "Condition B"}
        assert "dateRanges" in result
        
        # Level 2 fields should NOT be present
        assert "interventions" not in result
        assert "responseTrend" not in result
        
        # Level 3 fields should NOT be present
        assert "redFlags" not in result
        assert "timeline" not in result
        assert "lastSeenDate" not in result
    
    def test_level_2_adds_interventions_and_trend(self):
        """Level 2 should add interventions and responseTrend"""
        episode = Episode(
            episodeId="ep1",
            clinicId="A",
            fingerprint="test",
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Condition A"],
            interventions=["Intervention X", "Intervention Y"],
            responseTrend="plateau",
            redFlags=["Red Flag 1"],
            timeline=["Event 1"]
        )
        
        result = contributor_summary_for_visible_level([episode], visible_level=2)
        
        assert result is not None
        # Level 1 fields present
        assert "conditions" in result
        assert "dateRanges" in result
        
        # Level 2 fields present
        assert "interventions" in result
        assert set(result["interventions"]) == {"Intervention X", "Intervention Y"}
        assert "responseTrend" in result
        assert result["responseTrend"] == "plateau"
        
        # Level 3 fields should NOT be present
        assert "redFlags" not in result
        assert "timeline" not in result
        assert "lastSeenDate" not in result
    
    def test_level_3_adds_all_fields(self):
        """Level 3 should add redFlags, timeline, lastSeenDate"""
        episode = Episode(
            episodeId="ep1",
            clinicId="A",
            fingerprint="test",
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Condition A"],
            interventions=["Intervention X"],
            responseTrend="worse",
            redFlags=["Red Flag 1", "Red Flag 2"],
            timeline=["Event 1", "Event 2", "Event 3"]
        )
        
        result = contributor_summary_for_visible_level([episode], visible_level=3)
        
        assert result is not None
        # All fields present
        assert "conditions" in result
        assert "dateRanges" in result
        assert "interventions" in result
        assert "responseTrend" in result
        assert "redFlags" in result
        assert set(result["redFlags"]) == {"Red Flag 1", "Red Flag 2"}
        assert "timeline" in result
        assert "lastSeenDate" in result
        assert result["lastSeenDate"] == "2023-12-31"
    
    def test_timeline_capped_at_5(self):
        """Timeline should be capped at 5 items"""
        episode = Episode(
            episodeId="ep1",
            clinicId="A",
            fingerprint="test",
            startDate="2023-01-01",
            endDate="2023-12-31",
            conditions=["Test"],
            interventions=["Test"],
            responseTrend="improving",
            redFlags=[],
            timeline=[f"Event {i}" for i in range(10)]  # 10 items
        )
        
        result = contributor_summary_for_visible_level([episode], visible_level=3)
        assert len(result["timeline"]) <= 5
    
    def test_empty_episodes_returns_none(self):
        """Empty episodes list should return None"""
        result = contributor_summary_for_visible_level([], visible_level=3)
        assert result is None


# =============================================================================
# TEST: aggregate_shared_summary_from_contributors()
# CRITICAL: Tests aggregation logic with per-contributor level gating
# =============================================================================
class TestAggregateSharedSummaryFromContributors:
    """Tests for aggregate_shared_summary_from_contributors function
    
    IMPORTANT: Aggregation rules:
    - conditions/dateRanges: aggregated from visibleLevel >= 1 contributors
    - interventions/responseTrend: aggregated from visibleLevel >= 2 contributors
    - redFlags/timeline/lastSeenDate: aggregated from visibleLevel >= 3 contributors
    """
    
    def test_empty_contributors_returns_none(self):
        """Empty contributor summaries should return None"""
        result = aggregate_shared_summary_from_contributors({})
        assert result is None
    
    def test_level_1_only_contributors(self):
        """With only Level 1 contributors, only conditions/dateRanges aggregated"""
        contributor_summaries = {
            "ClinicX": (1, {
                "conditions": ["Condition A"],
                "dateRanges": [{"start": "2023-01-01", "end": "2023-06-30"}]
            }),
            "ClinicY": (1, {
                "conditions": ["Condition B"],
                "dateRanges": [{"start": "2023-07-01", "end": "2023-12-31"}]
            })
        }
        
        result = aggregate_shared_summary_from_contributors(contributor_summaries)
        
        assert result is not None
        assert set(result["conditions"]) == {"Condition A", "Condition B"}
        assert len(result["dateRanges"]) == 2
        
        # Level 2+ fields should NOT be present
        assert "interventions" not in result
        assert "responseTrend" not in result
        assert "redFlags" not in result
    
    def test_mixed_level_contributors(self):
        """Mixed levels should aggregate based on each contributor's level"""
        contributor_summaries = {
            "ClinicL1": (1, {
                "conditions": ["Condition A"],
                "dateRanges": [{"start": "2023-01-01", "end": "2023-03-31"}]
            }),
            "ClinicL2": (2, {
                "conditions": ["Condition B"],
                "dateRanges": [{"start": "2023-04-01", "end": "2023-06-30"}],
                "interventions": ["Intervention X"],
                "responseTrend": "improving"
            }),
            "ClinicL3": (3, {
                "conditions": ["Condition C"],
                "dateRanges": [{"start": "2023-07-01", "end": "2023-12-31"}],
                "interventions": ["Intervention Y"],
                "responseTrend": "worse",
                "redFlags": ["Red Flag 1"],
                "timeline": ["Event 1"],
                "lastSeenDate": "2023-12-31"
            })
        }
        
        result = aggregate_shared_summary_from_contributors(contributor_summaries)
        
        # conditions from all 3
        assert set(result["conditions"]) == {"Condition A", "Condition B", "Condition C"}
        
        # interventions only from L2 and L3
        assert set(result["interventions"]) == {"Intervention X", "Intervention Y"}
        
        # responseTrend worst across L2 and L3
        assert result["responseTrend"] == "worse"
        
        # redFlags/timeline/lastSeenDate only from L3
        assert result["redFlags"] == ["Red Flag 1"]
        assert result["timeline"] == ["Event 1"]
        assert result["lastSeenDate"] == "2023-12-31"
    
    def test_response_trend_aggregation_worst_wins(self):
        """responseTrend should aggregate to worst across Level 2+ contributors"""
        contributor_summaries = {
            "ClinicA": (2, {
                "conditions": ["A"],
                "dateRanges": [],
                "interventions": ["X"],
                "responseTrend": "improving"
            }),
            "ClinicB": (2, {
                "conditions": ["B"],
                "dateRanges": [],
                "interventions": ["Y"],
                "responseTrend": "plateau"
            })
        }
        
        result = aggregate_shared_summary_from_contributors(contributor_summaries)
        assert result["responseTrend"] == "plateau"


# =============================================================================
# TEST: check_patient_match() - MAIN INTEGRATION TESTS
# CRITICAL: This tests the full patient matching with per-contributor gating
# =============================================================================
class TestCheckPatientMatch:
    """Tests for check_patient_match function - the core business logic"""
    
    def test_nonexistent_clinic_returns_error(self):
        """Should return error for non-existent clinic"""
        result = check_patient_match("test|fp", "NONEXISTENT")
        assert "error" in result
        assert result["error"] == "Clinic not found"
    
    def test_no_match_found(self):
        """Should indicate no match when fingerprint not found"""
        fp = compute_fingerprint("Unknown Person", "2000-01-01", "0000")
        result = check_patient_match(fp, "A")
        
        assert result["matchFound"] is False
        assert result["sharedSummary"] is None
    
    def test_match_found_basic(self):
        """Should indicate match found when fingerprint exists in other clinics"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # Request from B (has no John Doe episodes)
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 50
        
        result = check_patient_match(fp, "B")
        
        assert result["matchFound"] is True
        assert result["fingerprint"] == fp
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_requesting_clinic_info(self):
        """Should return correct requesting clinic info"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 45
        
        result = check_patient_match(fp, "B")
        
        assert result["requestingClinic"]["clinicId"] == "B"
        assert result["requestingClinic"]["optedIn"] is True
        assert result["requestingClinic"]["contributionPct"] == 45
        assert result["requestingClinic"]["contextLevel"] == 2
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# TEST: visibleLevel = min(requesterLevel, contributorLevel) LOGIC
# CRITICAL: This tests the core per-contributor gating logic
# =============================================================================
class TestVisibleLevelGating:
    """Tests for the visibleLevel calculation: min(requesterLevel, contributorLevel)
    
    CRITICAL CONDITION: The visible level for each contributor is capped by
    the MINIMUM of the requester's level and the contributor's level.
    
    If this logic is incorrect, tests here will highlight the issue.
    """
    
    def test_requester_level_3_contributor_level_1(self):
        """
        Requester Level 3, Contributor Level 1:
        visibleLevel should be 1 (contributor caps the visibility)
        
        EXPLANATION:
        - Requester is willing to share 80%+ (Level 3)
        - Contributor only shares 10-39% (Level 1)
        - Visible data is capped by the LESSER contributor level
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B requests at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3
        
        # C is at Level 1 (30% in seed data)
        assert clinics["C"].get_context_level() == 1
        
        result = check_patient_match(fp, "B")
        
        # Find C in contributing clinics
        c_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "C"),
            None
        )
        
        assert c_detail is not None
        assert c_detail["contributorLevel"] == 1
        assert c_detail["visibleLevel"] == 1  # min(3, 1) = 1
        assert c_detail["isCapped"] is True  # 1 < 3
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_requester_level_1_contributor_level_3(self):
        """
        Requester Level 1, Contributor Level 3:
        visibleLevel should be 1 (requester caps the visibility)
        
        EXPLANATION:
        - Requester only shares 10-39% (Level 1)
        - Contributor shares 80%+ (Level 3)
        - Visible data is capped by the LESSER requester level
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B requests at Level 1
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 25  # Level 1
        
        # A is at Level 3 (85% in seed data)
        assert clinics["A"].get_context_level() == 3
        
        result = check_patient_match(fp, "B")
        
        # Find A in contributing clinics
        a_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A"),
            None
        )
        
        assert a_detail is not None
        assert a_detail["contributorLevel"] == 3
        assert a_detail["visibleLevel"] == 1  # min(1, 3) = 1
        assert a_detail["isCapped"] is False  # 3 >= 1, contributor is NOT capped
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_equal_levels_not_capped(self):
        """
        Equal levels: visibleLevel equals both, isCapped is False
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B requests at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 85  # Level 3
        
        # A is also Level 3
        assert clinics["A"].get_context_level() == 3
        
        result = check_patient_match(fp, "B")
        
        a_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A"),
            None
        )
        
        assert a_detail is not None
        assert a_detail["contributorLevel"] == 3
        assert a_detail["visibleLevel"] == 3  # min(3, 3) = 3
        assert a_detail["isCapped"] is False  # 3 >= 3
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# TEST: isCapped CONDITION CORRECTNESS
# CRITICAL: Tests the is_capped = (contributorLevel < requesterLevel) logic
# =============================================================================
class TestIsCappedLogic:
    """Tests for the isCapped condition
    
    CURRENT LOGIC in logic.py line 241:
        is_capped = contributor_level < requester_level
    
    This means:
    - isCapped = True when contributor provides LESS detail than requester could see
    - isCapped = False when contributor provides EQUAL OR MORE detail
    
    POTENTIAL ISSUE: This logic seems correct for indicating when the
    CONTRIBUTOR is limiting the visible data. However, if the requester
    is at a lower level, they wouldn't see full data anyway (but that's
    due to their own limits, not the contributor's).
    """
    
    def test_is_capped_true_when_contributor_lower(self):
        """isCapped=True when contributorLevel < requesterLevel"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90  # Level 3
        
        # C is Level 1 (lower)
        assert clinics["C"].get_context_level() == 1
        
        result = check_patient_match(fp, "B")
        
        c_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "C"),
            None
        )
        
        # C's level (1) < B's level (3), so C is capped
        assert c_detail["isCapped"] is True
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_is_capped_false_when_contributor_equal(self):
        """isCapped=False when contributorLevel == requesterLevel"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 85  # Level 3
        
        # A is also Level 3
        assert clinics["A"].get_context_level() == 3
        
        result = check_patient_match(fp, "B")
        
        a_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A"),
            None
        )
        
        # A's level (3) == B's level (3), so A is NOT capped
        assert a_detail["isCapped"] is False
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
    
    def test_is_capped_false_when_contributor_higher(self):
        """isCapped=False when contributorLevel > requesterLevel
        
        NOTE: In this case, the REQUESTER is the limiting factor, not the
        contributor. So it makes sense that isCapped (referring to the
        contributor being the limiter) is False.
        """
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B at Level 1
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 15  # Level 1
        
        # A is Level 3 (higher)
        assert clinics["A"].get_context_level() == 3
        
        result = check_patient_match(fp, "B")
        
        a_detail = next(
            (c for c in result["contributionGating"]["contributingClinics"] if c["clinicId"] == "A"),
            None
        )
        
        # A's level (3) > B's level (1), so A is NOT the capping factor
        assert a_detail["isCapped"] is False
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# TEST: detailCappedClinicsCount ACCURACY
# =============================================================================
class TestDetailCappedClinicsCount:
    """Tests for detailCappedClinicsCount calculation"""
    
    def test_count_matches_capped_contributors(self):
        """detailCappedClinicsCount should match number of isCapped=True contributors"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B at Level 3
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90
        
        result = check_patient_match(fp, "B")
        
        # Count manually
        capped_count = sum(
            1 for c in result["contributionGating"]["contributingClinics"]
            if c["isCapped"]
        )
        
        assert result["contributionGating"]["detailCappedClinicsCount"] == capped_count
        
        # In seed data: A is Level 3 (not capped), C is Level 1 (capped)
        assert capped_count == 1
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# TEST: sharedSummary null when requesterLevel == 0
# =============================================================================
class TestSharedSummaryNullConditions:
    """Tests for when sharedSummary should be null"""
    
    def test_level_0_requester_gets_null_summary(self):
        """Level 0 requester should always get null sharedSummary even with matches"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B at Level 0 (not opted in)
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 100  # High pct but not opted in = Level 0
        
        result = check_patient_match(fp, "B")
        
        assert result["matchFound"] is True  # Matches exist
        assert result["requestingClinic"]["contextLevel"] == 0
        assert result["sharedSummary"] is None
    
    def test_no_match_gets_null_summary(self):
        """No match should always get null sharedSummary"""
        fp = compute_fingerprint("Unknown Person", "2000-01-01", "0000")
        
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 90
        
        result = check_patient_match(fp, "B")
        
        assert result["matchFound"] is False
        assert result["sharedSummary"] is None
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0


# =============================================================================
# TEST: Opted-out contributors are filtered
# =============================================================================
class TestOptedOutContributorFiltering:
    """Tests for opted-out contributor filtering"""
    
    def test_opted_out_contributor_not_included(self):
        """Opted-out clinics should not appear in contributing clinics"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        # B requests
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 50
        
        # Confirm B is not opted out (so we can see the filter working on others)
        # A is opted in (seed: 85%), C is opted in (seed: 30%)
        assert clinics["A"].optedIn is True
        assert clinics["C"].optedIn is True
        
        result = check_patient_match(fp, "B")
        
        # Both A and C should be in contributing clinics
        contributor_ids = {c["clinicId"] for c in result["contributionGating"]["contributingClinics"]}
        assert "A" in contributor_ids
        assert "C" in contributor_ids
        
        # Now opt out C
        clinics["C"].optedIn = False
        
        result2 = check_patient_match(fp, "B")
        
        # Only A should be in contributing clinics now
        contributor_ids2 = {c["clinicId"] for c in result2["contributionGating"]["contributingClinics"]}
        assert "A" in contributor_ids2
        assert "C" not in contributor_ids2
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
        clinics["C"].optedIn = True
        clinics["C"].contributionPct = 30


# =============================================================================
# TEST: Network stats
# =============================================================================
class TestNetworkStats:
    """Tests for networkStats in response"""
    
    def test_participating_clinics_count(self):
        """Should count only opted-in clinics"""
        fp = compute_fingerprint("John Doe", "1990-01-15", "1234")
        
        clinics["B"].optedIn = True
        clinics["B"].contributionPct = 50
        
        result = check_patient_match(fp, "B")
        
        # In seed: A is opted in, B we just opted in, C is opted in
        # So 3 opted in
        expected_count = sum(1 for c in clinics.values() if c.optedIn)
        assert result["networkStats"]["participatingClinicsCount"] == expected_count
        
        # Reset
        clinics["B"].optedIn = False
        clinics["B"].contributionPct = 0
