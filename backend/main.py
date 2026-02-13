# Backend main entry point - EXACT spec implementation
import os
from dotenv import load_dotenv
load_dotenv()  # Load .env so DEMO_MODE=true works for local reviewers
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from models import compute_fingerprint, clinics
from logic import get_clinic, update_clinic_settings, check_patient_match, get_network_status
from seed import seed_data

# Initialize seed data
seed_data()

app = FastAPI(title="Incentive Design API")


def _is_demo_mode() -> bool:
    """True only when DEMO_MODE env var is explicitly 'true' (case-insensitive)."""
    return os.environ.get("DEMO_MODE", "").lower() == "true"

# Configure CORS - allow local dev and deployed Vercel frontend
_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]
# Add Vercel frontend URL from env if set (e.g. https://your-app.vercel.app)
_vercel_url = os.environ.get("FRONTEND_URL", "")
if _vercel_url:
    _allowed_origins.append(_vercel_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ClinicResponse(BaseModel):
    clinicId: str
    name: str
    optedIn: bool
    contributionPct: int
    contextLevel: int
    networkStatus: str

class ClinicSettingsUpdate(BaseModel):
    optedIn: bool
    contributionPct: int = Field(ge=0, le=100)

class IntakeCheckRequest(BaseModel):
    clinicId: str
    fullName: str
    dob: str  # YYYY-MM-DD
    phoneLast4: str

@app.get("/")
def read_root():
    return {"message": "Incentive Design Under Adversarial Conditions API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/clinics", response_model=List[ClinicResponse])
def get_all_clinics():
    """Get all clinics"""
    return [
        ClinicResponse(
            clinicId=clinic.clinicId,
            name=clinic.name,
            optedIn=clinic.optedIn,
            contributionPct=clinic.contributionPct,
            contextLevel=clinic.get_context_level(),
            networkStatus=get_network_status(clinic.get_context_level())
        )
        for clinic in clinics.values()
    ]

@app.post("/clinics/{clinic_id}/settings", response_model=ClinicResponse)
def update_clinic_settings_endpoint(clinic_id: str, settings: ClinicSettingsUpdate):
    """Update clinic settings"""
    clinic = update_clinic_settings(clinic_id, settings.optedIn, settings.contributionPct)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return ClinicResponse(
        clinicId=clinic.clinicId,
        name=clinic.name,
        optedIn=clinic.optedIn,
        contributionPct=clinic.contributionPct,
        contextLevel=clinic.get_context_level(),
        networkStatus=get_network_status(clinic.get_context_level())
    )

@app.post("/intake/continue-care")
def continue_care(intake: IntakeCheckRequest):
    """
    Simulate "Continue Care" - using shared history to continue care.
    Awards continuity credits to all contributing clinics with visible_level > 0.
    """
    if not intake.phoneLast4.isdigit() or len(intake.phoneLast4) != 4:
        raise HTTPException(status_code=400, detail="phoneLast4 must be exactly 4 digits")
    fingerprint = compute_fingerprint(intake.fullName, intake.dob, intake.phoneLast4)
    result = check_patient_match(fingerprint, intake.clinicId)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    if not result.get("matchFound") or not result.get("contributionGating"):
        return {
            "status": "no_contributors",
            "credited": False,
            "creditsAwarded": 0,
            "message": "No contributing clinics to award",
            "events": [],
        }

    contributing = result["contributionGating"].get("contributingClinics", [])
    to_award = [(c["clinicId"], c["visibleLevel"]) for c in contributing]

    from credits import award_continuity_credits
    events, credited = award_continuity_credits(fingerprint, intake.clinicId, to_award)

    if credited:
        return {
            "status": "recorded",
            "credited": True,
            "creditsAwarded": len(events),
            "message": f"Awarded {len(events)} credit(s) to contributing clinics",
            "events": events,
        }
    return {
        "status": "already_recorded",
        "credited": False,
        "creditsAwarded": 0,
        "message": "Already recorded for this patient and clinic pair",
        "events": [],
    }


@app.get("/credits/dashboard")
def get_credits_dashboard():
    """Get credits dashboard: total per clinic, last 5 events."""
    from credits import get_all_clinic_credits, get_recent_credit_events
    return {
        "clinicCredits": get_all_clinic_credits(),
        "recentEvents": get_recent_credit_events(5),
    }


@app.get("/clinics/{clinic_id}/benchmark")
def get_clinic_benchmark(clinic_id: str):
    """Get outcome benchmark: clinic vs network average (anonymized, safe fields only)."""
    from benchmarking import get_clinic_benchmark
    clinic = get_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return get_clinic_benchmark(clinic_id)


@app.post("/intake/check")
def check_intake(intake: IntakeCheckRequest):
    """
    Check for patient matches with reciprocity filtering and context-level gating.
    EXACT spec implementation.
    """
    # Validate phoneLast4 is 4 digits
    if not intake.phoneLast4.isdigit() or len(intake.phoneLast4) != 4:
        raise HTTPException(status_code=400, detail="phoneLast4 must be exactly 4 digits")
    
    # Compute fingerprint
    fingerprint = compute_fingerprint(intake.fullName, intake.dob, intake.phoneLast4)
    
    # Check for matches
    result = check_patient_match(fingerprint, intake.clinicId)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@app.get("/demo/status")
def demo_status():
    """Returns whether demo mode is enabled. Only for frontend visibility gate."""
    return {"demoMode": _is_demo_mode()}


@app.post("/demo/reset")
def demo_reset():
    """
    Reset prototype to baseline. Only available when DEMO_MODE=true.
    Restores: seed data, clears credits, clears idempotency keys.
    """
    if not _is_demo_mode():
        raise HTTPException(status_code=404, detail="Demo reset not available")
    from credits import reset_credits
    seed_data()
    reset_credits()
    return {"status": "ok"}


@app.post("/demo/scenario/all_level_0")
def demo_scenario_all_level_0():
    """
    Set all clinics to optedIn=true, contributionPct=0 (Level 0).
    Only available when DEMO_MODE=true.
    """
    if not _is_demo_mode():
        raise HTTPException(status_code=404, detail="Demo scenarios not available")
    for clinic in clinics.values():
        clinic.optedIn = True
        clinic.contributionPct = 0
    return [
        {
            "clinicId": c.clinicId,
            "name": c.name,
            "optedIn": c.optedIn,
            "contributionPct": c.contributionPct,
            "contextLevel": c.get_context_level(),
            "networkStatus": get_network_status(c.get_context_level()),
        }
        for c in clinics.values()
    ]


@app.get("/debug/test-match")
def debug_test_match():
    """Debug endpoint to test matching"""
    from models import compute_fingerprint
    fingerprint = compute_fingerprint("John Doe", "1990-01-15", "1234")
    result = check_patient_match(fingerprint, "A")
    return {
        "fingerprint": fingerprint,
        "result": result,
        "clinics": {c.clinicId: {"contributionPct": c.contributionPct, "optedIn": c.optedIn} for c in clinics.values()}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
