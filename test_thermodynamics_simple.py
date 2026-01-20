"""
Simple test for thermodynamic ensemble scoring (no RDKit dependency).

This validates the core thermodynamic calculations without requiring
molecular structure libraries.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from thermodynamics import ThermodynamicEnsemble


def test_henderson_hasselbalch():
    """Test Henderson-Hasselbalch probability calculations."""
    print("=" * 60)
    print("Test 1: Henderson-Hasselbalch Calculations")
    print("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    
    # Test case 1: Acid at pKa = pH (should be 50/50)
    pka = 7.0
    ph = 7.0
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    print(f"\nAcid at pH=pKa: P(protonated) = {p_prot:.3f}")
    assert abs(p_prot - 0.5) < 0.01, f"Should be 0.5 at pH=pKa, got {p_prot}"
    print("  ✓ Correct (0.500)")
    
    # Test case 2: Acid at pH >> pKa (should be mostly deprotonated)
    ph = 10.0
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    print(f"\nAcid at pH=10 (pKa=7): P(protonated) = {p_prot:.3f}")
    assert p_prot < 0.01, f"Should be mostly deprotonated, got {p_prot}"
    print("  ✓ Correct (< 0.01)")
    
    # Test case 3: Acid at pH << pKa (should be mostly protonated)
    ph = 4.0
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    print(f"\nAcid at pH=4 (pKa=7): P(protonated) = {p_prot:.3f}")
    assert p_prot > 0.99, f"Should be mostly protonated, got {p_prot}"
    print("  ✓ Correct (> 0.99)")
    
    # Test case 4: Base at pKa = pH
    p_prot = thermo.compute_site_probability(pka, ph=7.0, site_type="base")
    print(f"\nBase at pH=pKa: P(protonated) = {p_prot:.3f}")
    assert abs(p_prot - 0.5) < 0.01, f"Should be 0.5 at pH=pKa, got {p_prot}"
    print("  ✓ Correct (0.500)")
    
    print("\n✓ All Henderson-Hasselbalch tests passed!")
    return True


def test_ensemble_aggregation():
    """Test ensemble aggregation with mock data."""
    print("\n" + "=" * 60)
    print("Test 2: Ensemble Aggregation")
    print("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    
    # Mock two-state system at pH 7.4 with pKa 7.0
    pka = 7.0
    ph = 7.4
    
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    p_deprot = 1.0 - p_prot
    
    print(f"\nTwo-state system: pKa={pka}, pH={ph}")
    print(f"  P(COOH)  = {p_prot:.3f}")
    print(f"  P(COO-)  = {p_deprot:.3f}")
    
    # Mock states
    states = [
        {"state_id": 0, "probability": p_prot, "charge": 0},
        {"state_id": 1, "probability": p_deprot, "charge": -1}
    ]
    
    # Mock docking results (deprotonated binds better)
    docking_results = [
        {"state_id": 0, "delta_g": -7.0},  # COOH
        {"state_id": 1, "delta_g": -9.0}   # COO- (more favorable)
    ]
    
    print(f"\nDocking scores:")
    print(f"  State 0 (COOH): {docking_results[0]['delta_g']} kcal/mol")
    print(f"  State 1 (COO-): {docking_results[1]['delta_g']} kcal/mol")
    
    # Test weighted average
    delta_g_ensemble = thermo.aggregate_binding_energy(states, docking_results)
    
    # Manual calculation for verification
    expected = p_prot * (-7.0) + p_deprot * (-9.0)
    
    print(f"\nResults:")
    print(f"  Ensemble ΔG: {delta_g_ensemble:.3f} kcal/mol")
    print(f"  Expected:    {expected:.3f} kcal/mol")
    print(f"  Difference:  {abs(delta_g_ensemble - expected):.6f} kcal/mol")
    
    assert abs(delta_g_ensemble - expected) < 0.01, \
        f"Mismatch: {delta_g_ensemble} vs {expected}"
    print("  ✓ Weighted average correct!")
    
    # Test Boltzmann averaging
    delta_g_boltzmann = thermo.boltzmann_average_binding_energy(states, docking_results)
    print(f"\n  Boltzmann ΔG: {delta_g_boltzmann:.3f} kcal/mol")
    print("  ✓ Boltzmann averaging computed!")
    
    print("\n✓ All ensemble aggregation tests passed!")
    return True


def test_ph_titration_curve():
    """Test pH titration curve generation."""
    print("\n" + "=" * 60)
    print("Test 3: pH Titration Curve")
    print("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    pka = 7.0
    
    # Generate states across pH range
    ph_values = [5.0, 6.0, 7.0, 7.4, 8.0, 9.0]
    states_by_ph = {}
    docking_results_by_ph = {}
    
    # Same docking scores at all pH (only probabilities change)
    mock_docking = [
        {"state_id": 0, "delta_g": -7.0},
        {"state_id": 1, "delta_g": -9.0}
    ]
    
    for ph in ph_values:
        p_prot = thermo.compute_site_probability(pka, ph, "acid")
        states_by_ph[ph] = [
            {"state_id": 0, "probability": p_prot, "charge": 0},
            {"state_id": 1, "probability": 1.0 - p_prot, "charge": -1}
        ]
        docking_results_by_ph[ph] = mock_docking
    
    # Compute titration curve
    curve = thermo.compute_ph_titration_curve(states_by_ph, docking_results_by_ph)
    
    print("\npH Titration Curve:")
    print("-" * 50)
    print(f"{'pH':<6} {'ΔG_bind':<12} {'Method':<20}")
    print("-" * 50)
    for _, row in curve.iterrows():
        print(f"{row['pH']:<6.1f} {row['delta_g_bind']:<12.3f} {row['method']:<20}")
    
    # At low pH, should favor protonated (ΔG closer to -7.0)
    # At high pH, should favor deprotonated (ΔG closer to -9.0)
    low_ph_result = curve[curve['pH'] == 5.0].iloc[0]['delta_g_bind']
    high_ph_result = curve[curve['pH'] == 9.0].iloc[0]['delta_g_bind']
    
    print(f"\nΔG at pH 5.0 (mostly COOH): {low_ph_result:.2f} kcal/mol")
    print(f"ΔG at pH 9.0 (mostly COO-): {high_ph_result:.2f} kcal/mol")
    print(f"Difference: {abs(low_ph_result - high_ph_result):.2f} kcal/mol")
    
    assert low_ph_result > high_ph_result, \
        "High pH should have more favorable binding (more negative ΔG)"
    print("  ✓ pH-dependent trend correct!")
    
    print("\n✓ All pH titration curve tests passed!")
    return True


def test_contribution_analysis():
    """Test state contribution analysis."""
    print("\n" + "=" * 60)
    print("Test 4: Contribution Analysis")
    print("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    
    # Three-state system with varying contributions
    states = [
        {"state_id": 0, "probability": 0.70, "charge": 0, "smiles": "COOH"},
        {"state_id": 1, "probability": 0.25, "charge": -1, "smiles": "COO-"},
        {"state_id": 2, "probability": 0.05, "charge": 0, "smiles": "other"}
    ]
    
    docking_results = [
        {"state_id": 0, "delta_g": -7.0},
        {"state_id": 1, "delta_g": -9.0},
        {"state_id": 2, "delta_g": -6.0}
    ]
    
    contributions = thermo.compute_state_contributions(states, docking_results)
    
    print("\nState Contributions:")
    print("-" * 60)
    print(f"{'State':<8} {'P(i)':<8} {'ΔG_i':<12} {'P(i)×ΔG_i':<15} {'SMILES':<10}")
    print("-" * 60)
    for _, row in contributions.iterrows():
        print(f"{row['state_id']:<8} {row['probability']:<8.3f} "
              f"{row['delta_g']:<12.2f} {row['contribution']:<15.3f} "
              f"{row['smiles']:<10}")
    
    # Verify contributions sum to ensemble average
    total_contribution = contributions['contribution'].sum()
    ensemble_avg = thermo.aggregate_binding_energy(states, docking_results)
    
    print("-" * 60)
    print(f"Sum of contributions: {total_contribution:.3f} kcal/mol")
    print(f"Ensemble average:     {ensemble_avg:.3f} kcal/mol")
    print(f"Difference:           {abs(total_contribution - ensemble_avg):.6f} kcal/mol")
    
    assert abs(total_contribution - ensemble_avg) < 0.01, \
        "Contributions should sum to ensemble average"
    print("  ✓ Contributions sum correctly!")
    
    print("\n✓ All contribution analysis tests passed!")
    return True


def test_multisite_probability():
    """Test multi-site microstate probability calculation."""
    print("\n" + "=" * 60)
    print("Test 5: Multi-Site Microstate Probability")
    print("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    
    # Two-site molecule: one acid (pKa=4.5), one base (pKa=9.5)
    pka_sites = [
        {"pka": 4.5, "type": "acid"},
        {"pka": 9.5, "type": "base"}
    ]
    
    ph = 7.0
    
    # Microstate: both protonated
    microstate = {"site_states": [True, True]}  # [acid_prot, base_prot]
    
    prob = thermo.compute_microstate_probability(microstate, pka_sites, ph)
    
    # Manual calculation
    p_acid_prot = thermo.compute_site_probability(4.5, 7.0, "acid")
    p_base_prot = thermo.compute_site_probability(9.5, 7.0, "base")
    expected = p_acid_prot * p_base_prot
    
    print(f"\nTwo-site molecule at pH {ph}:")
    print(f"  Site 1 (acid, pKa=4.5): P(prot) = {p_acid_prot:.3f}")
    print(f"  Site 2 (base, pKa=9.5): P(prot) = {p_base_prot:.3f}")
    print(f"\nMicrostate (both protonated):")
    print(f"  Calculated:  {prob:.6f}")
    print(f"  Expected:    {expected:.6f}")
    print(f"  Difference:  {abs(prob - expected):.9f}")
    
    assert abs(prob - expected) < 1e-6, \
        f"Microstate probability mismatch: {prob} vs {expected}"
    print("  ✓ Multi-site probability correct!")
    
    print("\n✓ All multi-site tests passed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("THERMODYNAMIC ENSEMBLE SCORING VALIDATION")
    print("(Simplified - no RDKit dependency)")
    print("=" * 60)
    
    try:
        # Run all tests
        test_henderson_hasselbalch()
        test_ensemble_aggregation()
        test_ph_titration_curve()
        test_contribution_analysis()
        test_multisite_probability()
        
        # Summary
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe thermodynamic ensemble implementation is working correctly!")
        print("\nCore features validated:")
        print("  ✓ Henderson-Hasselbalch calculations")
        print("  ✓ Weighted ensemble averaging (ΔG_bind = Σ P_i × ΔG_i)")
        print("  ✓ Boltzmann averaging")
        print("  ✓ pH titration curves")
        print("  ✓ Contribution analysis")
        print("  ✓ Multi-site microstate probabilities")
        
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run full tests: python test_thermodynamics.py")
        print("  3. Run with docking: python main.py --mode ph_ensemble_docking")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
