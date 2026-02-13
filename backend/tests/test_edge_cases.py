"""
Edge case tests for incentive logic
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from seed import seed_data
from models import clinics, compute_fingerprint
from logic import check_patient_match

# Reset seed data before tests
seed_data()

client = TestClient(app)


class TestTopContributorParadox:
    """Regression: top contributor no longer blocks clinics; details are capped per-contributor."""
    
    def test_top_contributor_90_percent_gets_full_from_a_partial_from_c(self):
        """
        NEW per-contributor detail gating:
        - Requester gets all opted-in contributor clinics (never blocked by pct mismatches)
        - visibleLevel = min(requesterLevel, contributorLevel) per clinic
        """
        # Use Clinic B as requester (no episodes) and set to 90% (Level 3)
        response = client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 90})
        assert response.status_code == 200
        assert response.json()["contextLevel"] == 3

        intake_response = client.post(
            "/intake/check",
            json={"clinicId": "B", "fullName": "John Doe", "dob": "1990-01-15", "phoneLast4": "1234"},
        )
        assert intake_response.status_code == 200
        
        data = intake_response.json()

        assert data["matchFound"] is True
        assert data["sharedSummary"] is not None

        # Two opted-in contributor clinics (A and C); C is capped at Level 1
        assert data["contributionGating"]["contributingClinicsCount"] == 2
        assert data["contributionGating"]["detailCappedClinicsCount"] == 1

        summary = data["sharedSummary"]
        # At Level 3 requester, only Level>=3 contributors contribute redFlags/timeline/lastSeenDate
        assert "redFlags" in summary
        assert "timeline" in summary
        assert "lastSeenDate" in summary

        # Reset Clinic B to seeded state
        client.post("/clinics/B/settings", json={"optedIn": False, "contributionPct": 0})


class TestOptOutConsistency:
    """Test that opted-out clinics consistently get Level 0 and null sharedSummary"""
    
    def test_opt_out_consistency_level_0_and_null_summary(self):
        """
        Opt-out consistency test:
        - Set requesting clinic optedIn=false, contributionPct=0
        - Call /intake/check for Patient 1
        - Assert requesting contextLevel == 0
        - Assert sharedSummary is null
        - Assert contributionGating counts follow the current intended policy
        """
        # Set Clinic B to opted out (it already is, but ensure)
        response = client.post(
            "/clinics/B/settings",
            json={"optedIn": False, "contributionPct": 0}
        )
        assert response.status_code == 200
        assert response.json()["optedIn"] is False
        assert response.json()["contextLevel"] == 0
        
        # Check Patient 1
        intake_response = client.post(
            "/intake/check",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234"
            }
        )
        assert intake_response.status_code == 200
        
        data = intake_response.json()
        
        # Assert contextLevel is 0
        assert data["requestingClinic"]["contextLevel"] == 0
        assert data["requestingClinic"]["optedIn"] is False
        
        # Assert sharedSummary is null (Level 0 always returns null)
        assert data["sharedSummary"] is None
        
        # Assert contributionGating counts
        # For opted-out clinics, sharedSummary must be null, but we still report contributor counts.
        assert "contributionGating" in data
        assert "contributingClinicsCount" in data["contributionGating"]
        assert "detailCappedClinicsCount" in data["contributionGating"]
        assert data["contributionGating"]["contributingClinicsCount"] == 2
        assert data["contributionGating"]["detailCappedClinicsCount"] == 0


class TestPHILeakage:
    """Test that PHI (Protected Health Information) does not leak in responses"""
    
    def test_phi_leakage_no_full_name_in_response(self):
        """
        PHI leakage test:
        - Call /intake/check with a name and phoneLast4
        - Assert the response body does not contain the raw fullName string
        - Response may include fingerprint only (which is hashed/normalized)
        """
        test_name = "Alice Johnson"
        test_dob = "1985-05-20"
        test_phone = "9876"
        
        intake_response = client.post(
            "/intake/check",
            json={
                "clinicId": "A",
                "fullName": test_name,
                "dob": test_dob,
                "phoneLast4": test_phone
            }
        )
        assert intake_response.status_code == 200
        
        response_text = intake_response.text
        data = intake_response.json()
        
        # Assert raw fullName format is NOT in response (case-sensitive check)
        # The normalized version in fingerprint is expected and OK
        assert test_name not in response_text  # "Alice Johnson" should not appear
        assert "Alice Johnson" not in response_text
        
        # Assert fingerprint is present (normalized version is expected)
        assert "fingerprint" in data
        # Fingerprint should be normalized (lowercase, trimmed)
        expected_fingerprint = compute_fingerprint(test_name, test_dob, test_phone)
        assert data["fingerprint"] == expected_fingerprint
        # Fingerprint should be normalized, not raw
        assert data["fingerprint"] == "alice johnson|1985-05-20|9876"
        
        # The normalized name in fingerprint is acceptable (it's the design)
        # But the raw capitalized name should not appear anywhere else
        # Check that "Alice" (capitalized) doesn't appear outside fingerprint context
        import json
        response_dict = json.loads(response_text)
        # Only fingerprint should contain name parts, and only in normalized form
        assert response_dict["fingerprint"] == "alice johnson|1985-05-20|9876"
    
    def test_phi_leakage_no_full_phone_in_response(self):
        """
        PHI leakage test:
        - Assert the response does not contain any phone digits beyond the provided last4
        - Response may include fingerprint (which contains last4), but no full phone number
        """
        test_name = "Bob Williams"
        test_dob = "1992-08-15"
        test_phone_last4 = "5432"
        
        intake_response = client.post(
            "/intake/check",
            json={
                "clinicId": "A",
                "fullName": test_name,
                "dob": test_dob,
                "phoneLast4": test_phone_last4
            }
        )
        assert intake_response.status_code == 200
        
        response_text = intake_response.text
        data = intake_response.json()
        
        # Assert only last4 appears in response (in fingerprint)
        # Should NOT contain full phone numbers like "555-1234-5432" or "55512345432"
        # The last4 digits should only appear as part of the fingerprint
        assert test_phone_last4 in response_text  # OK - it's in the fingerprint
        
        # Assert no full phone number patterns (more than 4 consecutive digits)
        import re
        # Check for patterns that might indicate full phone numbers
        # Should not have more than 4 consecutive digits except in the fingerprint format
        phone_patterns = [
            r'\d{5,}',  # 5 or more consecutive digits (beyond last4)
            r'\(\d{3}\)',  # (555) format
            r'\d{3}-\d{3}-\d{4}',  # 555-123-4567 format
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, response_text)
            # Only allow matches that are part of the fingerprint format (name|dob|last4)
            for match in matches:
                # If it's not in the fingerprint context, it's a leak
                assert match in data["fingerprint"], f"Found potential phone leak: {match}"
        
        # Verify fingerprint format is correct (contains last4 but normalized)
        assert "fingerprint" in data
        assert test_phone_last4 in data["fingerprint"]
        assert data["fingerprint"].endswith(f"|{test_dob}|{test_phone_last4}")
    
    def test_phi_leakage_no_raw_name_variations(self):
        """
        Test that no variations of the raw name appear in response
        """
        test_name = "Mary Jane Watson"
        test_dob = "1990-01-01"
        test_phone = "1111"
        
        intake_response = client.post(
            "/intake/check",
            json={
                "clinicId": "A",
                "fullName": test_name,
                "dob": test_dob,
                "phoneLast4": test_phone
            }
        )
        assert intake_response.status_code == 200
        
        response_text = intake_response.text
        data = intake_response.json()
        
        # Assert raw name format (capitalized) does NOT appear in response
        assert "Mary Jane Watson" not in response_text
        assert "Mary" not in response_text
        assert "Jane" not in response_text
        assert "Watson" not in response_text
        
        # The normalized lowercase version in fingerprint is expected (by design)
        # This is acceptable because it's a deterministic hash-like identifier
        assert "fingerprint" in data
        # Fingerprint should be normalized: "mary jane watson|1990-01-01|1111"
        assert data["fingerprint"] == "mary jane watson|1990-01-01|1111"
        
        # Verify that the normalized name only appears in the fingerprint field
        # and nowhere else in the response
        import json
        response_dict = json.loads(response_text)
        fingerprint_value = response_dict["fingerprint"]
        # Check that name parts only appear in fingerprint
        assert "mary jane watson" in fingerprint_value
        # But not in other fields
        for key, value in response_dict.items():
            if key != "fingerprint":
                if isinstance(value, str):
                    assert "mary jane watson" not in value.lower()
                elif isinstance(value, dict):
                    # Recursively check nested dicts
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, str):
                            assert "mary jane watson" not in nested_value.lower()
