# In-memory data models - EXACT spec implementation
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import re

# In-memory storage
clinics: Dict[str, 'Clinic'] = {}
episodes: List['Episode'] = []

@dataclass
class Clinic:
    """Clinic configuration"""
    clinicId: str  # "A", "B", or "C"
    name: str
    optedIn: bool = True
    contributionPct: int = 50  # 0-100 percentage
    
    def get_context_level(self) -> int:
        """Calculate Context Level based on opt-in and contribution"""
        if not self.optedIn or self.contributionPct < 10:
            return 0
        elif self.contributionPct < 40:
            return 1
        elif self.contributionPct < 80:
            return 2
        else:
            return 3

@dataclass
class Episode:
    """Patient episode from a clinic"""
    episodeId: str
    clinicId: str  # Origin clinic
    fingerprint: str
    startDate: str  # YYYY-MM-DD
    endDate: str  # YYYY-MM-DD
    conditions: List[str] = field(default_factory=list)
    interventions: List[str] = field(default_factory=list)
    responseTrend: str = ""  # "improving" | "plateau" | "worse"
    redFlags: List[str] = field(default_factory=list)
    timeline: List[str] = field(default_factory=list)  # Short bullets

def normalize_name(name: str) -> str:
    """Normalize name: trim, lowercase, collapse multiple spaces into one"""
    normalized = name.strip().lower()
    normalized = re.sub(r'\s+', ' ', normalized)  # Collapse multiple spaces
    return normalized

def compute_fingerprint(full_name: str, dob: str, phone_last4: str) -> str:
    """Compute fingerprint: normalize(name) + "|" + dob + "|" + phoneLast4"""
    normalized_name = normalize_name(full_name)
    return f"{normalized_name}|{dob}|{phone_last4}"
