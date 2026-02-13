"""
API smoke tests using FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from seed import seed_data
from models import clinics

# Reset seed data before tests
seed_data()

client = TestClient(app)


class TestClinicsEndpoint:
    """Test GET /clinics endpoint"""
    
    def test_get_clinics_returns_3_seeded_clinics(self):
        """GET /clinics returns 3 seeded clinics with correct levels"""
        response = client.get("/clinics")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        
        # Check clinic IDs
        clinic_ids = {c["clinicId"] for c in data}
        assert clinic_ids == {"A", "B", "C"}
        
        # Check Clinic A
        clinic_a = next(c for c in data if c["clinicId"] == "A")
        assert clinic_a["optedIn"] is True
        assert clinic_a["contributionPct"] == 85
        assert clinic_a["contextLevel"] == 3
        
        # Check Clinic B
        clinic_b = next(c for c in data if c["clinicId"] == "B")
        assert clinic_b["optedIn"] is False
        assert clinic_b["contributionPct"] == 0
        assert clinic_b["contextLevel"] == 0
        
        # Check Clinic C
        clinic_c = next(c for c in data if c["clinicId"] == "C")
        assert clinic_c["optedIn"] is True
        assert clinic_c["contributionPct"] == 30
        assert clinic_c["contextLevel"] == 1


class TestClinicSettingsEndpoint:
    """Test POST /clinics/{clinicId}/settings endpoint"""
    
    def test_update_clinic_settings_updates_level(self):
        """POST /clinics/{id}/settings updates level as expected"""
        # Update Clinic C to 45% (should be Level 2)
        response = client.post(
            "/clinics/C/settings",
            json={"optedIn": True, "contributionPct": 45}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["clinicId"] == "C"
        assert data["contributionPct"] == 45
        assert data["contextLevel"] == 2
        
        # Update Clinic C back to 30%
        response = client.post(
            "/clinics/C/settings",
            json={"optedIn": True, "contributionPct": 30}
        )
        assert response.status_code == 200
        assert response.json()["contextLevel"] == 1
    
    def test_opt_out_forces_contribution_zero_api(self):
        """API: When optedIn=false, contributionPct is always stored and returned as 0."""
        # Set Clinic A to opted in with 70%
        client.post("/clinics/A/settings", json={"optedIn": True, "contributionPct": 70})
        resp = client.get("/clinics")
        clinic_a = next(c for c in resp.json() if c["clinicId"] == "A")
        assert clinic_a["contributionPct"] == 70

        # Opt out with non-zero contribution - must be ignored, stored as 0
        resp = client.post(
            "/clinics/A/settings",
            json={"optedIn": False, "contributionPct": 50}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["optedIn"] is False
        assert data["contributionPct"] == 0
        assert data["contextLevel"] == 0
        assert data["networkStatus"] == "Isolated"

        # Verify GET also returns 0
        resp = client.get("/clinics")
        clinic_a = next(c for c in resp.json() if c["clinicId"] == "A")
        assert clinic_a["contributionPct"] == 0

        # Reset Clinic A to seed state for downstream tests
        client.post("/clinics/A/settings", json={"optedIn": True, "contributionPct": 85})

    def test_update_clinic_settings_validation(self):
        """Settings endpoint validates contributionPct range"""
        # Test invalid contributionPct > 100
        response = client.post(
            "/clinics/A/settings",
            json={"optedIn": True, "contributionPct": 101}
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid contributionPct < 0
        response = client.post(
            "/clinics/A/settings",
            json={"optedIn": True, "contributionPct": -1}
        )
        assert response.status_code == 422  # Validation error


class TestIntakeCheckEndpoint:
    """Test POST /intake/check endpoint"""
    
    def test_free_rider_clinic_sees_level_0(self):
        """Free rider clinic (optedOut) sees Level 0"""
        # Set Clinic B to opted out (it already is, but ensure)
        client.post(
            "/clinics/B/settings",
            json={"optedIn": False, "contributionPct": 0}
        )
        
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requestingClinic"]["contextLevel"] == 0
        assert data["requestingClinic"]["optedIn"] is False
        # matchFound is based on raw episodes from other clinics (before filtering)
        assert data["matchFound"] is True
        
        # Level 0 always returns null sharedSummary
        assert data["sharedSummary"] is None

        # New gating object
        assert data["contributionGating"]["contributingClinicsCount"] == 2
        assert data["contributionGating"]["detailCappedClinicsCount"] == 0
    
    def test_medium_contributor_45_percent(self):
        """Medium contributor (45%, Level 2) sees both contributors, C capped to Level 1."""
        # Use Clinic B as requester so both A and C are "other clinics"
        # Set Clinic B to 45% (Level 2)
        client.post(
            "/clinics/B/settings",
            json={"optedIn": True, "contributionPct": 45}
        )
        
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requestingClinic"]["contextLevel"] == 2
        assert data["requestingClinic"]["contributionPct"] == 45
        
        # Check new gating object
        assert "contributionGating" in data
        assert "contributingClinicsCount" in data["contributionGating"]
        assert "detailCappedClinicsCount" in data["contributionGating"]
        assert data["contributionGating"]["contributingClinicsCount"] == 2  # A and C
        assert data["contributionGating"]["detailCappedClinicsCount"] == 1  # C is Level 1 < requester Level 2

        assert data["matchFound"] is True
        assert data["sharedSummary"] is not None
        summary = data["sharedSummary"]

        # Level 2 requester sees:
        # - conditions/dateRanges from both contributors (A and C)
        # - interventions/responseTrend only from contributors with visibleLevel>=2 (A only)
        assert "conditions" in summary
        assert "dateRanges" in summary
        assert "interventions" in summary
        assert "responseTrend" in summary

        # Not Level 3 for requester
        assert "redFlags" not in summary
        assert "timeline" not in summary
        assert "lastSeenDate" not in summary

        # Reset Clinic B to opted-out per seed
        client.post("/clinics/B/settings", json={"optedIn": False, "contributionPct": 0})
    
    def test_low_contributor_20_percent(self):
        """Low contributor (20%, Level 1) sees both contributors at Level 1 detail."""
        # Use Clinic B as requester so both A and C are "other clinics"
        client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 20})
        client.post(
            "/clinics/B/settings",
            json={"optedIn": True, "contributionPct": 20}
        )
        
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["requestingClinic"]["contextLevel"] == 1
        assert data["requestingClinic"]["contributionPct"] == 20
        
        assert data["matchFound"] is True
        assert data["sharedSummary"] is not None
        summary = data["sharedSummary"]

        # Level 1 fields only
        assert "conditions" in summary
        assert "dateRanges" in summary
        assert "interventions" not in summary
        assert "responseTrend" not in summary

        # New gating object: both contributing clinics opted-in, and none are capped below Level 1
        assert data["contributionGating"]["contributingClinicsCount"] == 2
        assert data["contributionGating"]["detailCappedClinicsCount"] == 0

        # Reset Clinic B to opted-out per seed
        client.post("/clinics/B/settings", json={"optedIn": False, "contributionPct": 0})
    
    def test_intake_check_validation(self):
        """intake/check validates phoneLast4 format"""
        # Invalid phoneLast4 (not 4 digits)
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "A",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "123"  # Only 3 digits
            }
        )
        assert response.status_code == 400
        
        # Invalid phoneLast4 (non-numeric)
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "A",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "abcd"
            }
        )
        assert response.status_code == 400
    
    def test_intake_check_returns_expected_structure(self):
        """intake/check returns expected structure with all required fields"""
        response = client.post(
            "/intake/check",
            json={
                "clinicId": "C",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Required top-level fields
        assert "matchFound" in data
        assert "fingerprint" in data
        assert "requestingClinic" in data
        assert "networkStats" in data
        assert "contributionGating" in data
        assert "lockedPreview" in data
        
        # requestingClinic structure
        assert "clinicId" in data["requestingClinic"]
        assert "optedIn" in data["requestingClinic"]
        assert "contributionPct" in data["requestingClinic"]
        assert "contextLevel" in data["requestingClinic"]
        
        # networkStats structure
        assert "participatingClinicsCount" in data["networkStats"]
        assert "participatingClinicsPct" in data["networkStats"]
        
        # contributionGating structure
        assert "contributingClinicsCount" in data["contributionGating"]
        assert "detailCappedClinicsCount" in data["contributionGating"]
        assert "reason" in data["contributionGating"]
        
        # lockedPreview structure
        assert "nextLevelUnlocks" in data["lockedPreview"]
        assert isinstance(data["lockedPreview"]["nextLevelUnlocks"], list)
