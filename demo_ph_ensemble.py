"""
Standalone demo of pH-aware ensemble docking (without full pipeline dependencies).

This demonstrates the thermodynamic ensemble scoring in action.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from thermodynamics import ThermodynamicEnsemble
from protonation_engine import ProtonationEngine
from rdkit import Chem

def demo_single_molecule():
    """Demo with a single molecule (acetic acid)."""
    print("=" * 70)
    print("DEMO: pH-Aware Ensemble Docking")
    print("=" * 70)
    
    # Create a simple molecule (acetic acid)
    smiles = "CC(=O)O"
    mol = Chem.MolFromSmiles(smiles)
    print(f"\nMolecule: Acetic acid")
    print(f"SMILES: {smiles}")
    print(f"Known pKa: ~4.8")
    
    # Initialize engines
    protonation_engine = ProtonationEngine()
    thermo_engine = ThermodynamicEnsemble()
    
    # Test at different pH values
    ph_values = [4.0, 7.4, 9.0]
    
    for ph in ph_values:
        print(f"\n{'-' * 70}")
        print(f"pH = {ph}")
        print(f"{'-' * 70}")
        
        # Step 1: Enumerate microstates with probabilities
        microstates = protonation_engine.enumerate_microstates_with_probabilities(
            mol=mol,
            pka_values=[4.8],  # Known pKa
            ph=ph,
            probability_threshold=0.001
        )
        
        print(f"\nEnumerated {len(microstates)} microstates:")
        for state in microstates:
            print(f"  State {state['state_id']}: "
                  f"P={state['probability']:.3f}, "
                  f"charge={state['charge']:+d}")
        
        # Step 2: Mock docking scores (in real app, this comes from GNINA)
        # Simulate that deprotonated form binds better
        mock_docking = []
        for state in microstates:
            if state['charge'] == 0:  # Protonated (COOH)
                delta_g = -7.0
            else:  # Deprotonated (COO-)
                delta_g = -9.0
            
            mock_docking.append({
                'state_id': state['state_id'],
                'delta_g': delta_g
            })
        
        print(f"\nMock docking scores:")
        for result in mock_docking:
            print(f"  State {result['state_id']}: ΔG = {result['delta_g']} kcal/mol")
        
        # Step 3: Compute ensemble-weighted binding energy
        delta_g_ensemble = thermo_engine.aggregate_binding_energy(
            states=microstates,
            docking_results=mock_docking
        )
        
        print(f"\n✨ Ensemble ΔG_bind(pH={ph}) = {delta_g_ensemble:.3f} kcal/mol")
        
        # Step 4: Analyze contributions
        contributions = thermo_engine.compute_state_contributions(
            states=microstates,
            docking_results=mock_docking
        )
        
        print(f"\nState contributions:")
        for _, row in contributions.iterrows():
            print(f"  State {row['state_id']}: "
                  f"{row['probability']:.3f} × {row['delta_g']:.1f} = "
                  f"{row['contribution']:.3f} kcal/mol")
    
    print(f"\n{'=' * 70}")
    print("Key Insight:")
    print(f"  At low pH (4.0):  Mostly protonated  → ΔG closer to -7.0")
    print(f"  At high pH (9.0): Mostly deprotonated → ΔG closer to -9.0")
    print(f"  pH-dependent binding affinity captured! ✓")
    print(f"{'=' * 70}")


def demo_ph_titration():
    """Demo pH titration curve."""
    print("\n\n" + "=" * 70)
    print("DEMO: pH Titration Curve")
    print("=" * 70)
    
    smiles = "CC(=O)O"
    mol = Chem.MolFromSmiles(smiles)
    
    protonation_engine = ProtonationEngine()
    thermo_engine = ThermodynamicEnsemble()
    
    # Generate data across pH range
    ph_values = [3.0, 4.0, 4.8, 5.0, 6.0, 7.0, 7.4, 8.0, 9.0, 10.0]
    states_by_ph = {}
    docking_by_ph = {}
    
    for ph in ph_values:
        microstates = protonation_engine.enumerate_microstates_with_probabilities(
            mol=mol,
            pka_values=[4.8],
            ph=ph,
            probability_threshold=0.001
        )
        states_by_ph[ph] = microstates
        
        # Mock docking (same scores at all pH)
        docking_by_ph[ph] = [
            {'state_id': 0, 'delta_g': -9.0},  # Deprotonated
            {'state_id': 1, 'delta_g': -7.0}   # Protonated
        ]
    
    # Compute titration curve
    curve = thermo_engine.compute_ph_titration_curve(states_by_ph, docking_by_ph)
    
    print("\npH-Dependent Binding Free Energy:")
    print("-" * 70)
    print(f"{'pH':<6} {'ΔG_bind':<12} {'Dominant State':<20}")
    print("-" * 70)
    
    for _, row in curve.iterrows():
        ph = row['pH']
        delta_g = row['delta_g_bind']
        
        # Determine dominant state
        states = states_by_ph[ph]
        dominant = max(states, key=lambda s: s['probability'])
        state_name = "COO- (deprotonated)" if dominant['charge'] < 0 else "COOH (protonated)"
        
        print(f"{ph:<6.1f} {delta_g:<12.3f} {state_name:<20}")
    
    print("-" * 70)
    print("\nObservations:")
    print("  - At low pH: Protonated form dominates, ΔG ~ -7.0 kcal/mol")
    print("  - At pKa (4.8): Equal mix, ΔG ~ -8.0 kcal/mol")
    print("  - At high pH: Deprotonated form dominates, ΔG ~ -9.0 kcal/mol")
    print("  - Smooth transition captured by ensemble averaging!")
    print("=" * 70)


def demo_multisite_molecule():
    """Demo with a multi-site molecule."""
    print("\n\n" + "=" * 70)
    print("DEMO: Multi-Site Molecule (Ibuprofen)")
    print("=" * 70)
    
    # Ibuprofen has one carboxylic acid group
    smiles = "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"
    mol = Chem.MolFromSmiles(smiles)
    
    print(f"\nMolecule: Ibuprofen")
    print(f"SMILES: {smiles}")
    print(f"Ionizable groups: 1 carboxylic acid (pKa ~ 4.9)")
    
    protonation_engine = ProtonationEngine()
    thermo_engine = ThermodynamicEnsemble()
    
    ph = 7.4
    
    # Enumerate microstates
    microstates = protonation_engine.enumerate_microstates_with_probabilities(
        mol=mol,
        pka_values=[4.9],
        ph=ph,
        probability_threshold=0.001
    )
    
    print(f"\nAt pH {ph}:")
    print(f"  Found {len(microstates)} significant microstates")
    
    for state in microstates:
        print(f"    State {state['state_id']}: "
              f"P={state['probability']:.4f}, "
              f"charge={state['charge']:+d}")
    
    # Mock docking
    mock_docking = [
        {'state_id': state['state_id'], 'delta_g': -8.5 if state['charge'] < 0 else -7.2}
        for state in microstates
    ]
    
    delta_g_ensemble = thermo_engine.aggregate_binding_energy(microstates, mock_docking)
    
    print(f"\n✨ Ensemble ΔG_bind = {delta_g_ensemble:.3f} kcal/mol")
    print(f"\nSince pH {ph} >> pKa {4.9}, ibuprofen is almost fully deprotonated")
    print(f"→ Ensemble score dominated by COO- form")
    print("=" * 70)


if __name__ == "__main__":
    print("\n" * 2)
    print("🧪 pH-AWARE ENSEMBLE DOCKING DEMONSTRATION 🧪")
    print("\n")
    
    try:
        demo_single_molecule()
        demo_ph_titration()
        demo_multisite_molecule()
        
        print("\n\n" + "=" * 70)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  1. Microstates enumerated with Henderson-Hasselbalch probabilities")
        print("  2. Each microstate docked separately (here: mocked)")
        print("  3. Ensemble average: ΔG_bind = Σ P_i × ΔG_i")
        print("  4. pH-dependent binding captured quantitatively")
        print("\nNext Steps:")
        print("  - Install GNINA for real docking")
        print("  - Run: python main.py --mode ph_ensemble_docking --receptor protein.pdb")
        print("  - Benchmark on SAMPL6 dataset")
        print("=" * 70)
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
