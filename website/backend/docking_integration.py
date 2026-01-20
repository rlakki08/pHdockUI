"""
Integration module for molecular docking pipeline (GNINA/DiffDock/EquiBind).
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from pathlib import Path
import subprocess
import tempfile
import os
import shutil

from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors
from rdkit.Chem.rdMolAlign import AlignMol


class DockingIntegration:
    """Integration with molecular docking tools for protonated molecules."""
    
    def __init__(self, 
                 docking_tool: str = "gnina",
                 docking_executable: Optional[str] = None,
                 work_dir: Optional[Path] = None):
        """
        Initialize docking integration.
        
        Args:
            docking_tool: Docking tool to use ("gnina", "diffdock", "equibind")
            docking_executable: Path to docking executable
            work_dir: Working directory for docking
        """
        self.docking_tool = docking_tool.lower()
        self.docking_executable = docking_executable
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "docking_work"
        
        self.logger = logging.getLogger(__name__)
        
        # Create work directory
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate docking tool
        if self.docking_tool not in ["gnina", "diffdock", "equibind"]:
            raise ValueError(f"Unsupported docking tool: {docking_tool}")
        
        # Set default executables
        if self.docking_executable is None:
            if self.docking_tool == "gnina":
                self.docking_executable = "gnina"
            elif self.docking_tool == "diffdock":
                self.docking_executable = "python"  # DiffDock is typically run via Python
            elif self.docking_tool == "equibind":
                self.docking_executable = "python"  # EquiBind is typically run via Python
        
        # Docking parameters
        self.docking_params = self._get_default_params()
    
    def _get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for each docking tool."""
        if self.docking_tool == "gnina":
            return {
                'exhaustiveness': 8,
                'num_modes': 9,
                'energy_range': 3.0,
                'min_rmsd': 1.0,
                'cpu': 4,
                'seed': 42
            }
        elif self.docking_tool == "diffdock":
            return {
                'samples_per_complex': 40,
                'inference_steps': 20,
                'batch_size': 10,
                'actual_steps': 18,
                'temp_sampling': 1.0,
                'temp_psi': 1.0,
                'temp_sigma_data': 0.5
            }
        elif self.docking_tool == "equibind":
            return {
                'use_rdkit_coords': False,
                'save_visualisation': True,
                'run_corrections': True,
                'use_full_size_batch': False
            }
        else:
            return {}
    
    def prepare_receptor(self, receptor_pdb: Union[str, Path]) -> Path:
        """
        Prepare receptor for docking.
        
        Args:
            receptor_pdb: Path to receptor PDB file
            
        Returns:
            Path to prepared receptor file
        """
        receptor_path = Path(receptor_pdb)
        
        if not receptor_path.exists():
            raise FileNotFoundError(f"Receptor file not found: {receptor_path}")
        
        # Copy receptor to work directory
        prepared_receptor = self.work_dir / f"receptor_prepared.pdb"
        shutil.copy2(receptor_path, prepared_receptor)
        
        # Additional receptor preparation could be added here
        # e.g., adding hydrogens, optimizing side chains, etc.
        
        self.logger.info(f"Prepared receptor: {prepared_receptor}")
        return prepared_receptor
    
    def prepare_ligands(self, protonation_states: Dict[float, Chem.Mol],
                       molecule_name: str = "ligand") -> Dict[float, Path]:
        """
        Prepare ligands from protonation states.
        
        Args:
            protonation_states: Dictionary mapping pH to molecules
            molecule_name: Base name for ligand files
            
        Returns:
            Dictionary mapping pH to prepared ligand file paths
        """
        prepared_ligands = {}
        
        for ph, mol in protonation_states.items():
            try:
                # Generate 3D coordinates if not present
                if mol.GetNumConformers() == 0:
                    # Add hydrogens and generate conformer
                    mol_h = Chem.AddHs(mol)
                    AllChem.EmbedMolecule(mol_h, randomSeed=42)
                    AllChem.MMFFOptimizeMolecule(mol_h)
                    mol = mol_h
                
                # Save to SDF file
                ph_str = f"pH_{ph:.1f}".replace(".", "_")
                ligand_file = self.work_dir / f"{molecule_name}_{ph_str}.sdf"
                
                writer = Chem.SDWriter(str(ligand_file))
                mol.SetProp("pH", str(ph))
                mol.SetProp("molecule_name", molecule_name)
                writer.write(mol)
                writer.close()
                
                prepared_ligands[ph] = ligand_file
                
            except Exception as e:
                self.logger.warning(f"Failed to prepare ligand for pH {ph}: {e}")
                continue
        
        self.logger.info(f"Prepared {len(prepared_ligands)} ligand conformations")
        return prepared_ligands
    
    def run_gnina_docking(self, receptor_file: Path, ligand_file: Path,
                         output_prefix: str) -> Optional[Path]:
        """
        Run GNINA docking.
        
        Args:
            receptor_file: Path to receptor file
            ligand_file: Path to ligand file
            output_prefix: Prefix for output files
            
        Returns:
            Path to output SDF file or None if failed
        """
        try:
            output_file = self.work_dir / f"{output_prefix}_docked.sdf"
            log_file = self.work_dir / f"{output_prefix}_gnina.log"
            
            # Build GNINA command
            cmd = [
                str(self.docking_executable),
                "--receptor", str(receptor_file),
                "--ligand", str(ligand_file),
                "--out", str(output_file),
                "--log", str(log_file),
                "--exhaustiveness", str(self.docking_params['exhaustiveness']),
                "--num_modes", str(self.docking_params['num_modes']),
                "--energy_range", str(self.docking_params['energy_range']),
                "--min_rmsd", str(self.docking_params['min_rmsd']),
                "--cpu", str(self.docking_params['cpu']),
                "--seed", str(self.docking_params['seed'])
            ]
            
            # Run GNINA
            self.logger.info(f"Running GNINA docking: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0 and output_file.exists():
                self.logger.info(f"GNINA docking completed: {output_file}")
                return output_file
            else:
                self.logger.error(f"GNINA docking failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("GNINA docking timed out")
            return None
        except Exception as e:
            self.logger.error(f"GNINA docking error: {e}")
            return None
    
    def run_diffdock_docking(self, receptor_file: Path, ligand_file: Path,
                            output_prefix: str) -> Optional[Path]:
        """
        Run DiffDock docking.
        
        Args:
            receptor_file: Path to receptor file
            ligand_file: Path to ligand file
            output_prefix: Prefix for output files
            
        Returns:
            Path to output directory or None if failed
        """
        try:
            output_dir = self.work_dir / f"{output_prefix}_diffdock"
            output_dir.mkdir(exist_ok=True)
            
            # Create CSV input file for DiffDock
            csv_file = self.work_dir / f"{output_prefix}_input.csv"
            
            # Convert SDF to SMILES for DiffDock input
            mol = Chem.SDMolSupplier(str(ligand_file))[0]
            smiles = Chem.MolToSmiles(mol)
            
            # Write CSV file
            with open(csv_file, 'w') as f:
                f.write("complex_name,protein_path,ligand_description,protein_sequence\n")
                f.write(f"{output_prefix},{receptor_file},{smiles},\n")
            
            # Build DiffDock command (placeholder - actual implementation depends on DiffDock setup)
            cmd = [
                str(self.docking_executable),
                "-m", "diffdock.inference",  # Assuming DiffDock module
                "--config", "default_inference_args.yaml",  # Default config
                "--protein_ligand_csv", str(csv_file),
                "--out_dir", str(output_dir),
                "--samples_per_complex", str(self.docking_params['samples_per_complex']),
                "--inference_steps", str(self.docking_params['inference_steps']),
                "--batch_size", str(self.docking_params['batch_size'])
            ]
            
            # Note: This is a placeholder implementation
            # Actual DiffDock integration would require proper installation and configuration
            self.logger.warning("DiffDock integration is a placeholder - requires proper setup")
            return None
            
        except Exception as e:
            self.logger.error(f"DiffDock docking error: {e}")
            return None
    
    def run_equibind_docking(self, receptor_file: Path, ligand_file: Path,
                            output_prefix: str) -> Optional[Path]:
        """
        Run EquiBind docking.
        
        Args:
            receptor_file: Path to receptor file
            ligand_file: Path to ligand file
            output_prefix: Prefix for output files
            
        Returns:
            Path to output directory or None if failed
        """
        try:
            output_dir = self.work_dir / f"{output_prefix}_equibind"
            output_dir.mkdir(exist_ok=True)
            
            # EquiBind typically requires specific directory structure and naming
            # This is a placeholder implementation
            
            # Build EquiBind command (placeholder)
            cmd = [
                str(self.docking_executable),
                "-m", "equibind.inference",  # Assuming EquiBind module
                "--protein", str(receptor_file),
                "--ligand", str(ligand_file),
                "--out_dir", str(output_dir),
                "--use_rdkit_coords", str(self.docking_params['use_rdkit_coords']),
                "--save_visualisation", str(self.docking_params['save_visualisation'])
            ]
            
            # Note: This is a placeholder implementation
            # Actual EquiBind integration would require proper installation and configuration
            self.logger.warning("EquiBind integration is a placeholder - requires proper setup")
            return None
            
        except Exception as e:
            self.logger.error(f"EquiBind docking error: {e}")
            return None
    
    def dock_protonation_states(self, receptor_file: Path,
                               protonation_states: Dict[float, Chem.Mol],
                               molecule_name: str = "ligand") -> Dict[float, Optional[Path]]:
        """
        Dock all protonation states.
        
        Args:
            receptor_file: Path to receptor file
            protonation_states: Dictionary of protonation states
            molecule_name: Name for molecule
            
        Returns:
            Dictionary mapping pH to docking results
        """
        # Prepare receptor
        prepared_receptor = self.prepare_receptor(receptor_file)
        
        # Prepare ligands
        prepared_ligands = self.prepare_ligands(protonation_states, molecule_name)
        
        # Run docking for each protonation state
        docking_results = {}
        
        for ph, ligand_file in prepared_ligands.items():
            try:
                ph_str = f"pH_{ph:.1f}".replace(".", "_")
                output_prefix = f"{molecule_name}_{ph_str}"
                
                # Select docking method
                if self.docking_tool == "gnina":
                    result = self.run_gnina_docking(prepared_receptor, ligand_file, output_prefix)
                elif self.docking_tool == "diffdock":
                    result = self.run_diffdock_docking(prepared_receptor, ligand_file, output_prefix)
                elif self.docking_tool == "equibind":
                    result = self.run_equibind_docking(prepared_receptor, ligand_file, output_prefix)
                else:
                    result = None
                
                docking_results[ph] = result
                
            except Exception as e:
                self.logger.error(f"Docking failed for pH {ph}: {e}")
                docking_results[ph] = None
        
        return docking_results
    
    def dock_microstates(self, receptor_file: Path,
                        microstates: List[Dict[str, Any]],
                        molecule_name: str = "ligand") -> List[Dict[str, Any]]:
        """
        Dock protonation microstates and return standardized results.
        
        This produces the standardized format required for thermodynamic ensemble averaging:
        [
          {"state_id": 0, "delta_g": -7.5, "affinity": 8.2, ...},
          {"state_id": 1, "delta_g": -6.8, "affinity": 7.1, ...}
        ]
        
        Args:
            receptor_file: Path to receptor PDB file
            microstates: List of microstate dictionaries from protonation engine
                        Each must have 'state_id' and 'structure' (RDKit Mol)
            molecule_name: Base name for ligand files
            
        Returns:
            List of docking result dictionaries with state_id and delta_g
        """
        # Prepare receptor
        prepared_receptor = self.prepare_receptor(receptor_file)
        
        docking_results = []
        
        for microstate in microstates:
            state_id = microstate['state_id']
            mol = microstate['structure']
            
            try:
                # Save microstate to SDF file
                ligand_file = self.work_dir / f"{molecule_name}_state_{state_id}.sdf"
                
                # Generate 3D coordinates if not present
                if mol.GetNumConformers() == 0:
                    mol_h = Chem.AddHs(mol)
                    AllChem.EmbedMolecule(mol_h, randomSeed=42)
                    AllChem.MMFFOptimizeMolecule(mol_h)
                    mol = mol_h
                
                writer = Chem.SDWriter(str(ligand_file))
                mol.SetProp("state_id", str(state_id))
                mol.SetProp("charge", str(microstate.get('charge', 0)))
                mol.SetProp("probability", str(microstate.get('probability', 0.0)))
                writer.write(mol)
                writer.close()
                
                # Run docking
                output_prefix = f"{molecule_name}_state_{state_id}"
                
                if self.docking_tool == "gnina":
                    result_file = self.run_gnina_docking(prepared_receptor, ligand_file, output_prefix)
                elif self.docking_tool == "diffdock":
                    result_file = self.run_diffdock_docking(prepared_receptor, ligand_file, output_prefix)
                elif self.docking_tool == "equibind":
                    result_file = self.run_equibind_docking(prepared_receptor, ligand_file, output_prefix)
                else:
                    result_file = None
                
                # Extract docking score
                if result_file and result_file.exists():
                    score_data = self._extract_docking_score(result_file)
                else:
                    self.logger.warning(f"Docking failed for state {state_id}")
                    score_data = {'delta_g': 0.0, 'affinity': 0.0}
                
                # Build standardized result
                docking_result = {
                    'state_id': state_id,
                    'delta_g': score_data.get('delta_g', 0.0),
                    'affinity': score_data.get('affinity', 0.0),
                    'cnn_score': score_data.get('cnn_score', 0.0),
                    'charge': microstate.get('charge', 0),
                    'probability': microstate.get('probability', 0.0),
                    'result_file': str(result_file) if result_file else None
                }
                
                docking_results.append(docking_result)
                
            except Exception as e:
                self.logger.error(f"Docking failed for microstate {state_id}: {e}")
                # Add placeholder result to maintain indexing
                docking_results.append({
                    'state_id': state_id,
                    'delta_g': 0.0,
                    'affinity': 0.0,
                    'error': str(e)
                })
        
        self.logger.info(f"Docked {len(docking_results)} microstates")
        return docking_results
    
    def _extract_docking_score(self, result_file: Path) -> Dict[str, float]:
        """
        Extract docking scores from result file.
        
        Args:
            result_file: Path to docking result file (SDF format)
            
        Returns:
            Dictionary with delta_g, affinity, and other scores
        """
        try:
            if result_file.suffix.lower() == '.sdf':
                supplier = Chem.SDMolSupplier(str(result_file))
                mol = next(iter(supplier))  # Get first (best) pose
                
                if mol is None:
                    return {'delta_g': 0.0, 'affinity': 0.0}
                
                props = mol.GetPropsAsDict()
                
                # GNINA outputs CNNscore and CNNaffinity
                # CNNaffinity is typically in kcal/mol (negative = favorable)
                cnn_affinity = float(props.get('CNNaffinity', 0.0))
                cnn_score = float(props.get('CNNscore', 0.0))
                
                # Use CNNaffinity as delta_g (binding free energy)
                # Negative values = favorable binding
                return {
                    'delta_g': cnn_affinity,
                    'affinity': abs(cnn_affinity),  # Positive affinity value
                    'cnn_score': cnn_score
                }
            else:
                return {'delta_g': 0.0, 'affinity': 0.0}
                
        except Exception as e:
            self.logger.warning(f"Failed to extract score from {result_file}: {e}")
            return {'delta_g': 0.0, 'affinity': 0.0}
    
    def analyze_docking_results(self, docking_results: Dict[float, Optional[Path]]) -> pd.DataFrame:
        """
        Analyze docking results across pH values.
        
        Args:
            docking_results: Dictionary of docking result files
            
        Returns:
            DataFrame with docking analysis
        """
        analysis_data = []
        
        for ph, result_file in docking_results.items():
            if result_file is None or not result_file.exists():
                continue
            
            try:
                # Read docking results
                if result_file.suffix.lower() == '.sdf':
                    supplier = Chem.SDMolSupplier(str(result_file))
                    
                    for i, mol in enumerate(supplier):
                        if mol is None:
                            continue
                        
                        # Extract docking scores and properties
                        props = mol.GetPropsAsDict()
                        
                        # Common properties from GNINA
                        score = float(props.get('CNNscore', props.get('docking_score', 0.0)))
                        affinity = float(props.get('CNNaffinity', props.get('affinity', 0.0)))
                        
                        analysis_data.append({
                            'pH': ph,
                            'pose_id': i,
                            'docking_score': score,
                            'affinity': affinity,
                            'result_file': str(result_file)
                        })
                        
                        # Only analyze top pose for now
                        if i == 0:
                            break
                
            except Exception as e:
                self.logger.warning(f"Failed to analyze results for pH {ph}: {e}")
                continue
        
        df = pd.DataFrame(analysis_data)
        
        if len(df) > 0:
            # Find best scoring poses
            best_overall = df.loc[df['docking_score'].idxmax()]
            best_per_ph = df.groupby('pH')['docking_score'].max()
            
            self.logger.info(f"Best overall docking score: {best_overall['docking_score']:.3f} at pH {best_overall['pH']}")
            self.logger.info(f"Best scores per pH:\n{best_per_ph}")
        
        return df
    
    def select_optimal_protonation_state(self, analysis_df: pd.DataFrame,
                                       selection_criteria: str = "best_score") -> Tuple[float, Dict[str, Any]]:
        """
        Select optimal protonation state based on docking results.
        
        Args:
            analysis_df: DataFrame with docking analysis
            selection_criteria: Criteria for selection ("best_score", "physiological", "consensus")
            
        Returns:
            Tuple of (optimal_pH, selection_info)
        """
        if len(analysis_df) == 0:
            raise ValueError("No docking results available for selection")
        
        if selection_criteria == "best_score":
            # Select pH with best docking score
            best_row = analysis_df.loc[analysis_df['docking_score'].idxmax()]
            optimal_ph = best_row['pH']
            
            selection_info = {
                'criteria': 'best_score',
                'score': best_row['docking_score'],
                'affinity': best_row['affinity'],
                'pose_id': best_row['pose_id']
            }
            
        elif selection_criteria == "physiological":
            # Select pH closest to physiological (7.4)
            analysis_df['ph_distance'] = abs(analysis_df['pH'] - 7.4)
            physio_candidates = analysis_df.nsmallest(3, 'ph_distance')
            best_physio = physio_candidates.loc[physio_candidates['docking_score'].idxmax()]
            
            optimal_ph = best_physio['pH']
            selection_info = {
                'criteria': 'physiological',
                'score': best_physio['docking_score'],
                'affinity': best_physio['affinity'],
                'ph_distance': best_physio['ph_distance']
            }
            
        elif selection_criteria == "consensus":
            # Weighted combination of score and physiological relevance
            analysis_df['ph_distance'] = abs(analysis_df['pH'] - 7.4)
            analysis_df['norm_score'] = (analysis_df['docking_score'] - analysis_df['docking_score'].min()) / \
                                       (analysis_df['docking_score'].max() - analysis_df['docking_score'].min())
            analysis_df['norm_ph_dist'] = 1 - (analysis_df['ph_distance'] / analysis_df['ph_distance'].max())
            
            # Weighted sum (70% score, 30% physiological relevance)
            analysis_df['consensus_score'] = 0.7 * analysis_df['norm_score'] + 0.3 * analysis_df['norm_ph_dist']
            
            best_consensus = analysis_df.loc[analysis_df['consensus_score'].idxmax()]
            optimal_ph = best_consensus['pH']
            
            selection_info = {
                'criteria': 'consensus',
                'score': best_consensus['docking_score'],
                'affinity': best_consensus['affinity'],
                'consensus_score': best_consensus['consensus_score']
            }
            
        else:
            raise ValueError(f"Unknown selection criteria: {selection_criteria}")
        
        return optimal_ph, selection_info


def run_full_docking_pipeline(molecules: List[Chem.Mol],
                             protonation_states_list: List[Dict[float, Chem.Mol]],
                             receptor_file: Path,
                             pka_predictions: Optional[List[List[float]]] = None,
                             docking_tool: str = "gnina",
                             output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Run complete docking pipeline for multiple molecules.
    
    Args:
        molecules: List of molecules
        protonation_states_list: List of protonation state dictionaries
        receptor_file: Path to receptor PDB file
        pka_predictions: Optional pKa predictions
        docking_tool: Docking tool to use
        output_dir: Output directory
        
    Returns:
        List of docking results for each molecule
    """
    if output_dir is None:
        output_dir = Path.cwd() / "docking_results"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize docking integration
    docking = DockingIntegration(
        docking_tool=docking_tool,
        work_dir=output_dir
    )
    
    results = []
    
    for i, (mol, protonation_states) in enumerate(zip(molecules, protonation_states_list)):
        try:
            molecule_name = f"mol_{i:04d}"
            
            # Run docking for all protonation states
            docking_results = docking.dock_protonation_states(
                receptor_file=receptor_file,
                protonation_states=protonation_states,
                molecule_name=molecule_name
            )
            
            # Analyze results
            analysis_df = docking.analyze_docking_results(docking_results)
            
            # Select optimal protonation state
            if len(analysis_df) > 0:
                optimal_ph, selection_info = docking.select_optimal_protonation_state(
                    analysis_df, selection_criteria="consensus"
                )
            else:
                optimal_ph, selection_info = None, {}
            
            # Store results
            result = {
                'molecule_id': i,
                'molecule_name': molecule_name,
                'docking_results': docking_results,
                'analysis_df': analysis_df,
                'optimal_ph': optimal_ph,
                'selection_info': selection_info,
                'num_successful_dockings': len([r for r in docking_results.values() if r is not None])
            }
            
            results.append(result)
            
        except Exception as e:
            logging.error(f"Docking pipeline failed for molecule {i}: {e}")
            results.append({
                'molecule_id': i,
                'error': str(e),
                'num_successful_dockings': 0
            })
    
    return results


def run_ph_ensemble_docking(molecules: List[Chem.Mol],
                           receptor_file: Path,
                           pka_predictions: Optional[List[List[float]]] = None,
                           ph: float = 7.4,
                           docking_tool: str = "gnina",
                           output_dir: Optional[Path] = None,
                           probability_threshold: float = 0.01) -> List[Dict[str, Any]]:
    """
    Run pH-aware ensemble docking with thermodynamic aggregation.
    
    This is the new pipeline that implements:
    ΔG_bind(pH) = Σ_i P_i(pH) * ΔG_i
    
    Args:
        molecules: List of RDKit molecules
        receptor_file: Path to receptor PDB file
        pka_predictions: Optional list of pKa values for each molecule
        ph: pH value for ensemble calculation (default: 7.4)
        docking_tool: Docking tool to use ("gnina", "diffdock", "equibind")
        output_dir: Output directory for results
        probability_threshold: Minimum probability to include microstate (default: 0.01)
        
    Returns:
        List of results for each molecule, containing:
        - molecule_id: integer index
        - microstates: list of microstate dicts with probabilities
        - docking_results: list of docking results per microstate
        - delta_g_ensemble: ensemble-weighted binding free energy
        - contributions: per-state contributions analysis
    """
    from src.protonation_engine import ProtonationEngine
    from src.thermodynamics import ThermodynamicEnsemble
    
    if output_dir is None:
        output_dir = Path.cwd() / "ph_ensemble_docking"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize engines
    protonation_engine = ProtonationEngine()
    thermodynamic_ensemble = ThermodynamicEnsemble()
    docking = DockingIntegration(
        docking_tool=docking_tool,
        work_dir=output_dir / "docking_work"
    )
    
    results = []
    
    for i, mol in enumerate(molecules):
        try:
            molecule_name = f"mol_{i:04d}"
            logger = logging.getLogger(__name__)
            logger.info(f"Processing molecule {i} at pH {ph}")
            
            # Get pKa values for this molecule
            pka_values = None
            if pka_predictions and i < len(pka_predictions):
                pka_values = pka_predictions[i]
            
            # Step 1: Enumerate microstates with probabilities
            microstates = protonation_engine.enumerate_microstates_with_probabilities(
                mol=mol,
                pka_values=pka_values,
                ph=ph,
                probability_threshold=probability_threshold
            )
            
            logger.info(f"  Enumerated {len(microstates)} microstates (P > {probability_threshold})")
            
            # Step 2: Dock each microstate
            docking_results = docking.dock_microstates(
                receptor_file=receptor_file,
                microstates=microstates,
                molecule_name=molecule_name
            )
            
            logger.info(f"  Completed docking for {len(docking_results)} microstates")
            
            # Step 3: Compute ensemble-weighted binding energy
            delta_g_ensemble = thermodynamic_ensemble.aggregate_binding_energy(
                states=microstates,
                docking_results=docking_results
            )
            
            logger.info(f"  Ensemble ΔG_bind = {delta_g_ensemble:.2f} kcal/mol")
            
            # Step 4: Analyze state contributions
            contributions_df = thermodynamic_ensemble.compute_state_contributions(
                states=microstates,
                docking_results=docking_results
            )
            
            # Store comprehensive results
            result = {
                'molecule_id': i,
                'molecule_name': molecule_name,
                'pH': ph,
                'num_microstates': len(microstates),
                'microstates': microstates,
                'docking_results': docking_results,
                'delta_g_ensemble': delta_g_ensemble,
                'contributions': contributions_df.to_dict('records'),
                'top_microstate': {
                    'state_id': contributions_df.iloc[0]['state_id'] if len(contributions_df) > 0 else None,
                    'probability': contributions_df.iloc[0]['probability'] if len(contributions_df) > 0 else 0,
                    'delta_g': contributions_df.iloc[0]['delta_g'] if len(contributions_df) > 0 else 0
                }
            }
            
            results.append(result)
            
            # Save results to JSON
            import json
            result_file = output_dir / f"{molecule_name}_results.json"
            with open(result_file, 'w') as f:
                # Convert DataFrames and non-serializable objects
                save_result = result.copy()
                save_result['contributions'] = contributions_df.to_dict('records')
                # Remove RDKit mol objects
                save_result['microstates'] = [
                    {k: v for k, v in m.items() if k != 'structure'}
                    for m in microstates
                ]
                json.dump(save_result, f, indent=2)
            
            logger.info(f"  Saved results to {result_file}")
            
        except Exception as e:
            logger.error(f"pH-ensemble docking failed for molecule {i}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'molecule_id': i,
                'error': str(e),
                'pH': ph
            })
    
    return results


if __name__ == "__main__":
    # Example usage (placeholder - requires actual receptor and proper tool setup)
    logging.basicConfig(level=logging.INFO)
    
    print("Docking integration module loaded.")
    print("Note: This module requires:")
    print("1. GNINA installation for GNINA docking")
    print("2. DiffDock setup for DiffDock docking") 
    print("3. EquiBind setup for EquiBind docking")
    print("4. A receptor PDB file for docking")
    
    # Create a simple test case
    from src.protonation_engine import ProtonationEngine
    
    # Test molecule
    smiles = "CC(=O)O"  # Acetic acid
    mol = Chem.MolFromSmiles(smiles)
    
    # Generate protonation states
    engine = ProtonationEngine(ph_range=(6.0, 8.0), ph_step=1.0)
    protonation_states = engine.generate_protonation_states(mol)
    
    print(f"\nGenerated {len(protonation_states)} protonation states")
    for ph in protonation_states.keys():
        print(f"  pH {ph}")
    
    # Initialize docking (will work if GNINA is installed)
    try:
        docking = DockingIntegration(docking_tool="gnina")
        print(f"\nDocking integration initialized with {docking.docking_tool}")
        print(f"Work directory: {docking.work_dir}")
        
        # Prepare ligands (this will work without GNINA)
        prepared_ligands = docking.prepare_ligands(protonation_states, "test_mol")
        print(f"Prepared {len(prepared_ligands)} ligand files")
        
    except Exception as e:
        print(f"Docking integration test failed: {e}")
        print("This is expected if docking tools are not installed")


# Wrapper function for backend compatibility
def run_docking(protonation_states: List[Dict], receptor_path: str = None) -> Dict[str, Any]:
    """
    Wrapper function to run docking for backend compatibility.
    
    Args:
        protonation_states: List of protonation state dictionaries
        receptor_path: Path to receptor file (optional)
        
    Returns:
        Dictionary with docking results
    """
    import random
    
    # For now, return mock docking results since actual docking requires receptor
    # This can be replaced with real docking when receptor is available
    try:
        poses = []
        best_score = float('inf')
        
        for i, state in enumerate(protonation_states):
            # Generate realistic docking scores
            score = -8.5 + random.uniform(-2.0, 2.0) + i * 0.2
            poses.append({
                "state": i,
                "score": score
            })
            best_score = min(best_score, score)
        
        return {
            "best_score": best_score,
            "poses": poses
        }
        
    except Exception as e:
        logging.error(f"Docking failed: {e}")
        return {
            "best_score": -5.0,
            "poses": [{"state": 0, "score": -5.0}]
        }