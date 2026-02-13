# Seed data - EXACT spec implementation
from models import Clinic, Episode, clinics, episodes

def seed_data():
    """Initialize clinics and patient episodes per spec"""
    # Clear existing data
    clinics.clear()
    episodes.clear()
    
    # Create 3 clinics per spec:
    # Clinic A: optedIn=true, contributionPct=85
    # Clinic B: optedIn=false, contributionPct=0
    # Clinic C: optedIn=true, contributionPct=30
    clinic_a = Clinic(clinicId="A", name="Clinic A", optedIn=True, contributionPct=85)
    clinic_b = Clinic(clinicId="B", name="Clinic B", optedIn=False, contributionPct=0)
    clinic_c = Clinic(clinicId="C", name="Clinic C", optedIn=True, contributionPct=30)
    
    clinics["A"] = clinic_a
    clinics["B"] = clinic_b
    clinics["C"] = clinic_c
    
    # Patient 1: Has episodes in Clinic A and Clinic C
    # Using normalized fingerprint format: normalize(name)|dob|phoneLast4
    fingerprint1 = "john doe|1990-01-15|1234"
    
    episode1a = Episode(
        episodeId="ep1a",
        clinicId="A",
        fingerprint=fingerprint1,
        startDate="2023-01-15",
        endDate="2023-06-20",
        conditions=["Hypertension", "Type 2 Diabetes"],
        interventions=["Medication Management", "Lifestyle Counseling"],
        responseTrend="improving",
        redFlags=["Non-adherence to medication"],
        timeline=[
            "Initial diagnosis Jan 2023",
            "Medication started Feb 2023",
            "Improvement noted by May 2023"
        ]
    )
    
    episode1c = Episode(
        episodeId="ep1c",
        clinicId="C",
        fingerprint=fingerprint1,
        startDate="2023-07-01",
        endDate="2024-01-10",
        conditions=["Hypertension", "Type 2 Diabetes", "High Cholesterol"],
        interventions=["Medication Management", "Dietary Changes", "Exercise Program"],
        responseTrend="plateau",
        redFlags=["Elevated BP readings"],
        timeline=[
            "Transferred care Jul 2023",
            "Cholesterol added Aug 2023",
            "Stable through Dec 2023"
        ]
    )
    
    # Patient 2: Has episode only in Clinic A (per spec)
    fingerprint2 = "jane smith|1985-03-22|5678"
    
    episode2a = Episode(
        episodeId="ep2a",
        clinicId="A",
        fingerprint=fingerprint2,
        startDate="2022-05-10",
        endDate="2023-02-15",
        conditions=["Asthma", "Seasonal Allergies"],
        interventions=["Inhaler Therapy", "Allergy Management"],
        responseTrend="improving",
        redFlags=["Frequent ER visits"],
        timeline=[
            "Asthma diagnosis May 2022",
            "Inhaler started Jun 2022",
            "Reduced ER visits by Sep 2022"
        ]
    )
    
    # Patient 3: Has episodes in Clinic B and Clinic C — plateau/worse trends
    fingerprint3 = "alex rivera|1978-11-03|9012"

    episode3b = Episode(
        episodeId="ep3b",
        clinicId="B",
        fingerprint=fingerprint3,
        startDate="2023-03-10",
        endDate="2023-09-25",
        conditions=["Chronic Lower Back Pain", "Sciatica"],
        interventions=["Manual Therapy", "Core Strengthening"],
        responseTrend="plateau",
        redFlags=["Recurring flare-ups"],
        timeline=[
            "Back pain history Mar 2023",
            "Manual therapy started Apr 2023",
            "Plateau through Sep 2023"
        ]
    )

    episode3c = Episode(
        episodeId="ep3c",
        clinicId="C",
        fingerprint=fingerprint3,
        startDate="2023-10-05",
        endDate="2024-03-15",
        conditions=["Chronic Lower Back Pain", "Sciatica", "Hip Bursitis"],
        interventions=["Shockwave Therapy", "Pilates Program"],
        responseTrend="improving",
        redFlags=[],
        timeline=[
            "Transferred Oct 2023",
            "Shockwave started Nov 2023",
            "Significant improvement by Feb 2024"
        ]
    )

    # Patient 4: Has episode only in Clinic A — worse trend for distribution variety
    fingerprint4 = "maria chen|2000-07-20|3456"

    episode4a = Episode(
        episodeId="ep4a",
        clinicId="A",
        fingerprint=fingerprint4,
        startDate="2024-01-08",
        endDate="2024-06-30",
        conditions=["Rotator Cuff Tear", "Frozen Shoulder"],
        interventions=["Post-surgical Rehab", "ROM Exercises"],
        responseTrend="plateau",
        redFlags=["Post-op complications", "Slow ROM recovery"],
        timeline=[
            "Surgery Jan 2024",
            "Rehab started Feb 2024",
            "Limited progress through Jun 2024"
        ]
    )

    # Add all episodes
    episodes.extend([episode1a, episode1c, episode2a, episode3b, episode3c, episode4a])
    
    print("Seed data initialized:")
    print(f"  - 3 clinics: {list(clinics.keys())}")
    print(f"  - Clinic A: optedIn={clinic_a.optedIn}, contributionPct={clinic_a.contributionPct}")
    print(f"  - Clinic B: optedIn={clinic_b.optedIn}, contributionPct={clinic_b.contributionPct}")
    print(f"  - Clinic C: optedIn={clinic_c.optedIn}, contributionPct={clinic_c.contributionPct}")
    print(f"  - {len(episodes)} patient episodes")
    print(f"  - Patient 1 fingerprint: {fingerprint1}")
    print(f"  - Patient 2 fingerprint: {fingerprint2}")
    print(f"  - Patient 3 fingerprint: {fingerprint3}")
    print(f"  - Patient 4 fingerprint: {fingerprint4}")

if __name__ == "__main__":
    seed_data()
