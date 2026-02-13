"""
Test Context Level computation and fingerprint normalization
"""
import pytest
from models import Clinic, compute_fingerprint, normalize_name


class TestContextLevelComputation:
    """Test that context levels are computed correctly"""
    
    def test_opted_in_false_always_level_0(self):
        """optedIn=false always yields Level 0"""
        clinic = Clinic(clinicId="TEST", name="Test Clinic", optedIn=False, contributionPct=100)
        assert clinic.get_context_level() == 0
        
        clinic.contributionPct = 50
        assert clinic.get_context_level() == 0
        
        clinic.contributionPct = 0
        assert clinic.get_context_level() == 0
    
    def test_opted_in_true_contribution_0_to_9_level_0(self):
        """optedIn=true with contributionPct 0-9 yields Level 0"""
        clinic = Clinic(clinicId="TEST", name="Test Clinic", optedIn=True, contributionPct=0)
        assert clinic.get_context_level() == 0
        
        clinic.contributionPct = 9
        assert clinic.get_context_level() == 0
    
    def test_contribution_10_to_39_level_1(self):
        """contributionPct 10-39 yields Level 1"""
        clinic = Clinic(clinicId="TEST", name="Test Clinic", optedIn=True, contributionPct=10)
        assert clinic.get_context_level() == 1
        
        clinic.contributionPct = 39
        assert clinic.get_context_level() == 1
        
        clinic.contributionPct = 25
        assert clinic.get_context_level() == 1
    
    def test_contribution_40_to_79_level_2(self):
        """contributionPct 40-79 yields Level 2"""
        clinic = Clinic(clinicId="TEST", name="Test Clinic", optedIn=True, contributionPct=40)
        assert clinic.get_context_level() == 2
        
        clinic.contributionPct = 79
        assert clinic.get_context_level() == 2
        
        clinic.contributionPct = 60
        assert clinic.get_context_level() == 2
    
    def test_contribution_80_to_100_level_3(self):
        """contributionPct 80-100 yields Level 3"""
        clinic = Clinic(clinicId="TEST", name="Test Clinic", optedIn=True, contributionPct=80)
        assert clinic.get_context_level() == 3
        
        clinic.contributionPct = 100
        assert clinic.get_context_level() == 3
        
        clinic.contributionPct = 85
        assert clinic.get_context_level() == 3


class TestFingerprintNormalization:
    """Test fingerprint computation and name normalization"""
    
    def test_fingerprint_format(self):
        """Fingerprint should be normalize(name)|dob|phoneLast4"""
        fp1 = compute_fingerprint("John Doe", "1990-01-01", "1234")
        assert fp1 == "john doe|1990-01-01|1234"
    
    def test_name_normalization_trim(self):
        """Names should be trimmed"""
        fp1 = compute_fingerprint("John Smith", "1990-01-01", "1234")
        fp2 = compute_fingerprint(" John Smith ", "1990-01-01", "1234")
        fp3 = compute_fingerprint("  John Smith  ", "1990-01-01", "1234")
        assert fp1 == fp2 == fp3 == "john smith|1990-01-01|1234"
    
    def test_name_normalization_lowercase(self):
        """Names should be lowercased"""
        fp1 = compute_fingerprint("JOHN SMITH", "1990-01-01", "1234")
        fp2 = compute_fingerprint("john smith", "1990-01-01", "1234")
        assert fp1 == fp2 == "john smith|1990-01-01|1234"
    
    def test_name_normalization_multiple_spaces(self):
        """Multiple spaces should collapse to single space"""
        fp1 = compute_fingerprint("John  Smith", "1990-01-01", "1234")
        fp2 = compute_fingerprint("John   Smith", "1990-01-01", "1234")
        fp3 = compute_fingerprint("John Smith", "1990-01-01", "1234")
        assert fp1 == fp2 == fp3 == "john smith|1990-01-01|1234"
    
    def test_name_normalization_mixed_case_and_spaces(self):
        """Test combined normalization"""
        fp1 = compute_fingerprint("John  Smith", "1990-01-01", "1234")
        fp2 = compute_fingerprint(" john smith ", "1990-01-01", "1234")
        assert fp1 == fp2 == "john smith|1990-01-01|1234"
    
    def test_normalize_name_function(self):
        """Test normalize_name function directly"""
        assert normalize_name("John  Smith") == "john smith"
        assert normalize_name("  JOHN SMITH  ") == "john smith"
        assert normalize_name("John\tSmith") == "john smith"  # tabs become spaces
        assert normalize_name("John   Doe   Smith") == "john doe smith"
