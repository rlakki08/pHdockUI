"""
Thermodynamic ensemble aggregation for pH-aware binding energy calculations.

This module implements the core equation:
ΔG_bind(pH) = Σ_i P_i(pH) * ΔG_i

where:
- i = protonation microstate index
- P_i(pH) = probability of microstate i at given pH (from Henderson-Hasselbalch)
- ΔG_i = binding free energy (docking score) for microstate i
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

# Physical constants
GAS_CONSTANT = 1.987e-3  # kcal/(mol·K)
STANDARD_TEMP = 298.15    # K (25°C)


class ThermodynamicEnsemble:
    """
    Compute pH-dependent binding free energies using thermodynamic ensemble averaging.
    
    This class handles:
    1. Microstate probability calculations (Henderson-Hasselbalch)
    2. Ensemble-weighted binding energy aggregation
    3. Boltzmann averaging for advanced scenarios
    """
    
    def __init__(self, temperature: float = STANDARD_TEMP):
        """
        Initialize thermodynamic ensemble calculator.
        
        Args:
            temperature: Temperature in Kelvin (default: 298.15 K)
        """
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)
        
    def compute_site_probability(self, pka: float, ph: float, 
                                 site_type: str = "acid") -> float:
        """
        Compute protonation probability for a single ionizable site.
        
        Uses Henderson-Hasselbalch equation:
        - For acidic sites: P_deprot = 1 / (1 + 10^(pKa - pH))
        - For basic sites: P_prot = 1 / (1 + 10^(pH - pKa))
        
        Args:
            pka: pKa value of the ionizable site
            ph: pH value
            site_type: Type of site ("acid" or "base")
            
        Returns:
            Probability of protonated state (0 to 1)
        """
        if site_type.lower() in ["acid", "acidic", "carboxyl", "phenol", "thiol"]:
            # For acids: deprotonated (COO-) is favored at high pH
            # Return protonated fraction (COOH)
            return 1.0 / (1.0 + 10**(ph - pka))
        else:
            # For bases: protonated (NH3+) is favored at low pH
            # Return protonated fraction (NH3+)
            return 1.0 / (1.0 + 10**(pka - ph))
    
    def compute_microstate_probability(self, microstate: Dict[str, Any], 
                                      pka_sites: List[Dict[str, Any]], 
                                      ph: float) -> float:
        """
        Compute probability of a multi-site microstate.
        
        For independent sites, the microstate probability is the product
        of individual site probabilities.
        
        Args:
            microstate: Dictionary describing protonation state
                       Must contain 'site_states' - list of protonation states per site
            pka_sites: List of dicts with 'pka', 'type' for each ionizable site
            ph: pH value
            
        Returns:
            Probability of this microstate (0 to 1)
        """
        if not pka_sites:
            return 1.0
            
        probability = 1.0
        
        site_states = microstate.get('site_states', [])
        
        for i, site in enumerate(pka_sites):
            pka = site['pka']
            site_type = site.get('type', 'acid')
            
            # Get desired protonation state for this site in this microstate
            is_protonated = site_states[i] if i < len(site_states) else True
            
            # Compute probability of this site being in the desired state
            p_protonated = self.compute_site_probability(pka, ph, site_type)
            
            if is_protonated:
                site_prob = p_protonated
            else:
                site_prob = 1.0 - p_protonated
                
            probability *= site_prob
            
        return probability
    
    def aggregate_binding_energy(self, states: List[Dict[str, Any]], 
                                 docking_results: List[Dict[str, Any]]) -> float:
        """
        Compute ensemble-weighted binding free energy.
        
        Implements: ΔG_bind(pH) = Σ_i P_i(pH) * ΔG_i
        
        Args:
            states: List of protonation states, each with:
                   - state_id: unique identifier
                   - probability: P_i(pH) value (0 to 1)
            docking_results: List of docking results, each with:
                            - state_id: matching identifier
                            - delta_g: binding free energy (kcal/mol)
                            
        Returns:
            Ensemble-weighted binding free energy (kcal/mol)
        """
        # Create mapping from state_id to delta_g
        docking_map = {
            r["state_id"]: r["delta_g"]
            for r in docking_results
        }
        
        # Compute weighted sum
        delta_g_bind = 0.0
        total_probability = 0.0
        
        for state in states:
            state_id = state["state_id"]
            probability = state["probability"]
            
            if state_id not in docking_map:
                self.logger.warning(f"No docking result for state {state_id}, skipping")
                continue
                
            delta_g_i = docking_map[state_id]
            
            # Weighted contribution
            delta_g_bind += probability * delta_g_i
            total_probability += probability
            
        # Normalize if probabilities don't sum to 1 (numerical issues)
        if total_probability > 0 and abs(total_probability - 1.0) > 1e-6:
            self.logger.warning(
                f"Probabilities sum to {total_probability:.4f}, normalizing"
            )
            delta_g_bind /= total_probability
            
        return delta_g_bind
    
    def boltzmann_average_binding_energy(self, states: List[Dict[str, Any]], 
                                        docking_results: List[Dict[str, Any]]) -> float:
        """
        Compute Boltzmann-weighted binding free energy (advanced).
        
        Implements: ΔG_bind = -RT ln(Σ_i P_i exp(-ΔG_i/RT))
        
        This is more rigorous than simple weighted average but requires
        docking scores to be on a free energy scale.
        
        Args:
            states: List of protonation states with probabilities
            docking_results: List of docking results with delta_g
            
        Returns:
            Boltzmann-weighted binding free energy (kcal/mol)
        """
        docking_map = {
            r["state_id"]: r["delta_g"]
            for r in docking_results
        }
        
        rt = GAS_CONSTANT * self.temperature
        
        # Compute Boltzmann sum
        boltzmann_sum = 0.0
        
        for state in states:
            state_id = state["state_id"]
            probability = state["probability"]
            
            if state_id not in docking_map:
                continue
                
            delta_g_i = docking_map[state_id]
            
            # Boltzmann factor: exp(-ΔG/RT)
            boltzmann_factor = np.exp(-delta_g_i / rt)
            boltzmann_sum += probability * boltzmann_factor
            
        if boltzmann_sum <= 0:
            self.logger.error("Invalid Boltzmann sum, returning NaN")
            return np.nan
            
        # Free energy from partition function
        delta_g_bind = -rt * np.log(boltzmann_sum)
        
        return delta_g_bind
    
    def compute_ph_titration_curve(self, states_by_ph: Dict[float, List[Dict[str, Any]]], 
                                   docking_results_by_ph: Dict[float, List[Dict[str, Any]]],
                                   use_boltzmann: bool = False) -> pd.DataFrame:
        """
        Compute binding energy across pH range (titration curve).
        
        Args:
            states_by_ph: Dict mapping pH -> list of protonation states
            docking_results_by_ph: Dict mapping pH -> list of docking results
            use_boltzmann: Use Boltzmann averaging instead of linear weighting
            
        Returns:
            DataFrame with columns: pH, delta_g_bind, num_states
        """
        results = []
        
        for ph in sorted(states_by_ph.keys()):
            states = states_by_ph[ph]
            docking_results = docking_results_by_ph.get(ph, [])
            
            if use_boltzmann:
                delta_g = self.boltzmann_average_binding_energy(states, docking_results)
            else:
                delta_g = self.aggregate_binding_energy(states, docking_results)
                
            results.append({
                'pH': ph,
                'delta_g_bind': delta_g,
                'num_states': len(states),
                'method': 'boltzmann' if use_boltzmann else 'weighted_average'
            })
            
        return pd.DataFrame(results)
    
    def compute_state_contributions(self, states: List[Dict[str, Any]], 
                                   docking_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Analyze individual microstate contributions to ensemble average.
        
        Useful for understanding which protonation states dominate binding.
        
        Args:
            states: List of protonation states
            docking_results: List of docking results
            
        Returns:
            DataFrame with per-state analysis
        """
        docking_map = {
            r["state_id"]: r["delta_g"]
            for r in docking_results
        }
        
        contributions = []
        
        for state in states:
            state_id = state["state_id"]
            probability = state["probability"]
            
            if state_id not in docking_map:
                continue
                
            delta_g_i = docking_map[state_id]
            contribution = probability * delta_g_i
            
            contributions.append({
                'state_id': state_id,
                'probability': probability,
                'delta_g': delta_g_i,
                'contribution': contribution,
                'charge': state.get('charge', 0),
                'smiles': state.get('smiles', '')
            })
            
        df = pd.DataFrame(contributions)
        
        # Sort by absolute contribution
        if len(df) > 0:
            df = df.sort_values('probability', ascending=False)
            
        return df


def aggregate_binding_energy(states: List[Dict[str, Any]], 
                             docking_results: List[Dict[str, Any]],
                             temperature: float = STANDARD_TEMP) -> float:
    """
    Convenience function for simple ensemble aggregation.
    
    Args:
        states: List of protonation states with probabilities
        docking_results: List of docking results
        temperature: Temperature in Kelvin
        
    Returns:
        Ensemble-weighted binding free energy (kcal/mol)
    """
    ensemble = ThermodynamicEnsemble(temperature=temperature)
    return ensemble.aggregate_binding_energy(states, docking_results)


def compute_ph_binding_curve(states_by_ph: Dict[float, List[Dict[str, Any]]], 
                             docking_results_by_ph: Dict[float, List[Dict[str, Any]]],
                             use_boltzmann: bool = False,
                             temperature: float = STANDARD_TEMP) -> pd.DataFrame:
    """
    Convenience function for computing pH-dependent binding curve.
    
    Args:
        states_by_ph: Dict mapping pH to protonation states
        docking_results_by_ph: Dict mapping pH to docking results
        use_boltzmann: Use Boltzmann averaging
        temperature: Temperature in Kelvin
        
    Returns:
        DataFrame with pH titration curve
    """
    ensemble = ThermodynamicEnsemble(temperature=temperature)
    return ensemble.compute_ph_titration_curve(
        states_by_ph, 
        docking_results_by_ph, 
        use_boltzmann=use_boltzmann
    )


if __name__ == "__main__":
    # Example usage and validation
    logging.basicConfig(level=logging.INFO)
    
    # Example: Two-state system (protonated vs deprotonated)
    # Single acidic site with pKa = 7.0 at pH 7.4
    
    print("=== Example 1: Simple two-state system ===")
    
    ensemble = ThermodynamicEnsemble()
    
    # Compute probabilities at pH 7.4 for pKa 7.0 acid
    ph = 7.4
    pka = 7.0
    
    p_protonated = ensemble.compute_site_probability(pka, ph, "acid")
    p_deprotonated = 1.0 - p_protonated
    
    print(f"pH {ph}, pKa {pka} (acid):")
    print(f"  P(COOH) = {p_protonated:.3f}")
    print(f"  P(COO-) = {p_deprotonated:.3f}")
    
    # Mock protonation states
    states = [
        {"state_id": 0, "probability": p_protonated, "charge": 0, "smiles": "COOH"},
        {"state_id": 1, "probability": p_deprotonated, "charge": -1, "smiles": "COO-"}
    ]
    
    # Mock docking results (state 1 binds better)
    docking_results = [
        {"state_id": 0, "delta_g": -7.0},  # Neutral form
        {"state_id": 1, "delta_g": -9.0}   # Charged form binds better
    ]
    
    # Compute ensemble average
    delta_g_ensemble = ensemble.aggregate_binding_energy(states, docking_results)
    
    print(f"\nDocking scores:")
    print(f"  State 0 (COOH): {docking_results[0]['delta_g']} kcal/mol")
    print(f"  State 1 (COO-): {docking_results[1]['delta_g']} kcal/mol")
    print(f"  Ensemble average: {delta_g_ensemble:.2f} kcal/mol")
    
    # Analyze contributions
    contributions = ensemble.compute_state_contributions(states, docking_results)
    print("\nState contributions:")
    print(contributions.to_string(index=False))
    
    print("\n=== Example 2: pH titration curve ===")
    
    # Compute binding across pH range
    ph_values = [5.0, 6.0, 7.0, 7.4, 8.0, 9.0]
    states_by_ph = {}
    docking_results_by_ph = {}
    
    for ph_val in ph_values:
        p_prot = ensemble.compute_site_probability(pka, ph_val, "acid")
        p_deprot = 1.0 - p_prot
        
        states_by_ph[ph_val] = [
            {"state_id": 0, "probability": p_prot, "charge": 0},
            {"state_id": 1, "probability": p_deprot, "charge": -1}
        ]
        
        docking_results_by_ph[ph_val] = docking_results
    
    curve = ensemble.compute_ph_titration_curve(states_by_ph, docking_results_by_ph)
    print("\npH-dependent binding energy:")
    print(curve.to_string(index=False))
    
    print("\n=== Example 3: Boltzmann vs weighted average ===")
    
    curve_boltzmann = ensemble.compute_ph_titration_curve(
        states_by_ph, docking_results_by_ph, use_boltzmann=True
    )
    
    comparison = pd.DataFrame({
        'pH': curve['pH'],
        'weighted_avg': curve['delta_g_bind'],
        'boltzmann': curve_boltzmann['delta_g_bind'],
        'difference': curve['delta_g_bind'] - curve_boltzmann['delta_g_bind']
    })
    
    print("\nComparison of methods:")
    print(comparison.to_string(index=False))
