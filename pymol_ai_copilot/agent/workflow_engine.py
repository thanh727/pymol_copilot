"""
Scientific Workflow Engine for PyMOL AI Copilot.

Declaratively defines structured scientific workflows (WF01 to WF05+), provides entity
and intent resolution, context-dependent tool scoping, precondition/postcondition gates,
and scientific provenance tracking.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple


class WorkflowState(str, Enum):
    """Execution states for scientific workflows."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepState(str, Enum):
    """Execution states for individual workflow steps."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class WorkflowStepExecution:
    """Record of an individual step execution within a workflow."""
    step_number: int
    name: str
    capability_name: str
    state: StepState = StepState.PENDING
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    precondition_ok: bool = True
    postcondition_ok: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "name": self.name,
            "capability_name": self.capability_name,
            "state": self.state.value,
            "arguments": self.arguments,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "precondition_ok": self.precondition_ok,
            "postcondition_ok": self.postcondition_ok
        }


@dataclass
class WorkflowExecutionRecord:
    """Full execution, validation, and scientific evidence record for a workflow run."""
    execution_id: str
    workflow_id: str
    workflow_name: str
    state: WorkflowState
    input_parameters: Dict[str, Any]
    step_records: List[WorkflowStepExecution] = field(default_factory=list)
    scientific_measurements: Dict[str, Any] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    validation_gates_passed: bool = False
    intent_match_confidence: float = 0.0  # NLP intent confidence, NEVER scientific confidence
    scientific_caveats: List[str] = field(default_factory=list)
    is_single_structure_inspection: bool = False
    reproducibility: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "state": self.state.value,
            "input_parameters": self.input_parameters,
            "step_records": [s.to_dict() for s in self.step_records],
            "scientific_measurements": self.scientific_measurements,
            "units": self.units,
            "validation_gates_passed": self.validation_gates_passed,
            "intent_match_confidence": self.intent_match_confidence,
            "scientific_caveats": self.scientific_caveats,
            "is_single_structure_inspection": self.is_single_structure_inspection,
            "reproducibility": self.reproducibility,
            "error": self.error
        }


@dataclass
class WorkflowStep:
    """A discrete, verifiable step within a scientific workflow."""
    step_number: int
    name: str
    description: str
    expected_capability: str
    required: bool = True
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """Declarative specification of a multi-step scientific workflow."""
    workflow_id: str
    name: str
    description: str
    user_intents: List[str]
    intent_patterns: List[str]
    required_inputs: List[str]
    required_capabilities: List[str]
    steps: List[WorkflowStep]
    validation_criteria: Dict[str, Any]
    error_recovery: str
    cancellation_behavior: str
    expected_outputs: List[str]
    scientific_limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def generate_guidance_prompt(self, extracted_entities: Dict[str, Any]) -> str:
        """Generate structured workflow execution guidance to inject into LLM prompt."""
        step_lines = "\n".join(
            f"   {s.step_number}. **{s.name}**: {s.description} (Use: `{s.expected_capability}`)"
            for s in self.steps
        )
        limits = "\n".join(f"   - {lim}" for lim in self.scientific_limitations)
        entities_str = json.dumps(extracted_entities) if extracted_entities else "None detected"

        return (
            f"## Active Scientific Workflow: {self.workflow_id} — {self.name}\n"
            f"**Workflow Purpose:** {self.description}\n"
            f"**Resolved Entities:** `{entities_str}`\n"
            f"**Recommended Execution Plan:**\n{step_lines}\n"
            f"**Scientific Caveats & Provenance Requirements:**\n{limits}\n"
        )

    def execute_deterministic(
        self,
        inputs: Dict[str, Any],
        registry: Optional[Any] = None
    ) -> WorkflowExecutionRecord:
        """
        Execute the workflow as a verified, dependency-aware deterministic process.
        Enforces execution state transitions: PENDING -> RUNNING -> VALIDATING -> COMPLETED / FAILED.
        """
        from .capability_registry import GLOBAL_CAPABILITY_REGISTRY
        reg = registry or GLOBAL_CAPABILITY_REGISTRY
        exec_id = f"exec_{self.workflow_id.lower()}_{int(time.time()*1000)}"

        record = WorkflowExecutionRecord(
            execution_id=exec_id,
            workflow_id=self.workflow_id,
            workflow_name=self.name,
            state=WorkflowState.PENDING,
            input_parameters=dict(inputs),
            scientific_caveats=list(self.scientific_limitations),
            reproducibility={"pymol_version": "3.1.0", "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        )

        record.state = WorkflowState.RUNNING

        try:
            # ----------------------------------------------------------------
            # WF01: Structure Acquisition
            # ----------------------------------------------------------------
            if self.workflow_id == "WF01":
                pdb_id = inputs.get("pdb_id", "").strip().lower()
                file_path = inputs.get("file_path", "").strip()
                obj_name = inputs.get("object_name")
                fmt = inputs.get("format", "cif")

                record.state = WorkflowState.VALIDATING
                if not pdb_id and not file_path:
                    record.state = WorkflowState.FAILED
                    record.error = "Workflow input error: Neither pdb_id nor file_path was provided."
                    return record

                # Step 1: Acquisition
                record.state = WorkflowState.RUNNING
                t0 = time.time()
                if pdb_id:
                    res_acq = reg.execute("fetch_structure", {"pdb_id": pdb_id, "object_name": obj_name, "format": fmt})
                else:
                    res_acq = reg.execute("load_structure", {"file_path": file_path, "object_name": obj_name})
                d_acq = round((time.time() - t0) * 1000, 2)

                step1 = WorkflowStepExecution(
                    1, "Structure Acquisition", "fetch_structure" if pdb_id else "load_structure",
                    StepState.COMPLETED if res_acq.get("success") else StepState.FAILED,
                    {"pdb_id": pdb_id} if pdb_id else {"file_path": file_path}, res_acq, d_acq,
                    error_message=res_acq.get("error")
                )
                record.step_records.append(step1)
                if not res_acq.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Structure acquisition failed: {res_acq.get('error')}"
                    return record

                target_name = res_acq.get("object_name", pdb_id)

                # Step 2: Verification of atoms and chains
                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_info = reg.execute("get_object_info", {"object_name": target_name})
                d_info = round((time.time() - t0) * 1000, 2)
                step2 = WorkflowStepExecution(
                    2, "Verify Atoms & Chains", "get_object_info",
                    StepState.COMPLETED if res_info.get("success") else StepState.FAILED,
                    {"object_name": target_name}, res_info, d_info,
                    error_message=res_info.get("error")
                )
                record.step_records.append(step2)
                if not res_info.get("success") or res_info.get("total_atoms", 0) <= 0:
                    record.state = WorkflowState.FAILED
                    record.error = "Postcondition gate failed: Loaded structure contains 0 atoms."
                    return record

                # Step 3 & 4: Styling & Orientation
                record.state = WorkflowState.RUNNING
                t0 = time.time()
                res_show = reg.execute("show_representation", {"representation": "cartoon", "selection": target_name})
                res_col = reg.execute("color_selection", {"color": "secondary_structure", "selection": target_name})
                res_orient = reg.execute("orient_selection", {"selection": target_name})
                d_style = round((time.time() - t0) * 1000, 2)

                step3 = WorkflowStepExecution(
                    3, "Apply Representation and Orient", "show_representation",
                    StepState.COMPLETED if res_show.get("success") else StepState.FAILED,
                    {"representation": "cartoon", "selection": target_name}, res_show, d_style
                )
                record.step_records.append(step3)

                # Scientific measurements capture
                record.scientific_measurements = {
                    "object_name": target_name,
                    "pdb_id": pdb_id or os.path.basename(file_path),
                    "atom_count": res_info.get("total_atoms", 0),
                    "protein_atoms": res_info.get("protein_atoms", 0),
                    "chains": res_info.get("chains", []),
                    "ligands": res_acq.get("ligand_names", [])
                }
                record.units = {"atom_count": "atoms"}
                record.validation_gates_passed = True
                record.state = WorkflowState.COMPLETED

            # ----------------------------------------------------------------
            # WF02: Structural Inspection
            # ----------------------------------------------------------------
            elif self.workflow_id == "WF02":
                obj_name = inputs.get("object_name")

                record.state = WorkflowState.RUNNING
                t0 = time.time()
                res_list = reg.execute("list_objects", {})
                d_list = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Enumerate Objects", "list_objects", StepState.COMPLETED, {}, res_list, d_list)
                record.step_records.append(step1)

                loaded_objs = res_list.get("objects", [])
                target = obj_name or (loaded_objs[0] if loaded_objs else None)
                if not target:
                    record.state = WorkflowState.FAILED
                    record.error = "Precondition gate failed: No loaded molecular objects available to inspect."
                    return record

                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_info = reg.execute("get_object_info", {"object_name": target})
                res_chains = reg.execute("get_chains", {"object_name": target})
                res_sum = reg.execute("get_structure_summary", {})
                d_inspect = round((time.time() - t0) * 1000, 2)

                step2 = WorkflowStepExecution(2, "Extract Macro-Statistics & Ligands", "get_object_info", StepState.COMPLETED, {"object_name": target}, res_info, d_inspect)
                record.step_records.append(step2)

                record.scientific_measurements = {
                    "inspected_object": target,
                    "total_atoms": res_info.get("total_atoms", 0),
                    "protein_atoms": res_info.get("protein_atoms", 0),
                    "nucleic_atoms": res_info.get("nucleic_atoms", 0),
                    "ligand_atoms": res_info.get("ligand_atoms", 0),
                    "solvent_atoms": res_info.get("solvent_atoms", 0),
                    "chains": res_info.get("chains", []),
                    "ligands": res_info.get("ligands", []),
                    "bounding_box_angstroms": res_info.get("bounding_box_angstroms", [0.0, 0.0, 0.0])
                }
                record.units = {"atoms": "count", "bounding_box": "Å"}
                record.validation_gates_passed = True
                record.state = WorkflowState.COMPLETED

            # ----------------------------------------------------------------
            # WF03: Structure Comparison & Alignment
            # ----------------------------------------------------------------
            elif self.workflow_id == "WF03":
                mobile = inputs.get("mobile", "").strip()
                target = inputs.get("target", "").strip()
                method = inputs.get("method", "align").strip()
                input_scope = inputs.get("scope", "").strip().lower()
                req_chain = inputs.get("chain", "").strip()
                mob_chain_in = inputs.get("mobile_chain", req_chain).strip()
                tgt_chain_in = inputs.get("target_chain", req_chain).strip()

                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_list = reg.execute("list_objects", {})
                d_list = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Verify Loaded Objects", "list_objects", StepState.COMPLETED, {}, res_list, d_list)
                record.step_records.append(step1)

                objs = res_list.get("objects", [])
                if not mobile or not target:
                    if len(objs) >= 2:
                        mobile, target = objs[0], objs[1]
                    else:
                        record.state = WorkflowState.FAILED
                        record.error = f"Precondition gate failed: Requires at least 2 distinct objects (found {len(objs)})."
                        return record

                # Automatic Multi-chain Detection
                res_mob_chains = reg.execute("get_chains", {"object_name": mobile})
                res_tgt_chains = reg.execute("get_chains", {"object_name": target})
                mob_chains_raw = res_mob_chains.get("chains", [])
                tgt_chains_raw = res_tgt_chains.get("chains", [])

                if isinstance(mob_chains_raw, dict):
                    mob_chains = mob_chains_raw.get(mobile, list(mob_chains_raw.values())[0] if mob_chains_raw else [])
                else:
                    mob_chains = list(mob_chains_raw)

                if isinstance(tgt_chains_raw, dict):
                    tgt_chains = tgt_chains_raw.get(target, list(tgt_chains_raw.values())[0] if tgt_chains_raw else [])
                else:
                    tgt_chains = list(tgt_chains_raw)

                # Scope Disambiguation: Distinguish single-chain and multichain comparisons
                if input_scope == "multichain" or (mob_chain_in.lower() == "all" and tgt_chain_in.lower() == "all"):
                    comparison_scope = "multichain"
                    eff_mob_chain = ""
                    eff_tgt_chain = ""
                    chain_resolution_note = "Multichain comparison across all chains."
                else:
                    comparison_scope = "single_chain"
                    # Validate explicit chain requests
                    if mob_chain_in and mob_chain_in not in mob_chains:
                        record.state = WorkflowState.FAILED
                        record.error = f"Requested chain '{mob_chain_in}' does not exist in mobile structure '{mobile}' (available chains: {mob_chains})."
                        return record
                    if tgt_chain_in and tgt_chain_in not in tgt_chains:
                        record.state = WorkflowState.FAILED
                        record.error = f"Requested chain '{tgt_chain_in}' does not exist in target structure '{target}' (available chains: {tgt_chains})."
                        return record

                    # Biologically informed chain resolution
                    if mob_chain_in and tgt_chain_in:
                        eff_mob_chain = mob_chain_in
                        eff_tgt_chain = tgt_chain_in
                        chain_resolution_note = f"Explicit user-specified chain pair: {eff_mob_chain} -> {eff_tgt_chain}."
                    elif mob_chain_in and not tgt_chain_in:
                        eff_mob_chain = mob_chain_in
                        eff_tgt_chain = mob_chain_in if mob_chain_in in tgt_chains else (tgt_chains[0] if len(tgt_chains) == 1 else "")
                        if not eff_tgt_chain:
                            record.state = WorkflowState.FAILED
                            record.error = f"Ambiguous target chain for mobile chain '{eff_mob_chain}'. Target '{target}' has multiple chains {tgt_chains}. Specify target_chain."
                            return record
                        chain_resolution_note = f"Matched mobile chain '{eff_mob_chain}' to target chain '{eff_tgt_chain}'."
                    elif not mob_chain_in and tgt_chain_in:
                        eff_tgt_chain = tgt_chain_in
                        eff_mob_chain = tgt_chain_in if tgt_chain_in in mob_chains else (mob_chains[0] if len(mob_chains) == 1 else "")
                        if not eff_mob_chain:
                            record.state = WorkflowState.FAILED
                            record.error = f"Ambiguous mobile chain for target chain '{eff_tgt_chain}'. Mobile '{mobile}' has multiple chains {mob_chains}. Specify mobile_chain."
                            return record
                        chain_resolution_note = f"Matched target chain '{eff_tgt_chain}' to mobile chain '{eff_mob_chain}'."
                    else:
                        # Neither chain explicitly requested: apply biological resolution
                        if len(mob_chains) == 1 and len(tgt_chains) == 1:
                            eff_mob_chain = mob_chains[0]
                            eff_tgt_chain = tgt_chains[0]
                            chain_resolution_note = f"Single-chain resolution: {eff_mob_chain} -> {eff_tgt_chain}."
                        else:
                            common_chains = [c for c in mob_chains if c in tgt_chains]
                            if len(common_chains) == 1:
                                eff_mob_chain = common_chains[0]
                                eff_tgt_chain = common_chains[0]
                                chain_resolution_note = f"Unambiguous common chain: {eff_mob_chain}."
                            elif len(common_chains) > 1:
                                # Multiple matching chains, default to primary common chain
                                eff_mob_chain = common_chains[0]
                                eff_tgt_chain = common_chains[0]
                                chain_resolution_note = f"Primary common chain selected: '{eff_mob_chain}' (available common chains: {common_chains})."
                            else:
                                # No overlapping chain IDs across multi-chain complexes
                                record.state = WorkflowState.FAILED
                                record.error = (
                                    f"Ambiguous biological assembly: mobile structure '{mobile}' has chains {mob_chains} and "
                                    f"target '{target}' has chains {tgt_chains} with no overlapping chain IDs. "
                                    f"Explicit chain correspondence is required (e.g., mobile_chain='A', target_chain='C')."
                                )
                                return record

                # Step 2: Superimpose Structures with explicit chain scoping
                record.state = WorkflowState.RUNNING
                align_args = {
                    "mobile": mobile,
                    "target": target,
                    "method": method,
                    "mobile_chain": eff_mob_chain if comparison_scope == "single_chain" else "",
                    "target_chain": eff_tgt_chain if comparison_scope == "single_chain" else ""
                }
                t0 = time.time()
                res_align = reg.execute("align_structures", align_args)
                d_align = round((time.time() - t0) * 1000, 2)

                step2 = WorkflowStepExecution(2, f"Superimpose Structures ({comparison_scope})", "align_structures",
                                              StepState.COMPLETED if res_align.get("success") else StepState.FAILED,
                                              align_args, res_align, d_align, error_message=res_align.get("error"))
                record.step_records.append(step2)
                if not res_align.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Structural alignment failed: {res_align.get('error')}"
                    return record

                # Step 3: Strict C-alpha RMSD Calculation & Residue Deviations
                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                mob_sel_str = f"{mobile}" + (f" and chain {eff_mob_chain}" if (comparison_scope == "single_chain" and eff_mob_chain) else "")
                tgt_sel_str = f"{target}" + (f" and chain {eff_tgt_chain}" if (comparison_scope == "single_chain" and eff_tgt_chain) else "")

                res_rmsd = reg.execute("calculate_rmsd", {
                    "mobile_selection": mob_sel_str,
                    "target_selection": tgt_sel_str,
                    "atom_type": "CA"
                })
                res_comp = reg.execute("compare_residues", {
                    "structure1": target,
                    "structure2": mobile,
                    "chain1": eff_tgt_chain or (tgt_chains[0] if tgt_chains else "A"),
                    "chain2": eff_mob_chain or (mob_chains[0] if mob_chains else "A")
                })
                d_val = round((time.time() - t0) * 1000, 2)

                step3 = WorkflowStepExecution(3, "Calculate Strict C-alpha RMSD & Residue Deviations", "calculate_rmsd",
                                              StepState.COMPLETED if res_rmsd.get("success") else StepState.FAILED,
                                              {"mobile_selection": mob_sel_str, "target_selection": tgt_sel_str}, res_rmsd, d_val)
                record.step_records.append(step3)

                # Anomaly Detection & Scientific Warnings (No Automatic Blind Certification)
                scientific_warning = None
                rmsd_val = res_rmsd.get("rmsd", res_align.get("rmsd", 0.0))
                rmsd_global_ca = res_align.get("rmsd_global_ca", rmsd_val)
                rmsd_refined_ca = res_align.get("rmsd_refined_ca", rmsd_val)
                rmsd_refined_all_atom = res_align.get("rmsd_refined_all_atom", res_align.get("rmsd", rmsd_val))
                rmsd_refined_core = res_align.get("rmsd_refined_core", rmsd_refined_all_atom)
                matched_residues = res_align.get("matched_residues", res_comp.get("compared_residues", 0))

                if comparison_scope == "multichain" and rmsd_global_ca > 12.0:
                    scientific_warning = (
                        f"Diagnostic Signal (Multichain Asymmetric Unit Caveat): Unusually high multichain Ca RMSD ({rmsd_global_ca:.2f} Å) "
                        f"detected across multiple chains. This diagnostic signal may indicate quaternary reorganization, "
                        f"relative subunit displacement, domain movement, or differences in crystallographic asymmetric "
                        f"unit packing. Evaluate individual chain alignments and biological assembly definitions to disambiguate."
                    )
                elif comparison_scope == "single_chain" and rmsd_global_ca > 15.0:
                    scientific_warning = (
                        f"Scientific Review Required: Single-chain Ca RMSD is unusually high ({rmsd_global_ca:.2f} Å). "
                        f"Verify chain correspondence, sequence alignment coverage, or severe domain reorientation."
                    )

                record.scientific_measurements = {
                    "comparison_scope": comparison_scope,
                    "chain_resolution_note": chain_resolution_note,
                    "mobile": mobile,
                    "target": target,
                    "mobile_chain": eff_mob_chain,
                    "target_chain": eff_tgt_chain,
                    "rmsd_global_ca": rmsd_global_ca,
                    "rmsd_refined_ca": rmsd_refined_ca,
                    "rmsd_refined_all_atom": rmsd_refined_all_atom,
                    "rmsd_refined_core": rmsd_refined_core,
                    "total_initial_atoms": res_align.get("total_initial_atoms", 0),
                    "aligned_all_atoms": res_align.get("aligned_all_atoms", res_align.get("aligned_atoms", 0)),
                    "aligned_ca_atoms": res_align.get("aligned_ca_atoms", 0),
                    "refined_ca_atoms": res_align.get("refined_ca_atoms", 0),
                    "matched_residues": matched_residues,
                    "residue_correspondence_count": res_align.get("residue_correspondence_count", 0),
                    "rmsd_units": "Å",
                    "mobile_chain": eff_mob_chain if comparison_scope == "single_chain" else "all",
                    "target_chain": eff_tgt_chain if comparison_scope == "single_chain" else "all",
                    "chains_detected": {"mobile": mob_chains, "target": tgt_chains},
                    "fitting_method": method,
                    "atom_selection": "name CA",
                    "rmsd_angstrom": rmsd_global_ca if comparison_scope == "single_chain" else res_rmsd.get("rmsd", rmsd_global_ca),
                    "rmsd_global_ca": rmsd_global_ca,
                    "rmsd_refined_core": rmsd_refined_core,
                    "aligned_atoms": res_align.get("aligned_atoms", res_rmsd.get("atoms_compared", 0)),
                    "total_initial_atoms": res_align.get("total_initial_atoms", 0),
                    "matched_residues": matched_residues,
                    "outlier_rejection_cycles": res_align.get("cycles", 0),
                    "divergent_residues_count": res_comp.get("deviating_residues_count", 0),
                    "max_displacement_angstrom": res_comp.get("max_displacement", 0.0),
                    "scientific_warning": scientific_warning
                }
                record.units = {"rmsd_angstrom": "Å", "rmsd_global_ca": "Å", "rmsd_refined_core": "Å", "displacement": "Å"}
                if scientific_warning:
                    record.scientific_caveats.append(scientific_warning)
                record.validation_gates_passed = True
                record.state = WorkflowState.COMPLETED

            # ----------------------------------------------------------------
            # WF04: Mutation Neighborhood Analysis
            # ----------------------------------------------------------------
            elif self.workflow_id == "WF04":
                mut_str = inputs.get("mutation_str") or inputs.get("mutation") or inputs.get("resi", "42")
                obj_name = inputs.get("object_name")
                chain = inputs.get("chain", "A")
                cutoff = float(inputs.get("cutoff", 5.0))

                record.is_single_structure_inspection = True
                record.scientific_caveats.append(
                    "NOTICE: This is a single-structure local spatial geometry analysis. "
                    "It does NOT represent a physical wildtype-versus-mutant coordinate comparison "
                    "or a thermodynamic stability calculation (Delta-Delta-G)."
                )

                record.state = WorkflowState.RUNNING
                t0 = time.time()
                res_mut = reg.execute("analyze_mutation", {
                    "mutation_str": str(mut_str),
                    "object_name": obj_name,
                    "chain": chain,
                    "radius": cutoff
                })
                d_mut = round((time.time() - t0) * 1000, 2)

                step1 = WorkflowStepExecution(1, "Analyze Mutation & Wildtype Validation", "analyze_mutation",
                                              StepState.COMPLETED if res_mut.get("success") else StepState.FAILED,
                                              {"mutation_str": str(mut_str), "object_name": obj_name, "chain": chain}, res_mut, d_mut,
                                              error_message=res_mut.get("error"))
                record.step_records.append(step1)
                if not res_mut.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Residue analysis failed: {res_mut.get('error')}"
                    return record

                resolved_resi = res_mut.get("resi", str(mut_str))
                target_sel = f"{obj_name + ' and ' if obj_name else ''}chain {chain} and resi {resolved_resi}"

                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_near = reg.execute("find_nearby_residues", {"target_selection": target_sel, "cutoff": cutoff})
                res_polar = reg.execute("find_polar_contact_candidates", {
                    "selection1": target_sel,
                    "selection2": f"{obj_name + ' and ' if obj_name else ''}chain {chain} and not resi {resolved_resi}",
                    "cutoff": 3.5
                })
                d_val = round((time.time() - t0) * 1000, 2)

                step2 = WorkflowStepExecution(2, "Measure Spatial Neighborhood & Contacts", "find_nearby_residues", StepState.COMPLETED,
                                              {"target_selection": target_sel, "cutoff": cutoff}, res_near, d_val)
                record.step_records.append(step2)

                residues_list = res_near.get("residues", [])
                resi_numbers = []
                for r in residues_list:
                    if isinstance(r, dict) and "resi" in r:
                        try:
                            resi_numbers.append(int(r["resi"]))
                        except Exception:
                            pass
                    elif isinstance(r, str):
                        m = re.search(r'\d+', r)
                        if m:
                            resi_numbers.append(int(m.group()))

                actual_res_3 = res_mut.get("actual_residue_3", "")
                actual_res_1 = res_mut.get("wt", "")
                resolved_resi_int = int(resolved_resi) if str(resolved_resi).isdigit() else resolved_resi

                record.scientific_measurements = {
                    "locus": f"chain {chain} resi {resolved_resi}",
                    "wildtype_match": res_mut.get("wildtype_match", True),
                    "actual_residue": actual_res_3,
                    "residue_name": actual_res_3 or actual_res_1,
                    "residue_number": resolved_resi_int,
                    "expected_residue": res_mut.get("expected_wildtype_3"),
                    "neighbor_radius_angstroms": cutoff,
                    "neighbor_residues_count": res_near.get("residue_count", 0),
                    "neighbor_residues": residues_list,
                    "neighbor_residue_numbers": resi_numbers,
                    "polar_contact_candidates_count": res_polar.get("polar_contact_candidates_count", 0),
                    "polar_contact_distances": res_polar.get("polar_contact_distances", [])
                }
                record.units = {"distance_cutoff": "Å", "polar_contacts": "Å"}
                record.validation_gates_passed = True
                record.state = WorkflowState.COMPLETED

            # ----------------------------------------------------------------
            # WF05: Publication Visualization
            # ----------------------------------------------------------------
            elif self.workflow_id == "WF05":
                preset_name = inputs.get("preset_name") or inputs.get("preset") or "cartoon_by_chain"
                output_dir = inputs.get("output_dir")
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    png_path = inputs.get("output_png") or os.path.join(output_dir, "figure.png")
                    pml_path = inputs.get("output_pml") or os.path.join(output_dir, "figure_commands.pml")
                    pse_path = inputs.get("output_pse") or os.path.join(output_dir, "figure_session.pse")
                else:
                    png_path = inputs.get("output_png") or inputs.get("filename") or "figure.png"
                    pml_path = inputs.get("output_pml") or "figure_commands.pml"
                    pse_path = inputs.get("output_pse") or "figure_session.pse"

                record.state = WorkflowState.RUNNING
                t0 = time.time()
                res_pre = reg.execute("apply_visualization_preset", {"preset_name": preset_name})
                res_bg = reg.execute("set_background", {"color": "white"})
                res_orient = reg.execute("orient_selection", {"selection": "all"})
                d_style = round((time.time() - t0) * 1000, 2)

                step1 = WorkflowStepExecution(1, "Apply Publication Preset & Framing", "apply_visualization_preset",
                                              StepState.COMPLETED, {"preset_name": preset_name}, res_pre, d_style)
                record.step_records.append(step1)

                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_png = reg.execute("export_png", {"filename": png_path, "width": 1920, "height": 1080, "ray": 0})
                res_pml = reg.execute("export_pml", {"filename": pml_path})
                res_pse = reg.execute("save_session", {"filename": pse_path})
                d_io = round((time.time() - t0) * 1000, 2)

                step2 = WorkflowStepExecution(2, "Render Figure & Export Scripts", "export_png",
                                              StepState.COMPLETED if res_png.get("success") else StepState.FAILED,
                                              {"filename": png_path}, res_png, d_io, error_message=res_png.get("error"))
                record.step_records.append(step2)

                final_png = res_png.get("filepath") or res_png.get("filename") or png_path
                final_pml = res_pml.get("filepath") or res_pml.get("filename") or pml_path
                final_pse = res_pse.get("filepath") or res_pse.get("filename") or pse_path

                record.scientific_measurements = {
                    "preset_applied": preset_name,
                    "png_output": final_png,
                    "pml_script": final_pml,
                    "pse_session": final_pse,
                    "resolution": "1920x1080"
                }
                record.validation_gates_passed = res_png.get("success", False) and os.path.exists(final_png)
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            # WF06: Ligand Interaction Analysis
            elif self.workflow_id == "WF06":
                record.state = WorkflowState.RUNNING
                target_obj = inputs.get("target") or inputs.get("object_name") or inputs.get("pdb_id") or ""
                if not target_obj:
                    res_objs = reg.execute("list_objects", {})
                    objs = res_objs.get("objects", [])
                    if not objs:
                        record.state = WorkflowState.FAILED
                        record.error = "No structures loaded for ligand interaction analysis."
                        return record
                    target_obj = objs[0]

                # Step 1: Identify ligands
                t0 = time.time()
                res_ligs = reg.execute("identify_ligands", {"object_name": target_obj})
                d1 = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Identify Bound Ligands", "identify_ligands",
                                              StepState.COMPLETED if res_ligs.get("success") else StepState.FAILED,
                                              {"object_name": target_obj}, res_ligs, d1, error_message=res_ligs.get("error"))
                record.step_records.append(step1)

                ligands = res_ligs.get("ligands", [])
                if not ligands:
                    record.state = WorkflowState.FAILED
                    record.error = f"No biologically relevant organic ligands identified in '{target_obj}'."
                    return record

                ligand_resn = inputs.get("ligand_resn") or ligands[0]["resn"]
                ligand_resi = inputs.get("ligand_resi") or ligands[0]["resi"]
                ligand_chain = inputs.get("ligand_chain") or ligands[0]["chain"]
                cutoff = float(inputs.get("cutoff", 4.0))

                # Step 2: Analyze contacts & polar candidates
                t0 = time.time()
                res_inter = reg.execute("analyze_ligand_interactions", {
                    "object_name": target_obj,
                    "ligand_resn": ligand_resn,
                    "ligand_resi": ligand_resi,
                    "ligand_chain": ligand_chain,
                    "cutoff": cutoff,
                    "altloc": inputs.get("altloc", "A")
                })
                d2 = round((time.time() - t0) * 1000, 2)
                step2 = WorkflowStepExecution(2, "Analyze Ligand Contacts", "analyze_ligand_interactions",
                                              StepState.COMPLETED if res_inter.get("success") else StepState.FAILED,
                                              {"object_name": target_obj, "ligand_resn": ligand_resn, "cutoff": cutoff},
                                              res_inter, d2, error_message=res_inter.get("error"))
                record.step_records.append(step2)

                # Step 3: Visualize Pocket
                t0 = time.time()
                res_vis = reg.execute("visualize_ligand_pocket", {
                    "object_name": target_obj,
                    "ligand_resn": ligand_resn,
                    "ligand_resi": ligand_resi,
                    "ligand_chain": ligand_chain,
                    "cutoff": cutoff,
                    "show_contacts": True
                })
                d3 = round((time.time() - t0) * 1000, 2)
                step3 = WorkflowStepExecution(3, "Visualize Binding Pocket", "visualize_ligand_pocket",
                                              StepState.COMPLETED if res_vis.get("success") else StepState.FAILED,
                                              {"object_name": target_obj, "ligand_resn": ligand_resn}, res_vis, d3)
                record.step_records.append(step3)

                # Step 4: Optional export
                out_path = inputs.get("output_path")
                if out_path:
                    fmt = "csv" if out_path.endswith(".csv") else "json"
                    reg.execute("export_ligand_contacts", {
                        "object_name": target_obj,
                        "output_path": out_path,
                        "ligand_resn": ligand_resn,
                        "ligand_resi": ligand_resi,
                        "cutoff": cutoff,
                        "format": fmt
                    })

                record.scientific_measurements = {
                    "object": target_obj,
                    "ligand_resn": ligand_resn,
                    "ligand_resi": ligand_resi,
                    "ligand_chain": ligand_chain,
                    "cutoff_angstrom": cutoff,
                    "contacting_residues_count": res_inter.get("contacting_residues_count", 0),
                    "polar_contacts_count": res_inter.get("polar_contacts_count", 0),
                    "top_contacts": res_inter.get("contacts", [])[:5],
                    "scientific_limitation": res_inter.get("scientific_limitation", "")
                }
                record.validation_gates_passed = res_inter.get("success", False)
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            # WF07: Solvent Accessibility Analysis
            elif self.workflow_id == "WF07":
                record.state = WorkflowState.RUNNING
                target_obj = inputs.get("target") or inputs.get("object_name") or ""
                if not target_obj:
                    res_objs = reg.execute("list_objects", {})
                    objs = res_objs.get("objects", [])
                    if not objs:
                        record.state = WorkflowState.FAILED
                        record.error = "No structures loaded for solvent accessibility analysis."
                        return record
                    target_obj = objs[0]

                probe_radius = float(inputs.get("probe_radius", 1.4))

                # Step 1: Calculate SASA
                t0 = time.time()
                res_sasa = reg.execute("calculate_sasa", {
                    "object_name": target_obj,
                    "selection": inputs.get("selection", ""),
                    "probe_radius": probe_radius
                })
                d1 = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Calculate Solvent Accessibility", "calculate_sasa",
                                              StepState.COMPLETED if res_sasa.get("success") else StepState.FAILED,
                                              {"object_name": target_obj, "probe_radius": probe_radius}, res_sasa, d1)
                record.step_records.append(step1)

                # Step 2: Map SASA to structure
                t0 = time.time()
                res_map = reg.execute("map_sasa_to_structure", {
                    "object_name": target_obj,
                    "probe_radius": probe_radius,
                    "palette": inputs.get("palette", "blue_white_red"),
                    "representation": inputs.get("representation", "surface")
                })
                d2 = round((time.time() - t0) * 1000, 2)
                step2 = WorkflowStepExecution(2, "Map SASA to Molecular Surface", "map_sasa_to_structure",
                                              StepState.COMPLETED if res_map.get("success") else StepState.FAILED,
                                              {"object_name": target_obj}, res_map, d2)
                record.step_records.append(step2)

                record.scientific_measurements = {
                    "object": target_obj,
                    "total_sasa_angstrom2": res_sasa.get("total_sasa_angstrom2", 0.0),
                    "probe_radius_angstrom": probe_radius,
                    "buried_residues_count": res_sasa.get("buried_residues_count", 0),
                    "intermediate_residues_count": res_sasa.get("intermediate_residues_count", 0),
                    "exposed_residues_count": res_sasa.get("exposed_residues_count", 0),
                    "scientific_limitation": res_sasa.get("scientific_limitation", "")
                }
                record.validation_gates_passed = res_sasa.get("success", False) and res_sasa.get("total_sasa_angstrom2", 0.0) > 0.0
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            # WF08: Epitope Structural Mapping
            elif self.workflow_id == "WF08":
                record.state = WorkflowState.RUNNING
                target_obj = inputs.get("target") or inputs.get("object_name") or ""
                if not target_obj:
                    res_objs = reg.execute("list_objects", {})
                    objs = res_objs.get("objects", [])
                    if not objs:
                        record.state = WorkflowState.FAILED
                        record.error = "No structures loaded for epitope mapping."
                        return record
                    target_obj = objs[0]

                # Step 1: Map epitope sequence or residue list
                t0 = time.time()
                res_map = reg.execute("map_epitope_sequence", {
                    "object_name": target_obj,
                    "epitope_sequence": inputs.get("epitope_sequence", ""),
                    "residue_list": inputs.get("residue_list", ""),
                    "chain": inputs.get("chain", "")
                })
                d1 = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Map Epitope to 3D Coordinates", "map_epitope_sequence",
                                              StepState.COMPLETED if res_map.get("success") else StepState.FAILED,
                                              {"object_name": target_obj}, res_map, d1, error_message=res_map.get("error"))
                record.step_records.append(step1)

                if not res_map.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Epitope mapping failed: {res_map.get('error')}"
                    return record

                mapped_chain = res_map.get("chain", "A")
                mapped_resis = res_map.get("residue_numbers", [])

                # Step 2: Visualize epitope on structure
                t0 = time.time()
                res_vis = reg.execute("visualize_epitope", {
                    "object_name": target_obj,
                    "chain": mapped_chain,
                    "residue_numbers": mapped_resis,
                    "representation": inputs.get("representation", "surface_highlight")
                })
                d2 = round((time.time() - t0) * 1000, 2)
                step2 = WorkflowStepExecution(2, "Highlight Epitope on Surface", "visualize_epitope",
                                              StepState.COMPLETED if res_vis.get("success") else StepState.FAILED,
                                              {"object_name": target_obj, "chain": mapped_chain}, res_vis, d2)
                record.step_records.append(step2)

                record.scientific_measurements = {
                    "object": target_obj,
                    "chain": mapped_chain,
                    "mapped_residues_count": res_map.get("mapped_residues_count", 0),
                    "residue_numbers": mapped_resis,
                    "spatial_centroid": res_map.get("spatial_centroid", []),
                    "maximum_span_angstrom": res_map.get("maximum_span_angstrom", 0.0),
                    "is_spatially_clustered": res_map.get("is_spatially_clustered", True),
                    "total_epitope_sasa_angstrom2": res_map.get("total_epitope_sasa_angstrom2", 0.0),
                    "average_rsa_percent": res_map.get("average_rsa_percent", 0.0),
                    "exposed_residues_count": res_map.get("exposed_residues_count", 0),
                    "scientific_limitation": res_map.get("scientific_limitation", "")
                }
                record.validation_gates_passed = res_map.get("success", False) and len(mapped_resis) > 0
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            # WF09: WT–Mutant Structural Comparison
            elif self.workflow_id == "WF09":
                record.state = WorkflowState.RUNNING
                wt_obj = inputs.get("wildtype_object") or inputs.get("wt_object") or ""
                mut_obj = inputs.get("mutant_object") or inputs.get("mut_object") or ""
                mut_str = inputs.get("mutation_str") or inputs.get("mutation") or ""
                chain = inputs.get("chain", "A")

                if not wt_obj or not mut_obj:
                    res_objs = reg.execute("list_objects", {})
                    objs = res_objs.get("objects", [])
                    if len(objs) >= 2:
                        wt_obj = wt_obj or objs[0]
                        mut_obj = mut_obj or objs[1]
                    else:
                        record.state = WorkflowState.FAILED
                        record.error = "WT-mutant comparison requires at least 2 loaded structures (wild-type and mutant)."
                        return record

                # Step 1: Execute sequence-aware structural comparison & local environment inspection
                t0 = time.time()
                res_comp = reg.execute("compare_wt_mutant", {
                    "wildtype_object": wt_obj,
                    "mutant_object": mut_obj,
                    "mutation_str": mut_str,
                    "chain": chain,
                    "radius": float(inputs.get("radius", 5.0))
                })
                d1 = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Compare WT vs Mutant Structures", "compare_wt_mutant",
                                              StepState.COMPLETED if res_comp.get("success") else StepState.FAILED,
                                              {"wildtype_object": wt_obj, "mutant_object": mut_obj, "mutation_str": mut_str},
                                              res_comp, d1, error_message=res_comp.get("error"))
                record.step_records.append(step1)

                if not res_comp.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"WT-mutant comparison failed: {res_comp.get('error')}"
                    return record

                loc = res_comp.get("local_mutation_comparison") or {}
                record.scientific_measurements = {
                    "wildtype_object": wt_obj,
                    "mutant_object": mut_obj,
                    "mutation": mut_str,
                    "chain": chain,
                    "global_chain_rmsd_angstrom": res_comp.get("global_chain_rmsd_angstrom", 0.0),
                    "aligned_atoms": res_comp.get("aligned_atoms", 0),
                    "structure_origin": res_comp.get("structure_origin", "experimental_structure"),
                    "ca_displacement_angstrom": loc.get("ca_displacement_angstrom", 0.0),
                    "backbone_rmsd_angstrom": loc.get("backbone_rmsd_angstrom", 0.0),
                    "wildtype_neighbors_count": loc.get("wildtype_neighbors_count", 0),
                    "mutant_neighbors_count": loc.get("mutant_neighbors_count", 0),
                    "common_neighbors_count": loc.get("common_neighbors_count", 0),
                    "polar_contacts_delta": loc.get("polar_contacts_delta", 0),
                    "scientific_limitation": res_comp.get("scientific_limitation", "")
                }
                record.validation_gates_passed = res_comp.get("success", False)
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            # WF10: Batch Structural Analysis
            elif self.workflow_id == "WF10":
                record.state = WorkflowState.RUNNING
                struct_names = inputs.get("structure_names") or inputs.get("structures") or []
                if not struct_names:
                    res_objs = reg.execute("list_objects", {})
                    struct_names = res_objs.get("objects", [])

                if len(struct_names) < 2:
                    record.state = WorkflowState.FAILED
                    record.error = f"Batch structural comparison requires at least 2 loaded structures (found {len(struct_names)})."
                    return record

                ref_name = inputs.get("reference_name") or struct_names[0]
                chain = inputs.get("chain", "A")
                method = inputs.get("method", "align")
                output_dir = inputs.get("output_dir", "")

                t0 = time.time()
                res_batch = reg.execute("batch_compare_structures", {
                    "structure_names": struct_names,
                    "reference_name": ref_name,
                    "chain": chain,
                    "method": method,
                    "output_dir": output_dir
                })
                d1 = round((time.time() - t0) * 1000, 2)
                step1 = WorkflowStepExecution(1, "Batch Pairwise Alignment", "batch_compare_structures",
                                              StepState.COMPLETED if res_batch.get("success") else StepState.FAILED,
                                              {"structure_names": struct_names, "reference_name": ref_name},
                                              res_batch, d1, error_message=res_batch.get("error"))
                record.step_records.append(step1)

                if not res_batch.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Batch comparison failed: {res_batch.get('error')}"
                    return record

                record.scientific_measurements = {
                    "reference_structure": ref_name,
                    "chain": chain,
                    "total_structures_analyzed": res_batch.get("total_structures_analyzed", 0),
                    "comparisons_count": res_batch.get("comparisons_count", 0),
                    "results": res_batch.get("results", []),
                    "exported_files": res_batch.get("exported_files", {}),
                    "scientific_limitation": res_batch.get("scientific_limitation", "")
                }
                record.validation_gates_passed = res_batch.get("success", False) and res_batch.get("comparisons_count", 0) > 0
                record.state = WorkflowState.COMPLETED if record.validation_gates_passed else WorkflowState.FAILED

            else:
                record.state = WorkflowState.FAILED
                record.error = f"Unsupported deterministic workflow: {self.workflow_id}"

        except Exception as e:
            record.state = WorkflowState.FAILED
            record.error = f"Workflow execution encountered unexpected exception: {e}"

        return record


class WorkflowSession:
    """
    State machine session tracking workflow execution within the interactive Agent loop.
    Enforces workflow states: PENDING -> RUNNING -> VALIDATING -> COMPLETED / FAILED.
    """

    def __init__(
        self,
        workflow: WorkflowDefinition,
        entities: Dict[str, Any],
        intent_match_confidence: float = 0.0
    ):
        self.workflow = workflow
        self.entities = entities
        self.intent_match_confidence = intent_match_confidence  # NLP confidence only
        self.state = WorkflowState.PENDING
        self.step_executions: List[WorkflowStepExecution] = []
        self.scientific_measurements: Dict[str, Any] = {}
        self.start_time = time.time()
        self.execution_id = f"sess_{workflow.workflow_id.lower()}_{int(self.start_time * 1000)}"

    def start(self):
        """Transition workflow state from PENDING to RUNNING."""
        self.state = WorkflowState.RUNNING

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: float = 0.0
    ):
        """Record and validate a tool execution against the active workflow definition."""
        self.state = WorkflowState.VALIDATING
        success = result.get("success", False)

        step_num = len(self.step_executions) + 1
        step_exec = WorkflowStepExecution(
            step_number=step_num,
            name=f"Step {step_num}: {tool_name}",
            capability_name=tool_name,
            state=StepState.COMPLETED if success else StepState.FAILED,
            arguments=arguments,
            result=result,
            duration_ms=duration_ms,
            error_message=result.get("error"),
            precondition_ok=not result.get("precondition_failure", False),
            postcondition_ok=not result.get("postcondition_failure", False)
        )
        self.step_executions.append(step_exec)

        # Harvest scientific measurements as they occur
        if success:
            if "total_atoms" in result or "atom_count" in result:
                self.scientific_measurements["atom_count"] = result.get("total_atoms", result.get("atom_count"))
            if "chains" in result:
                self.scientific_measurements["chains"] = result.get("chains")
            if "rmsd" in result or "rmsd_post_refinement" in result:
                self.scientific_measurements["rmsd_angstrom"] = result.get("rmsd_global_ca", result.get("rmsd", result.get("rmsd_post_refinement")))
                self.scientific_measurements["rmsd_refined_core"] = result.get("rmsd_refined_core", result.get("rmsd"))
                self.scientific_measurements["rmsd_global_ca"] = result.get("rmsd_global_ca")
                self.scientific_measurements["aligned_atoms"] = result.get("aligned_atoms", 0)
                self.scientific_measurements["matched_residues"] = result.get("matched_residues", 0)
                if "mobile_chain" in result:
                    self.scientific_measurements["mobile_chain"] = result["mobile_chain"]
                if "target_chain" in result:
                    self.scientific_measurements["target_chain"] = result["target_chain"]
            if "polar_contact_candidates_count" in result:
                self.scientific_measurements["polar_contacts_count"] = result.get("polar_contact_candidates_count")
            if "neighbor_residues_count" in result:
                self.scientific_measurements["neighbor_residues_count"] = result.get("neighbor_residues_count")
            if "filepath" in result:
                self.scientific_measurements["output_figure"] = result.get("filepath")
            if "total_sasa_angstrom2" in result:
                self.scientific_measurements["total_sasa_angstrom2"] = result["total_sasa_angstrom2"]
            if "contacting_residues_count" in result:
                self.scientific_measurements["contacting_residues_count"] = result["contacting_residues_count"]
            if "mapped_residues_count" in result:
                self.scientific_measurements["mapped_residues_count"] = result["mapped_residues_count"]
            if "global_chain_rmsd_angstrom" in result:
                self.scientific_measurements["global_chain_rmsd_angstrom"] = result["global_chain_rmsd_angstrom"]
            if "total_structures_analyzed" in result:
                self.scientific_measurements["total_structures_analyzed"] = result["total_structures_analyzed"]

        self.state = WorkflowState.RUNNING

    def finalize(self, cancelled: bool = False) -> WorkflowExecutionRecord:
        """Evaluate final gates and transition to COMPLETED, FAILED, or CANCELLED."""
        if cancelled:
            self.state = WorkflowState.CANCELLED
            error_msg = "Workflow execution cancelled by user."
            gates_passed = False
        else:
            # Check if all required steps succeeded
            has_failures = any(s.state == StepState.FAILED for s in self.step_executions)
            executed_caps = {s.capability_name for s in self.step_executions if s.state == StepState.COMPLETED}

            if len(self.step_executions) == 0:
                # No tools executed (e.g. conversational prompt or mock assistant response)
                gates_passed = True
                self.state = WorkflowState.COMPLETED
                error_msg = None
            else:
                # Workflow-specific mandatory gate verification: core capability must succeed
                if self.workflow.workflow_id == "WF01":
                    gates_passed = "fetch_structure" in executed_caps or "load_structure" in executed_caps
                elif self.workflow.workflow_id == "WF02":
                    gates_passed = "get_object_info" in executed_caps or "get_structure_summary" in executed_caps
                elif self.workflow.workflow_id == "WF03":
                    gates_passed = "align_structures" in executed_caps or "calculate_rmsd" in executed_caps
                elif self.workflow.workflow_id == "WF04":
                    gates_passed = "analyze_mutation" in executed_caps or "find_nearby_residues" in executed_caps
                elif self.workflow.workflow_id == "WF05":
                    gates_passed = "export_png" in executed_caps or "apply_visualization_preset" in executed_caps
                elif self.workflow.workflow_id == "WF06":
                    gates_passed = "analyze_ligand_interactions" in executed_caps or "identify_ligands" in executed_caps
                elif self.workflow.workflow_id == "WF07":
                    gates_passed = "calculate_sasa" in executed_caps or "map_sasa_to_structure" in executed_caps
                elif self.workflow.workflow_id == "WF08":
                    gates_passed = "map_epitope_sequence" in executed_caps or "visualize_epitope" in executed_caps
                elif self.workflow.workflow_id == "WF09":
                    gates_passed = "compare_wt_mutant" in executed_caps
                elif self.workflow.workflow_id == "WF10":
                    gates_passed = "batch_compare_structures" in executed_caps
                else:
                    gates_passed = not has_failures

                if gates_passed:
                    self.state = WorkflowState.COMPLETED
                    error_msg = None if not has_failures else "Core workflow gates passed with non-fatal auxiliary warnings."
                else:
                    self.state = WorkflowState.FAILED
                    error_msg = "Mandatory workflow validation gates failed or incomplete."

        return WorkflowExecutionRecord(
            execution_id=self.execution_id,
            workflow_id=self.workflow.workflow_id,
            workflow_name=self.workflow.name,
            state=self.state,
            input_parameters=dict(self.entities),
            step_records=list(self.step_executions),
            scientific_measurements=dict(self.scientific_measurements),
            units={"distances": "Å", "rmsd": "Å", "atoms": "count"},
            validation_gates_passed=gates_passed,
            intent_match_confidence=self.intent_match_confidence,
            scientific_caveats=list(self.workflow.scientific_limitations),
            is_single_structure_inspection=(self.workflow.workflow_id == "WF04"),
            reproducibility={"pymol_version": "3.1.0", "duration_seconds": round(time.time() - self.start_time, 2)},
            error=error_msg
        )


class EntityExtractor:
    """Extracts biological entities, accessions, mutations, and parameters from user text."""

    @staticmethod
    def extract_entities(user_text: str, session_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        text = user_text.strip()

        # 1. PDB Accession / AlphaFold ID
        # Match standard 4-char PDB ID or AF- accession
        pdb_match = re.search(r"\b([0-9][a-zA-Z0-9]{3})\b", text)
        if pdb_match:
            entities["pdb_id"] = pdb_match.group(1).lower()
        af_match = re.search(r"\b(af-[a-zA-Z0-9]+-f\d+)\b", text, re.IGNORECASE)
        if af_match:
            entities["pdb_id"] = af_match.group(1).lower()

        # 2. Mutation notation (e.g. R132H, Arg132His, A:R132H)
        mut_match = re.search(
            r"\b(?:chain\s+([A-Za-z0-9])\s*:?\s*)?([A-Z][a-z]{0,2})[-_: ]?(\d+)[-_: ]?([A-Z][a-z]{0,2})\b",
            text
        )
        if mut_match:
            ch = mut_match.group(1) or ""
            wt = mut_match.group(2)
            pos = mut_match.group(3)
            mut = mut_match.group(4)
            entities["mutation"] = f"{wt}{pos}{mut}".upper()
            entities["mutation_pos"] = int(pos)
            entities["mutation_wt"] = wt.upper()
            entities["mutation_mut"] = mut.upper()
            if ch:
                entities["mutation_chain"] = ch.upper()

        # 3. Residue identifier (e.g. resi 42, residue 42, chain A resi 50)
        resi_match = re.search(r"\b(?:chain\s+([A-Za-z0-9])\s+)?(?:resi|res|residue)\s+(\d+[A-Za-z]?)\b", text, re.IGNORECASE)
        if resi_match:
            if resi_match.group(1):
                entities["chain"] = resi_match.group(1).upper()
            entities["resi"] = resi_match.group(2)

        # 4. Chain identifier (e.g. chain A, chuỗi A)
        chain_match = re.search(r"\b(?:chain|chuỗi)\s+([A-Za-z0-9])\b", text, re.IGNORECASE)
        if chain_match and "chain" not in entities:
            entities["chain"] = chain_match.group(1).upper()

        # 5. Distance cutoff (e.g. 5 A, 5.0 angstroms, 3.5 Å)
        dist_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:angstroms?|angstrom|Å|a\b)", text, re.IGNORECASE)
        if dist_match:
            entities["cutoff"] = float(dist_match.group(1))

        # 6. Session object references
        if session_objects:
            referenced_objs = [obj for obj in session_objects if re.search(r"\b" + re.escape(obj) + r"\b", text, re.IGNORECASE)]
            if referenced_objs:
                entities["referenced_objects"] = referenced_objs

        # 7. File paths or image targets
        file_match = re.search(r"([a-zA-Z0-9_\-\./\\]+\.(?:png|pse|pml|cif|pdb|json|csv))\b", text, re.IGNORECASE)
        if file_match:
            entities["file_path"] = file_match.group(1)

        # 8. Comparison scope (multichain vs single_chain)
        if re.search(r"\b(multichain|multi-chain|all chains|toàn bộ chuỗi|toàn bộ protein)\b", text, re.IGNORECASE):
            entities["scope"] = "multichain"

        # 9. Ligand identifier (e.g. ligand AP5, chất gắn AP5, resn AP5)
        lig_match = re.search(r"\b(?:ligand|chất gắn|resn)\s+([A-Za-z0-9]{1,5})\b", text, re.IGNORECASE)
        if lig_match:
            entities["ligand_resn"] = lig_match.group(1).upper()

        # 10. Epitope sequence (e.g. epitope TITLEVE, peptide TITLEVE, đoạn TITLEVE)
        epi_match = re.search(r"\b(?:epitope|peptide|biểu vị|đoạn|sequence)\s+([A-Za-z]{4,30})\b", text, re.IGNORECASE)
        if epi_match:
            entities["epitope_sequence"] = epi_match.group(1).upper()

        # 11. Probe radius (e.g. probe 1.4, bán kính 1.4)
        probe_match = re.search(r"\b(?:probe|bán kính dò|probe radius)\s+(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
        if probe_match:
            entities["probe_radius"] = float(probe_match.group(1))

        return entities


class WorkflowRegistry:
    """
    Central engine for scientific workflows.
    Matches user requests to validated workflows, scopes available tools,
    and validates step-by-step scientific outcomes.
    """

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._register_reference_workflows()

    def register(self, wf: WorkflowDefinition) -> None:
        self._workflows[wf.workflow_id] = wf

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[WorkflowDefinition]:
        return list(self._workflows.values())

    def match_workflow(
        self,
        user_instruction: str,
        session_objects: Optional[List[str]] = None
    ) -> Tuple[Optional[WorkflowDefinition], Dict[str, Any], float]:
        """
        Evaluate user instruction and current session state to match a scientific workflow.

        Returns:
            (matched_workflow, extracted_entities, confidence_score)
        """
        entities = EntityExtractor.extract_entities(user_instruction, session_objects)
        text_lower = user_instruction.lower().strip()

        best_wf: Optional[WorkflowDefinition] = None
        best_score = 0.0

        for wf in self._workflows.values():
            score = 0.0

            # 1. Regex pattern matching (highest confidence)
            for pat in wf.intent_patterns:
                if re.search(pat, text_lower, re.IGNORECASE):
                    score += 0.6
                    break

            # 2. Intent keyword matching
            matched_intents = sum(1 for kw in wf.user_intents if kw.lower() in text_lower)
            if matched_intents > 0:
                score += min(0.4, matched_intents * 0.15)

            # 3. Contextual entity matching
            if wf.workflow_id == "WF01" and "pdb_id" in entities:
                # If user mentions a PDB ID and fetch/download intent
                score += 0.3
            elif wf.workflow_id == "WF03" and (session_objects and len(session_objects) >= 2 or len(entities.get("referenced_objects", [])) >= 2):
                if any(w in text_lower for w in ["compare", "so sánh", "align", "căn chỉnh", "rmsd"]):
                    score += 0.4
            elif wf.workflow_id == "WF04" and "mutation" in entities:
                # Do not prioritize WF04 if user explicitly requests comparison between WT and mutant
                if not (any(w in text_lower for w in ["compare", "so sánh", "vs", "versus", "đối chiếu"]) and any(w in text_lower for w in ["wt", "wildtype", "wild-type", "với wildtype", "mutant"])):
                    score += 0.5
            elif wf.workflow_id == "WF05" and ("png" in text_lower or "figure" in text_lower or "xuất" in text_lower or "publication" in text_lower):
                score += 0.4
            elif wf.workflow_id == "WF06" and ("ligand" in text_lower or "pocket" in text_lower or "túi gắn" in text_lower or "chất gắn" in text_lower or "ligand_resn" in entities):
                score += 0.5
            elif wf.workflow_id == "WF07" and ("sasa" in text_lower or "solvent" in text_lower or "accessibility" in text_lower or "dung môi" in text_lower or "bộc lộ" in text_lower):
                score += 0.5
            elif wf.workflow_id == "WF08" and ("epitope" in text_lower or "antigen" in text_lower or "biểu vị" in text_lower or "kháng nguyên" in text_lower or "epitope_sequence" in entities):
                score += 0.5
            elif wf.workflow_id == "WF09":
                has_comp = any(w in text_lower for w in ["compare", "so sánh", "vs", "versus", "đối chiếu"])
                has_mut = any(w in text_lower for w in ["mutant", "mutation", "đột biến"]) or "mutation" in entities
                has_wt = any(w in text_lower for w in ["wt", "wildtype", "wild-type"])
                if has_comp and (has_wt or has_mut):
                    score += 0.7
            elif wf.workflow_id == "WF10" and ("batch" in text_lower or "hàng loạt" in text_lower or "ensemble" in text_lower or "tập hợp" in text_lower):
                score += 0.5

            if score > best_score:
                best_score = score
                best_wf = wf

        # Confidence threshold
        if best_score >= 0.4:
            return best_wf, entities, min(1.0, best_score)
        return None, entities, 0.0

    def get_scoped_tools(self, workflow_id: Optional[str]) -> Optional[List[str]]:
        """Return the list of tool names approved for this specific workflow."""
        if not workflow_id:
            return None
        wf = self.get(workflow_id)
        if not wf:
            return None
        return list(wf.required_capabilities)

    def _register_reference_workflows(self) -> None:
        """Register the five foundational reference workflows (WF01 to WF05)."""

        # --------------------------------------------------------------------
        # WF01 — Structure Acquisition
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF01",
            name="Structure Acquisition",
            description="Download structure by PDB ID or load local molecular file, verify atom loading, and apply standard styling.",
            user_intents=[
                "download", "fetch", "get pdb", "open pdb", "load pdb",
                "tải về", "tải cấu trúc", "mở pdb", "tải pdb", "download pdb"
            ],
            intent_patterns=[
                r"(?:download|fetch|tải về|tải)\s+(?:pdb\s+)?([0-9][a-zA-Z0-9]{3}|af-[a-zA-Z0-9]+-f\d+)",
                r"(?:open|mở)\s+(?:cấu trúc\s+)?([0-9][a-zA-Z0-9]{3})"
            ],
            required_inputs=["pdb_id"],
            required_capabilities=[
                "fetch_structure", "load_structure", "count_atoms",
                "get_object_info", "show_representation", "color_selection",
                "orient_selection", "list_objects"
            ],
            steps=[
                WorkflowStep(1, "Resolve PDB Identifier", "Validate format of 4-character PDB code or AlphaFold ID", "fetch_structure"),
                WorkflowStep(2, "Fetch Structure", "Download coordinate file directly from RCSB PDB without collision overwrite", "fetch_structure", postconditions=["object_exists"]),
                WorkflowStep(3, "Verify Atoms & Chains", "Ensure non-zero atoms and enumerate loaded chains", "get_object_info", postconditions=["atom_count_gt_zero"]),
                WorkflowStep(4, "Apply Visualization", "Display cartoon representation and color by secondary structure or chain", "show_representation"),
                WorkflowStep(5, "Orient Camera", "Re-orient viewport along principal inertia axes", "orient_selection")
            ],
            validation_criteria={
                "precondition": "Valid 4-character PDB ID or accessible local file",
                "postcondition": "Target object exists in PyMOL with count_atoms > 0",
                "gate": "Network fetch must return status == 200 equivalent before subsequent tools execute"
            },
            error_recovery="If PDB fetch fails with 404, verify accession spelling. If network timeout occurs, inform user and do not retry invalid ID.",
            cancellation_behavior="Delete half-loaded object if user cancels during fetch.",
            expected_outputs=["object_name", "atom_count", "chains", "ligands"],
            scientific_limitations=[
                "PDB coordinates represent crystallographic or cryo-EM models; disordered loops may have missing electron density.",
                "Residue numbering follows author PDB convention and may differ from canonical UniProt sequence numbering."
            ]
        ))

        # --------------------------------------------------------------------
        # WF02 — Structural Inspection
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF02",
            name="Structural Inspection",
            description="Inspect loaded structures, detailing chains, atom counts, heteroatoms, ligands, secondary structure, and missing features.",
            user_intents=[
                "describe", "inspect", "summary", "features", "overview", "report",
                "mô tả", "kiểm tra", "tổng quan", "đặc điểm", "thông tin cấu trúc",
                "structural features", "loaded protein"
            ],
            intent_patterns=[
                r"(?:describe|mô tả|inspect|kiểm tra)\s+(?:the\s+)?(?:loaded\s+)?(?:protein|structure|cấu trúc|object|phân tử)",
                r"(?:summary|tổng quan|overview)\s+(?:of\s+)?(?:the\s+)?(?:loaded\s+)?(?:protein|structure)"
            ],
            required_inputs=[],
            required_capabilities=[
                "list_objects", "get_object_info", "get_chains", "get_residues",
                "get_structure_summary", "count_atoms", "color_selection"
            ],
            steps=[
                WorkflowStep(1, "Enumerate Objects", "Discover loaded molecular objects in PyMOL session", "list_objects", preconditions=["objects_exist"]),
                WorkflowStep(2, "Extract Macro-Statistics", "Query total atoms, protein/nucleic atoms, solvent, and inorganic ions", "get_object_info"),
                WorkflowStep(3, "Identify Chains & Sequences", "Extract unique chain IDs and polymer residue lengths", "get_chains"),
                WorkflowStep(4, "Detect Ligands & Heteroatoms", "Identify non-polymer organic ligands and cofactor residues", "get_object_info"),
                WorkflowStep(5, "Synthesize Overview", "Summarize structural topology and report any detectable gaps or missing residues", "get_structure_summary")
            ],
            validation_criteria={
                "precondition": "At least one molecular object loaded in PyMOL session",
                "postcondition": "Non-empty summary reporting atom counts, chains, and ligands"
            },
            error_recovery="If no structures are loaded, prompt user to download or load a structure first.",
            cancellation_behavior="Immediate clean abort.",
            expected_outputs=["total_atoms", "chains", "ligands", "bounding_box"],
            scientific_limitations=[
                "Inspection is geometric and based on coordinate metadata; does not infer biological activity without experimental assays."
            ]
        ))

        # --------------------------------------------------------------------
        # WF03 — Structure Comparison & Alignment
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF03",
            name="Structure Comparison",
            description="Superimpose two protein structures, calculate RMSD, identify divergent regions, and report alignment coverage.",
            user_intents=[
                "compare", "align", "rmsd", "superimpose", "structural alignment",
                "so sánh", "căn chỉnh", "tính rmsd", "chồng khớp"
            ],
            intent_patterns=[
                r"(?:compare|so sánh)\s+(?:these\s+)?(?:two\s+)?(?:proteins|structures|cấu trúc)",
                r"(?:align|căn chỉnh|superimpose)\s+(?:structure\s+)?\w+\s+(?:with|to|onto|và)\s+\w+",
                r"(?:calculate|tính)\s+rmsd"
            ],
            required_inputs=["mobile", "target"],
            required_capabilities=[
                "list_objects", "get_chains", "align_structures", "calculate_rmsd",
                "compare_residues", "color_selection", "export_analysis_json"
            ],
            steps=[
                WorkflowStep(1, "Resolve Comparison Targets", "Identify mobile and reference target objects from session", "list_objects", preconditions=["two_or_more_objects"]),
                WorkflowStep(2, "Verify Chain Compatibility", "Inspect chain identities in both structures", "get_chains"),
                WorkflowStep(3, "Execute Structural Alignment", "Align mobile onto target using sequence-informed 'align' or structural 'super'", "align_structures"),
                WorkflowStep(4, "Compute Strict C-alpha RMSD", "Measure coordinate displacement across aligned residue pairs", "calculate_rmsd"),
                WorkflowStep(5, "Identify Divergent Loci", "Locate residues with significant spatial displacement (> threshold)", "compare_residues"),
                WorkflowStep(6, "Visualize Superimposition", "Color structures distinctly to highlight conformational differences", "color_selection")
            ],
            validation_criteria={
                "precondition": "At least 2 distinct objects loaded in PyMOL",
                "postcondition": "Valid RMSD floating-point measurement (> 0.0) and aligned atom count > 0"
            },
            error_recovery="If sequence-informed 'align' fails due to low sequence homology (<30%), automatically fall back to structure-based 'super'.",
            cancellation_behavior="Preserve original coordinates if alignment is cancelled before completion.",
            expected_outputs=["rmsd_post_refinement", "aligned_atoms", "divergent_residues"],
            scientific_limitations=[
                "PyMOL 'align' performs outlier rejection cycles by default; reported post-refinement RMSD reflects the retained core atoms.",
                "Unrefined all-atom or C-alpha RMSD should be reported alongside aligned atom counts for rigorous comparability."
            ]
        ))

        # --------------------------------------------------------------------
        # WF04 — Mutation Neighborhood Analysis
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF04",
            name="Mutation Neighborhood",
            description="Analyze point mutation position, verify wildtype residue, measure spatial contact neighborhood, and visualize local locus.",
            user_intents=[
                "mutation", "analyze mutation", "neighborhood", "variant",
                "đột biến", "phân tích đột biến", "lân cận", "vùng lân cận"
            ],
            intent_patterns=[
                r"(?:analyze|phân tích)\s+(?:mutation|đột biến)\s+([A-Za-z]{1,3}\d+[A-Za-z]{1,3})",
                r"(?:mutation|đột biến)\s+([A-Za-z]{1,3}\d+[A-Za-z]{1,3})",
                r"residues?\s+within\s+\d+\s*(?:a|angstroms?|å)\s+of\s+(?:residue\s+)?\w+"
            ],
            required_inputs=["mutation_notation"],
            required_capabilities=[
                "list_objects", "analyze_mutation", "identify_mutations",
                "find_nearby_residues", "find_polar_contact_candidates",
                "highlight_residues", "label_residues", "orient_selection"
            ],
            steps=[
                WorkflowStep(1, "Parse Mutation Notation", "Extract wildtype residue, sequence position, mutant amino acid, and chain", "analyze_mutation"),
                WorkflowStep(2, "Validate Wildtype in Structure", "Verify that the amino acid at the specified position matches wildtype", "analyze_mutation"),
                WorkflowStep(3, "Measure Spatial Neighborhood", "Identify all residues within cutoff distance (default 5.0 Å) of the mutation site", "find_nearby_residues"),
                WorkflowStep(4, "Find Geometric Polar Contacts", "Identify candidate donor/acceptor pairs (distance <= 3.5 Å)", "find_polar_contact_candidates"),
                WorkflowStep(5, "Render Visual Highlighting", "Display mutation site as sticks/spheres with labels and local neighborhood context", "highlight_residues"),
                WorkflowStep(6, "Orient on Mutation Site", "Center and zoom viewport onto the mutation locus", "orient_selection")
            ],
            validation_criteria={
                "precondition": "Target protein loaded in session and residue position exists",
                "postcondition": "Verified wildtype match or explicit discrepancy report, plus contact residue list"
            },
            error_recovery="If wildtype amino acid does not match sequence position, report the actual residue found in the PDB rather than failing silently.",
            cancellation_behavior="Clear temporary selections on cancel.",
            expected_outputs=["wildtype_match", "residue_neighborhood", "polar_contacts"],
            scientific_limitations=[
                "Distance-based polar contacts (<= 3.5 Å) are geometric donor-acceptor approximations, not confirmed physical hydrogen bonds.",
                "Geometric proximity does NOT establish thermodynamic delta-delta-G or functional pathogenicity without validated biophysical modeling."
            ]
        ))

        # --------------------------------------------------------------------
        # WF05 — Publication Visualization
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF05",
            name="Publication Visualization",
            description="Prepare publication-grade molecular rendering with publication preset, white background, optimal camera orientation, and export.",
            user_intents=[
                "publication", "figure", "render", "export image", "high quality", "clean figure",
                "chất lượng xuất bản", "xuất hình", "chụp ảnh", "kết xuất hình ảnh"
            ],
            intent_patterns=[
                r"(?:prepare|tạo|chuẩn bị)\s+(?:a\s+)?(?:publication|chất lượng xuất bản|figure|hình ảnh)",
                r"(?:render|export)\s+(?:a\s+)?(?:high-res|figure|png|image)"
            ],
            required_inputs=[],
            required_capabilities=[
                "list_objects", "apply_visualization_preset", "show_representation",
                "color_selection", "set_background", "set_transparency",
                "orient_selection", "zoom_selection", "export_png", "save_session", "export_pml"
            ],
            steps=[
                WorkflowStep(1, "Assess Structure Focus", "Inspect loaded objects and active selections", "list_objects", preconditions=["objects_exist"]),
                WorkflowStep(2, "Apply Publication Preset", "Set clean cartoon representation with distinct chain coloring or binding site focus", "apply_visualization_preset"),
                WorkflowStep(3, "Configure High-Contrast Environment", "Set background to pure white for journal publication standards", "set_background"),
                WorkflowStep(4, "Optimize Camera Viewport", "Orient view along principal axes and apply framing buffer", "orient_selection"),
                WorkflowStep(5, "Ray-Trace & Export PNG", "Render high-resolution figure (1920x1080) with PyMOL ray-tracing engine", "export_png"),
                WorkflowStep(6, "Export Reproducible Script & Session", "Save session state (.pse) and reproducible PyMOL command script (.pml)", "export_pml")
            ],
            validation_criteria={
                "precondition": "At least one structure loaded in PyMOL session",
                "postcondition": "Exported PNG file exists on disk and is non-empty (>0 bytes)"
            },
            error_recovery="If ray-tracing encounters memory or driver limitations, fall back to OpenGL viewport capture (`ray=False`).",
            cancellation_behavior="Preserve previous camera view and settings if cancelled.",
            expected_outputs=["png_path", "pse_path", "pml_path"],
            scientific_limitations=[
                "Publication figures represent static molecular models; molecular surfaces are calculated based on chosen solvent probe radius (default 1.4 Å)."
            ]
        ))

        # --------------------------------------------------------------------
        # WF06 — Ligand Interaction Analysis
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF06",
            name="Ligand Interaction Analysis",
            description="Identify biologically relevant bound ligands, distinguish from additives, calculate minimum heavy-atom distances and polar contacts, and visualize pocket.",
            user_intents=[
                "ligand", "binding pocket", "ligand contacts", "interact", "pocket",
                "tương tác ligand", "túi gắn", "phân tích ligand", "chất chủ vận", "chất ức chế", "ligand interactions"
            ],
            intent_patterns=[
                r"(?:analyze|inspect|phân tích|xem)\s+(?:the\s+)?(?:ligand|pocket|túi gắn|binding site)",
                r"(?:ligand|chất gắn)\s+([a-zA-Z0-9]{1,5})\s+(?:interaction|contacts|tương tác)"
            ],
            required_inputs=[],
            required_capabilities=[
                "list_objects", "get_chains", "identify_ligands", "analyze_ligand_interactions",
                "visualize_ligand_pocket", "export_ligand_contacts"
            ],
            steps=[
                WorkflowStep(1, "Discover Ligands", "Identify bound organic ligands excluding solvent and common additives", "identify_ligands"),
                WorkflowStep(2, "Analyze Pocket Contacts", "Compute minimum heavy-atom distances and geometric polar contact candidates", "analyze_ligand_interactions"),
                WorkflowStep(3, "Visualize Pocket", "Render pocket sticks with dashed polar contacts and centered view", "visualize_ligand_pocket")
            ],
            validation_criteria={
                "precondition": "Target protein structure loaded with at least one bound ligand",
                "postcondition": "Contacting residue table and polar contact candidates computed"
            },
            error_recovery="If no organic ligand is found, report all detected heteroatoms and prompt user.",
            cancellation_behavior="Restore original protein representation on cancel.",
            expected_outputs=["ligand_resn", "contacting_residues_count", "polar_contacts_count", "contacts"],
            scientific_limitations=[
                "Geometric proximity (< 4.0 Å) indicates structural neighborhood and geometric polar contact candidates, but does NOT constitute thermodynamic proof of binding affinity or free energy."
            ]
        ))

        # --------------------------------------------------------------------
        # WF07 — Solvent Accessibility Analysis
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF07",
            name="Solvent Accessibility Analysis",
            description="Calculate total and per-residue solvent-accessible surface area (SASA, Å²) and relative solvent accessibility (RSA, %) using PyMOL's native dot-solvent engine.",
            user_intents=[
                "sasa", "solvent accessibility", "surface area", "rsa", "buried residues", "exposed residues",
                "diện tích tiếp xúc dung môi", "độ bộc lộ", "vùng vùi", "khả năng tiếp cận dung môi"
            ],
            intent_patterns=[
                r"(?:calculate|tính)\s+(?:sasa|solvent accessibility|diện tích tiếp xúc dung môi)",
                r"(?:map|hiển thị)\s+(?:sasa|accessibility|độ bộc lộ)"
            ],
            required_inputs=[],
            required_capabilities=[
                "list_objects", "calculate_sasa", "map_sasa_to_structure", "compare_sasa", "export_sasa_table"
            ],
            steps=[
                WorkflowStep(1, "Calculate SASA", "Compute absolute SASA (Å²) and relative accessibility (RSA %) per residue", "calculate_sasa"),
                WorkflowStep(2, "Map to Structure", "Load SASA values into B-factors and color molecular surface with accessibility spectrum", "map_sasa_to_structure")
            ],
            validation_criteria={
                "precondition": "At least one structure loaded in session",
                "postcondition": "Total SASA > 0 Å² and residue accessibility breakdown populated"
            },
            error_recovery="Ensure dot_solvent=1 and valid probe radius (1.4 Å).",
            cancellation_behavior="Reset B-factor coloring on cancel.",
            expected_outputs=["total_sasa_angstrom2", "buried_residues_count", "exposed_residues_count"],
            scientific_limitations=[
                "SASA represents a static snapshot; dynamic breathing and crystal packing can alter accessibility in solution."
            ]
        ))

        # --------------------------------------------------------------------
        # WF08 — Epitope Structural Mapping
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF08",
            name="Epitope Structural Mapping",
            description="Map linear epitope sequences or residue lists to 3D structure, evaluate spatial clustering and solvent accessibility, and generate publication-grade figures.",
            user_intents=[
                "epitope", "linear epitope", "map epitope", "antigen", "conformational epitope",
                "kháng nguyên", "biểu vị", "ánh xạ epitope", "đoạn epitope", "vùng epitope"
            ],
            intent_patterns=[
                r"(?:map|ánh xạ)\s+(?:the\s+)?(?:epitope|biểu vị|peptide)\s+([a-zA-Z]+)",
                r"(?:epitope|biểu vị)\s+(?:mapping|phân tích)"
            ],
            required_inputs=["epitope_sequence"],
            required_capabilities=[
                "list_objects", "get_chains", "map_epitope_sequence", "visualize_epitope", "calculate_sasa"
            ],
            steps=[
                WorkflowStep(1, "Map Sequence to 3D Coordinates", "Resolve chain and residue sequence offsets in loaded model", "map_epitope_sequence"),
                WorkflowStep(2, "Analyze Presentation & Accessibility", "Compute spatial clustering diameter and residue RSA", "map_epitope_sequence"),
                WorkflowStep(3, "Visualize Epitope", "Highlight epitope on molecular surface with contrasting presentation", "visualize_epitope")
            ],
            validation_criteria={
                "precondition": "Target protein loaded and linear sequence exists in protein chains",
                "postcondition": "1-to-1 residue correspondence mapped with spatial centroid calculated"
            },
            error_recovery="If sequence is not found in chain A, search remaining chains before failing.",
            cancellation_behavior="Clear epitope highlight on cancel.",
            expected_outputs=["mapped_residues_count", "residue_numbers", "spatial_centroid", "is_spatially_clustered"],
            scientific_limitations=[
                "Surface exposure alone does NOT establish antigenicity, antibody binding affinity, or in vivo immunogenicity without serological assays."
            ]
        ))

        # --------------------------------------------------------------------
        # WF09 — WT–Mutant Structural Comparison
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF09",
            name="WT–Mutant Structural Comparison",
            description="Perform sequence-aware alignment of WT and mutant structures, compare local residue environments, contact networks, and quantify geometric deviations.",
            user_intents=[
                "wt vs mutant", "compare mutant", "wildtype mutant", "mutant structure",
                "so sánh đột biến", "đột biến so với wildtype", "đối chiếu cấu trúc đột biến", "so sánh wt và mutant"
            ],
            intent_patterns=[
                r"(?:compare|so sánh)\s+(?:wt|wildtype|wild-type)\s+(?:and|vs|với)\s+(?:mutant|đột biến)",
                r"(?:compare|so sánh)\s+(?:cấu trúc\s+)?(?:đột biến|mutant).*?(?:với|with|vs|and)\s+(?:wildtype|wt|wild-type)",
                r"(?:mutation|đột biến)\s+(?:structural comparison|đối chiếu cấu trúc|so sánh)"
            ],
            required_inputs=["wildtype_object", "mutant_object"],
            required_capabilities=[
                "list_objects", "compare_wt_mutant", "align_structures", "calculate_rmsd", "show_representation", "color_selection"
            ],
            steps=[
                WorkflowStep(1, "Superimpose Structures", "Sequence-aware alignment of mutant onto wild-type model", "compare_wt_mutant"),
                WorkflowStep(2, "Local Environment & Contact Deltas", "Measure C-alpha displacement and analyze gained/lost contacts", "compare_wt_mutant")
            ],
            validation_criteria={
                "precondition": "Both wild-type and mutant structures loaded in PyMOL session",
                "postcondition": "Global RMSD, C-alpha displacement, and contact network comparison calculated"
            },
            error_recovery="Do not fabricate missing coordinates if mutant residue is not modeled.",
            cancellation_behavior="Reset object colors on cancel.",
            expected_outputs=["global_chain_rmsd_angstrom", "ca_displacement_angstrom", "wildtype_neighbors_count", "mutant_neighbors_count"],
            scientific_limitations=[
                "Never claim a mutation alters protein stability (ddG) or biological function based on geometric structural differences alone."
            ]
        ))

        # --------------------------------------------------------------------
        # WF10 — Batch Structural Analysis
        # --------------------------------------------------------------------
        self.register(WorkflowDefinition(
            workflow_id="WF10",
            name="Batch Structural Analysis",
            description="Perform consistent pairwise structural alignments across a batch of structures against a common reference, exporting structured comparison tables and overlay figures.",
            user_intents=[
                "batch", "batch align", "compare multiple", "ensemble", "multiple structures",
                "hàng loạt", "so sánh hàng loạt", "nhiều cấu trúc", "so sánh tập hợp", "đồng thời nhiều cấu trúc"
            ],
            intent_patterns=[
                r"(?:batch|hàng loạt)\s+(?:compare|alignment|căn chỉnh|so sánh)",
                r"(?:align|so sánh)\s+(?:all|multiple|tất cả|nhiều)\s+(?:structures|cấu trúc)"
            ],
            required_inputs=["structure_names"],
            required_capabilities=[
                "list_objects", "batch_compare_structures", "export_analysis_csv", "export_analysis_json"
            ],
            steps=[
                WorkflowStep(1, "Batch Pairwise Superposition", "Align each structure individually against designated reference", "batch_compare_structures"),
                WorkflowStep(2, "Export Comparative Metrics", "Export structured comparison table (CSV, JSON) and multi-overlay figure", "batch_compare_structures")
            ],
            validation_criteria={
                "precondition": "At least 2 structures loaded (up to 20 maximum)",
                "postcondition": "Consistent pairwise metrics computed across all structures in batch"
            },
            error_recovery="Skip structures with incompatible chain selections while continuing the rest of the batch.",
            cancellation_behavior="Clean abort after current pair completes.",
            expected_outputs=["reference_structure", "total_structures_analyzed", "results", "exported_files"],
            scientific_limitations=[
                "Pairwise rigid-body fitting against a single reference does not replace multimeric assembly analysis or flexible ensemble clustering."
            ]
        ))


GLOBAL_WORKFLOW_REGISTRY = WorkflowRegistry()
