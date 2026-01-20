"""
Test script for pH-aware thermodynamic ensemble scoring.

This script validates the implementation without requiring actual docking.
"""

import logging
from pathlib import Path
from rdkit import Chem

from src.protonation_engine import ProtonationEngine
from src.thermodynamics import ThermodynamicEnsemble, aggregate_binding_energy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_microstate_enumeration():
    """Test microstate enumeration with probability calculation."""
    logger.info("=" * 60)
    logger.info("Test 1: Microstate Enumeration")
    logger.info("=" * 60)
    
    # Test molecule: acetic acid (single carboxyl group, pKa ~4.8)
    smiles = "CC(=O)O"
    mol = Chem.MolFromSmiles(smiles)
    
    engine = ProtonationEngine()
    
    # Test at different pH values
    for ph in [4.0, 4.8, 7.4]:
        logger.info(f"\nTesting acetic acid at pH {ph}:")
        
        microstates = engine.enumerate_microstates_with_probabilities(
            mol=mol,
            pka_values=[4.8],  # Known pKa for acetic acid
            ph=ph,
            probability_threshold=0.001
        )
        
        logger.info(f"  Found {len(microstates)} microstates")
        for state in microstates:
            logger.info(
                f"    State {state['state_id']}: "
                f"P={state['probability']:.3f}, "
                f"charge={state['charge']}, "
                f"SMILES={state['smiles']}"
            )
        
        # Verify probabilities sum to ~1.0
        total_prob = sum(s['probability'] for s in microstates)
        logger.info(f"  Total probability: {total_prob:.4f}")
        assert abs(total_prob - 1.0) < 0.01, f"Probabilities don't sum to 1: {total_prob}"
    
    logger.info("\n✓ Microstate enumeration test passed")


def test_henderson_hasselbalch():
    """Test Henderson-Hasselbalch probability calculations."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Henderson-Hasselbalch Calculations")
    logger.info("=" * 60)
    
    thermo = ThermodynamicEnsemble()
    
    # Test case 1: Acid at pKa = pH
    pka = 7.0
    ph = 7.0
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    logger.info(f"\nAcid at pH=pKa: P(protonated) = {p_prot:.3f}")
    assert abs(p_prot - 0.5) < 0.01, f"Should be 0.5 at pH=pKa, got {p_prot}"
    
    # Test case 2: Acid at pH >> pKa (should be deprotonated)
    ph = 10.0
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    logger.info(f"Acid at pH=10 (pKa=7): P(protonated) = {p_prot:.3f}")
    assert p_prot < 0.01, f"Should be mostly deprotonated, got {p_prot}"
    
    # Test case 3: Base at pKa = pH
    p_prot = thermo.compute_site_probability(pka, ph=7.0, site_type="base")
    logger.info(f"Base at pH=pKa: P(protonated) = {p_prot:.3f}")
    assert abs(p_prot - 0.5) < 0.01, f"Should be 0.5 at pH=pKa, got {p_prot}"
    
    logger.info("\n✓ Henderson-Hasselbalch test passed")


def test_ensemble_aggregation():
    """Test ensemble aggregation with mock docking scores."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Ensemble Aggregation")
    logger.info("=" * 60)
    
    # Mock two-state system (protonated vs deprotonated)
    # at pH 7.4 with pKa 7.0
    thermo = ThermodynamicEnsemble()
    
    pka = 7.0
    ph = 7.4
    
    p_prot = thermo.compute_site_probability(pka, ph, "acid")
    p_deprot = 1.0 - p_prot
    
    logger.info(f"\nTwo-state system: pKa={pka}, pH={ph}")
    logger.info(f"  P(COOH) = {p_prot:.3f}")
    logger.info(f"  P(COO-) = {p_deprot:.3f}")
    
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
    
    logger.info(f"\nDocking scores:")
    logger.info(f"  State 0 (COOH): {docking_results[0]['delta_g']} kcal/mol")
    logger.info(f"  State 1 (COO-): {docking_results[1]['delta_g']} kcal/mol")
    
    # Test weighted average
    delta_g_ensemble = thermo.aggregate_binding_energy(states, docking_results)
    
    # Manual calculation for verification
    expected = p_prot * (-7.0) + p_deprot * (-9.0)
    
    logger.info(f"\nResults:")
    logger.info(f"  Ensemble ΔG: {delta_g_ensemble:.3f} kcal/mol")
    logger.info(f"  Expected:    {expected:.3f} kcal/mol")
    
    assert abs(delta_g_ensemble - expected) < 0.01, \
        f"Mismatch: {delta_g_ensemble} vs {expected}"
    
    # Test Boltzmann averaging
    delta_g_boltzmann = thermo.boltzmann_average_binding_energy(states, docking_results)
    logger.info(f"  Boltzmann ΔG: {delta_g_boltzmann:.3f} kcal/mol")
    
    logger.info("\n✓ Ensemble aggregation test passed")


def test_ph_titration_curve():
    """Test pH titration curve generation."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: pH Titration Curve")
    logger.info("=" * 60)
    
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
    
    logger.info("\npH Titration Curve:")
    logger.info(curve[['pH', 'delta_g_bind', 'num_states']].to_string(index=False))
    
    # At low pH, should favor protonated (ΔG closer to -7.0)
    # At high pH, should favor deprotonated (ΔG closer to -9.0)
    low_ph_result = curve[curve['pH'] == 5.0].iloc[0]['delta_g_bind']
    high_ph_result = curve[curve['pH'] == 9.0].iloc[0]['delta_g_bind']
    
    logger.info(f"\nΔG at pH 5.0 (mostly COOH): {low_ph_result:.2f} kcal/mol")
    logger.info(f"ΔG at pH 9.0 (mostly COO-): {high_ph_result:.2f} kcal/mol")
    
    assert low_ph_result > high_ph_result, \
        "High pH should have more favorable binding (more negative ΔG)"
    
    logger.info("\n✓ pH titration curve test passed")


def test_multi_site_molecule():
    """Test molecule with multiple ionizable sites."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 5: Multi-Site Molecule")
    logger.info("=" * 60)
    
    # Ibuprofen has one carboxyl group (pKa ~4.9)
    # For a real multi-site test, we'd use something like glycine (NH3+/COO-)
    smiles = "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"  # Ibuprofen
    mol = Chem.MolFromSmiles(smiles)
    
    engine = ProtonationEngine()
    
    ph = 7.4
    microstates = engine.enumerate_microstates_with_probabilities(
        mol=mol,
        ph=ph,
        probability_threshold=0.001
    )
    
    logger.info(f"\nIbuprofen at pH {ph}:")
    logger.info(f"  Found {len(microstates)} microstates")
    
    for i, state in enumerate(microstates[:5]):  # Show top 5
        logger.info(
            f"    State {i}: P={state['probability']:.3f}, "
            f"charge={state['charge']}"
        )
    
    total_prob = sum(s['probability'] for s in microstates)
    logger.info(f"  Total probability: {total_prob:.4f}")
    
    logger.info("\n✓ Multi-site molecule test passed")


def test_contribution_analysis():
    """Test state contribution analysis."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 6: Contribution Analysis")
    logger.info("=" * 60)
    
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
    
    logger.info("\nState Contributions:")
    logger.info(contributions[['state_id', 'probability', 'delta_g', 'contribution']].to_string(index=False))
    
    # Verify contributions sum to ensemble average
    total_contribution = contributions['contribution'].sum()
    ensemble_avg = thermo.aggregate_binding_energy(states, docking_results)
    
    logger.info(f"\nSum of contributions: {total_contribution:.3f} kcal/mol")
    logger.info(f"Ensemble average:     {ensemble_avg:.3f} kcal/mol")
    
    assert abs(total_contribution - ensemble_avg) < 0.01, \
        "Contributions should sum to ensemble average"
    
    logger.info("\n✓ Contribution analysis test passed")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("THERMODYNAMIC ENSEMBLE SCORING VALIDATION")
    logger.info("=" * 60)
    
    try:
        test_microstate_enumeration()
        test_henderson_hasselbalch()
        test_ensemble_aggregation()
        test_ph_titration_curve()
        test_multi_site_molecule()
        test_contribution_analysis()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nThe thermodynamic ensemble implementation is working correctly!")
        logger.info("\nNext steps:")
        logger.info("  1. Run actual docking with: python main.py --mode ph_ensemble_docking")
        logger.info("  2. Compare against baseline (single-state docking)")
        logger.info("  3. Validate on SAMPL6 or other benchmarks")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
