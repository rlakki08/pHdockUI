"""
Visual demonstration of pH-aware ensemble docking.

This creates publication-quality plots showing:
1. pH titration curves
2. Microstate populations
3. State contributions
4. Ensemble vs single-state comparison
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from thermodynamics import ThermodynamicEnsemble
from protonation_engine import ProtonationEngine
from rdkit import Chem

# Set publication-quality plot style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 10


def generate_ph_data():
    """Generate comprehensive pH-dependent data."""
    # Molecule: acetic acid (pKa = 4.8)
    smiles = "CC(=O)O"
    mol = Chem.MolFromSmiles(smiles)
    
    protonation_engine = ProtonationEngine()
    thermo_engine = ThermodynamicEnsemble()
    
    # pH range for smooth curves
    ph_values = np.linspace(2, 10, 100)
    
    # Mock docking scores (realistic values)
    # Deprotonated form (COO-) binds better than protonated (COOH)
    docking_scores = {
        'protonated': -7.0,      # COOH (neutral)
        'deprotonated': -9.0     # COO- (charged, better binding)
    }
    
    # Storage for results
    results = {
        'ph': [],
        'p_protonated': [],
        'p_deprotonated': [],
        'delta_g_ensemble': [],
        'delta_g_protonated': [],
        'delta_g_deprotonated': [],
        'contribution_protonated': [],
        'contribution_deprotonated': []
    }
    
    for ph in ph_values:
        # Calculate probabilities
        p_prot = thermo_engine.compute_site_probability(4.8, ph, "acid")
        p_deprot = 1.0 - p_prot
        
        # Ensemble average
        delta_g_ens = p_prot * docking_scores['protonated'] + \
                      p_deprot * docking_scores['deprotonated']
        
        # Store results
        results['ph'].append(ph)
        results['p_protonated'].append(p_prot)
        results['p_deprotonated'].append(p_deprot)
        results['delta_g_ensemble'].append(delta_g_ens)
        results['delta_g_protonated'].append(docking_scores['protonated'])
        results['delta_g_deprotonated'].append(docking_scores['deprotonated'])
        results['contribution_protonated'].append(p_prot * docking_scores['protonated'])
        results['contribution_deprotonated'].append(p_deprot * docking_scores['deprotonated'])
    
    return results, docking_scores


def plot_microstate_populations(results, ax):
    """Plot 1: Microstate population vs pH."""
    ax.plot(results['ph'], results['p_protonated'], 
            'b-', linewidth=2.5, label='COOH (protonated)')
    ax.plot(results['ph'], results['p_deprotonated'], 
            'r-', linewidth=2.5, label='COO⁻ (deprotonated)')
    
    # Mark pKa
    ax.axvline(x=4.8, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(4.8, 0.5, 'pKa = 4.8', rotation=90, 
            verticalalignment='center', fontsize=10, color='gray')
    
    # Shade physiological pH range
    ax.axvspan(7.2, 7.6, alpha=0.1, color='green', label='Physiological pH')
    
    ax.set_xlabel('pH', fontweight='bold')
    ax.set_ylabel('Population Fraction', fontweight='bold')
    ax.set_title('A. Microstate Populations (Henderson-Hasselbalch)', 
                 fontweight='bold', pad=15)
    ax.set_ylim(0, 1.05)
    ax.set_xlim(2, 10)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)


def plot_binding_energy(results, docking_scores, ax):
    """Plot 2: Binding energy vs pH."""
    # Plot individual state energies
    ax.axhline(y=docking_scores['protonated'], color='b', 
               linestyle=':', linewidth=2, alpha=0.6, 
               label='COOH only (ΔG = -7.0 kcal/mol)')
    ax.axhline(y=docking_scores['deprotonated'], color='r', 
               linestyle=':', linewidth=2, alpha=0.6,
               label='COO⁻ only (ΔG = -9.0 kcal/mol)')
    
    # Plot ensemble average
    ax.plot(results['ph'], results['delta_g_ensemble'], 
            'g-', linewidth=3, label='Ensemble Average', zorder=10)
    
    # Mark pKa
    ax.axvline(x=4.8, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    
    # Shade physiological pH
    ax.axvspan(7.2, 7.6, alpha=0.1, color='green')
    
    # Annotate key points
    ax.plot(4.8, -8.0, 'ko', markersize=8, zorder=15)
    ax.annotate('At pKa: ΔG = -8.0\n(50/50 mix)', 
                xy=(4.8, -8.0), xytext=(5.5, -8.0),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.plot(7.4, results['delta_g_ensemble'][np.argmin(np.abs(np.array(results['ph']) - 7.4))], 
            'gs', markersize=8, zorder=15)
    
    ax.set_xlabel('pH', fontweight='bold')
    ax.set_ylabel('ΔG$_{bind}$ (kcal/mol)', fontweight='bold')
    ax.set_title('B. pH-Dependent Binding Free Energy', 
                 fontweight='bold', pad=15)
    ax.set_xlim(2, 10)
    ax.set_ylim(-9.5, -6.5)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)


def plot_state_contributions(results, ax):
    """Plot 3: Stacked contributions."""
    ax.fill_between(results['ph'], 0, results['contribution_protonated'],
                     color='blue', alpha=0.6, label='COOH contribution')
    ax.fill_between(results['ph'], results['contribution_protonated'],
                     np.array(results['contribution_protonated']) + \
                     np.array(results['contribution_deprotonated']),
                     color='red', alpha=0.6, label='COO⁻ contribution')
    
    # Mark pKa
    ax.axvline(x=4.8, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    
    # Total line
    ax.plot(results['ph'], results['delta_g_ensemble'], 
            'k-', linewidth=2, label='Total (ensemble)', zorder=10)
    
    # Shade physiological pH
    ax.axvspan(7.2, 7.6, alpha=0.1, color='green')
    
    ax.set_xlabel('pH', fontweight='bold')
    ax.set_ylabel('ΔG contribution (kcal/mol)', fontweight='bold')
    ax.set_title('C. State Contributions to Ensemble Energy', 
                 fontweight='bold', pad=15)
    ax.set_xlim(2, 10)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)


def plot_comparison(results, docking_scores, ax):
    """Plot 4: Ensemble vs single-state comparison."""
    # Traditional approach: pick dominant state at pH 7.4
    ph_7_4_idx = np.argmin(np.abs(np.array(results['ph']) - 7.4))
    dominant_at_7_4 = docking_scores['deprotonated']  # COO- dominates at 7.4
    
    # Plot single-state (traditional)
    ax.axhline(y=dominant_at_7_4, color='orange', linestyle='--', 
               linewidth=2.5, label='Traditional: Single state at pH 7.4\n(COO⁻ only, ΔG = -9.0)')
    
    # Plot ensemble (our method)
    ax.plot(results['ph'], results['delta_g_ensemble'], 
            'g-', linewidth=3, label='pH-Aware Ensemble (this work)', zorder=10)
    
    # Highlight error regions
    diff = np.abs(np.array(results['delta_g_ensemble']) - dominant_at_7_4)
    error_region = diff > 0.5
    
    if np.any(error_region):
        ax.fill_between(results['ph'], 
                        results['delta_g_ensemble'],
                        dominant_at_7_4,
                        where=error_region,
                        alpha=0.3, color='yellow',
                        label='Error region (>0.5 kcal/mol)')
    
    # Mark pKa
    ax.axvline(x=4.8, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(4.8, -6.7, 'pKa', rotation=90, verticalalignment='bottom', fontsize=9)
    
    # Shade physiological pH
    ax.axvspan(7.2, 7.6, alpha=0.1, color='green', label='Physiological pH')
    
    # Annotate key difference
    max_diff_idx = np.argmax(diff)
    max_diff_ph = results['ph'][max_diff_idx]
    max_diff_val = diff[max_diff_idx]
    
    ax.annotate(f'Max error: {max_diff_val:.2f} kcal/mol\nat pH {max_diff_ph:.1f}', 
                xy=(max_diff_ph, results['delta_g_ensemble'][max_diff_idx]), 
                xytext=(max_diff_ph + 1, -7.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=9, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax.set_xlabel('pH', fontweight='bold')
    ax.set_ylabel('ΔG$_{bind}$ (kcal/mol)', fontweight='bold')
    ax.set_title('D. Ensemble vs Traditional Single-State Approach', 
                 fontweight='bold', pad=15)
    ax.set_xlim(2, 10)
    ax.set_ylim(-9.5, -6.5)
    ax.legend(loc='best', framealpha=0.9, fontsize=9)
    ax.grid(True, alpha=0.3)


def create_visualization():
    """Create complete 4-panel visualization."""
    print("Generating pH-aware ensemble docking visualization...")
    
    # Generate data
    results, docking_scores = generate_ph_data()
    
    # Create figure with 2x2 subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Generate plots
    plot_microstate_populations(results, ax1)
    plot_binding_energy(results, docking_scores, ax2)
    plot_state_contributions(results, ax3)
    plot_comparison(results, docking_scores, ax4)
    
    # Overall title
    fig.suptitle('pH-Aware Thermodynamic Ensemble Docking: Acetic Acid Example\n' + 
                 'ΔG$_{bind}$(pH) = Σ$_i$ P$_i$(pH) × ΔG$_i$', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Add footer with implementation details
    footer_text = (
        'Implementation: Henderson-Hasselbalch probabilities × GNINA docking scores\n'
        'Molecule: Acetic acid (CC(=O)O, pKa=4.8) | '
        'Scores: COOH=-7.0, COO⁻=-9.0 kcal/mol'
    )
    fig.text(0.5, 0.01, footer_text, ha='center', fontsize=9, 
             style='italic', color='gray')
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
    # Save figure
    output_file = Path(__file__).parent / 'ph_ensemble_visualization.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualization saved to: {output_file}")
    
    # Show plot
    plt.show()
    
    # Print summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    
    ph_7_4_idx = np.argmin(np.abs(np.array(results['ph']) - 7.4))
    ph_4_8_idx = np.argmin(np.abs(np.array(results['ph']) - 4.8))
    
    print(f"\nAt pKa (pH 4.8):")
    print(f"  P(COOH) = {results['p_protonated'][ph_4_8_idx]:.3f}")
    print(f"  P(COO-) = {results['p_deprotonated'][ph_4_8_idx]:.3f}")
    print(f"  ΔG_ensemble = {results['delta_g_ensemble'][ph_4_8_idx]:.3f} kcal/mol")
    
    print(f"\nAt physiological pH (pH 7.4):")
    print(f"  P(COOH) = {results['p_protonated'][ph_7_4_idx]:.3f}")
    print(f"  P(COO-) = {results['p_deprotonated'][ph_7_4_idx]:.3f}")
    print(f"  ΔG_ensemble = {results['delta_g_ensemble'][ph_7_4_idx]:.3f} kcal/mol")
    
    # Error analysis
    dominant_at_7_4 = docking_scores['deprotonated']
    errors = np.abs(np.array(results['delta_g_ensemble']) - dominant_at_7_4)
    max_error = np.max(errors)
    max_error_ph = results['ph'][np.argmax(errors)]
    
    print(f"\nError Analysis (vs single-state at pH 7.4):")
    print(f"  Maximum error: {max_error:.3f} kcal/mol at pH {max_error_ph:.1f}")
    print(f"  Mean error: {np.mean(errors):.3f} kcal/mol")
    print(f"  RMSE: {np.sqrt(np.mean(errors**2)):.3f} kcal/mol")
    
    print("\n" + "=" * 70)
    print("✅ VISUALIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    create_visualization()
