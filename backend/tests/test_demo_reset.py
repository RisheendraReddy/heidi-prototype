"""
Tests for demo reset endpoint. Demo reset is only available when DEMO_MODE=true.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from credits import get_all_clinic_credits, get_recent_credit_events, reset_credits
from seed import seed_data


client = TestClient(app)


class TestDemoResetEndpoint:
    """Test POST /demo/reset is gated by DEMO_MODE and behaves correctly."""

    def test_demo_reset_endpoint_disabled_when_demo_mode_false(self, monkeypatch):
        """When DEMO_MODE is false or unset, POST /demo/reset returns 404."""
        # Ensure DEMO_MODE is false
        monkeypatch.delenv("DEMO_MODE", raising=False)
        monkeypatch.setenv("DEMO_MODE", "false")

        resp = client.post("/demo/reset")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_demo_reset_endpoint_disabled_when_demo_mode_unset(self, monkeypatch):
        """When DEMO_MODE is unset, POST /demo/reset returns 404."""
        monkeypatch.delenv("DEMO_MODE", raising=False)

        resp = client.post("/demo/reset")
        assert resp.status_code == 404

    def test_demo_reset_clears_credits_and_events_when_demo_mode_true(
        self, monkeypatch
    ):
        """When DEMO_MODE=true, reset clears credits, events, and restores clinic defaults."""
        monkeypatch.setenv("DEMO_MODE", "true")

        # Seed and award some credits (via continue-care flow)
        seed_data()
        reset_credits()
        client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 45})
        cont_resp = client.post(
            "/intake/continue-care",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234",
            },
        )
        assert cont_resp.status_code == 200
        assert cont_resp.json()["credited"] is True

        dash_before = client.get("/credits/dashboard").json()
        assert dash_before["clinicCredits"].get("A", 0) == 1
        assert dash_before["clinicCredits"].get("C", 0) == 1
        assert len(dash_before["recentEvents"]) == 2

        # Call reset
        reset_resp = client.post("/demo/reset")
        assert reset_resp.status_code == 200
        assert reset_resp.json() == {"status": "ok"}

        # Credits and events cleared
        dash_after = client.get("/credits/dashboard").json()
        assert dash_after["clinicCredits"].get("A", 0) == 0
        assert dash_after["clinicCredits"].get("C", 0) == 0
        assert len(dash_after["recentEvents"]) == 0

        # Clinic settings restored to seed defaults (B: optedIn=false, contributionPct=0)
        clinics_resp = client.get("/clinics")
        assert clinics_resp.status_code == 200
        clinics = {c["clinicId"]: c for c in clinics_resp.json()}
        assert clinics["B"]["optedIn"] is False
        assert clinics["B"]["contributionPct"] == 0
        assert clinics["A"]["optedIn"] is True
        assert clinics["A"]["contributionPct"] == 85
        assert clinics["C"]["optedIn"] is True
        assert clinics["C"]["contributionPct"] == 30

        # Idempotency reset: same continue-care can be credited again after reset
        client.post("/clinics/B/settings", json={"optedIn": True, "contributionPct": 45})
        cont2 = client.post(
            "/intake/continue-care",
            json={
                "clinicId": "B",
                "fullName": "John Doe",
                "dob": "1990-01-15",
                "phoneLast4": "1234",
            },
        )
        assert cont2.status_code == 200
        assert cont2.json()["credited"] is True
        assert cont2.json()["creditsAwarded"] == 2
