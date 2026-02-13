# Incentive Design Under Adversarial Conditions

A working prototype that demonstrates how to make information sharing a selfish, rational decision for competing physiotherapy clinics. The system uses tiered reciprocity, continuity credits, and outcome benchmarking to drive opt-in from 19% toward 80%+.

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Backend runs at http://localhost:8001

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

## Guided Demo

Click **"Start Guided Demo"** in the header. It walks through the incentive mechanism in 5 steps:

1. All clinics at Level 0 (the 19% world: nobody shares, nobody sees anything)
2. One clinic opts in at Level 1 (first mover advantage)
3. That clinic increases to Level 3 (reciprocity: contribute more, see more)
4. Another clinic uses shared history via Continue Care (credits are awarded)
5. Open the Dashboard to see credits and outcome benchmarking

Each step drives real state changes through the API. The narration explains why each step matters for scaling adoption.

## Key Features

- **Tiered access**: 4 context levels (0-3) based on contribution percentage. Free-riders see nothing.
- **Reciprocity**: visibleLevel = min(requesterLevel, contributorLevel). You only see data at the level you share.
- **Continuity credits**: Awarded when another clinic uses your shared history to continue care. Idempotent (no inflation).
- **Outcome benchmarking**: You vs Network Average (improving/plateau/worse). Anonymized. Locked for Level 0.
- **What-If calculator**: Shows exactly what each clinic would unlock by increasing contribution.
- **Compare Clinics**: Side-by-side view of how the same patient looks from two different clinic perspectives.
- **Demo reset**: Reviewer tools to reset state or set all clinics to Level 0 for testing scenarios.
- **Privacy by design**: Reactive sharing only. Contributing clinics are never notified. No clinic names in benchmarks.

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

150 tests across 8 test files covering context levels, reciprocity, gating, credits, benchmarking, idempotency, edge cases, and demo reset.

## Seed Data

**3 Clinics:**

| Clinic | Opted In | Contribution | Level | Status |
|--------|----------|-------------|-------|--------|
| A | Yes | 85% | 3 | Trusted Contributor |
| B | No | 0% | 0 | Isolated |
| C | Yes | 30% | 1 | Basic |

**2 Patients:**

| Patient | Clinics | Used for |
|---------|---------|----------|
| John Doe (DOB: 1990-01-15, Phone: 1234) | A, C | Cross-clinic demo (preset in UI) |
| Jane Smith (DOB: 1985-03-22, Phone: 5678) | A | Single-clinic demo (preset in UI) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /clinics | List all clinics with context levels |
| POST | /clinics/{id}/settings | Update clinic opt-in and contribution |
| POST | /intake/check | Check for shared patient history |
| POST | /intake/continue-care | Record continued care, award credits |
| GET | /credits/dashboard | Credits per clinic and recent events |
| GET | /clinics/{id}/benchmark | Outcome benchmarking (you vs network) |
| GET | /demo/status | Whether demo mode is enabled |
| POST | /demo/reset | Reset to baseline (demo mode only) |
| POST | /demo/scenario/all_level_0 | Set all clinics to Level 0 (demo mode only) |

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic, in-memory data (no database)
- **Frontend**: React, TypeScript, Vite
- **Testing**: pytest with FastAPI TestClient
- **No authentication**: Prototype only
