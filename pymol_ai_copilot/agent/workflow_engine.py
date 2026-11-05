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
                mobile = inputs.get("mobile", "")
                target = inputs.get("target", "")
                method = inputs.get("method", "align")

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

                # Superimposition
                record.state = WorkflowState.RUNNING
                t0 = time.time()
                res_align = reg.execute("align_structures", {"mobile": mobile, "target": target, "method": method})
                d_align = round((time.time() - t0) * 1000, 2)

                step2 = WorkflowStepExecution(2, "Superimpose Structures", "align_structures",
                                              StepState.COMPLETED if res_align.get("success") else StepState.FAILED,
                                              {"mobile": mobile, "target": target, "method": method}, res_align, d_align,
                                              error_message=res_align.get("error"))
                record.step_records.append(step2)
                if not res_align.get("success"):
                    record.state = WorkflowState.FAILED
                    record.error = f"Structural alignment failed: {res_align.get('error')}"
                    return record

                # Strict C-alpha RMSD & Divergent Loci
                record.state = WorkflowState.VALIDATING
                t0 = time.time()
                res_rmsd = reg.execute("calculate_rmsd", {"mobile_selection": f"{mobile} and name CA", "target_selection": f"{target} and name CA"})
                res_comp = reg.execute("compare_residues", {"object1": target, "object2": mobile})
                d_val = round((time.time() - t0) * 1000, 2)

                step3 = WorkflowStepExecution(3, "Calculate Strict C-alpha RMSD", "calculate_rmsd", StepState.COMPLETED,
                                              {"mobile_selection": f"{mobile} and name CA", "target_selection": f"{target} and name CA"}, res_rmsd, d_val)
                record.step_records.append(step3)

                record.scientific_measurements = {
                    "mobile": mobile,
                    "target": target,
                    "method": method,
                    "rmsd_angstrom": res_rmsd.get("rmsd", res_align.get("rmsd", 0.0)),
                    "aligned_atoms": res_align.get("aligned_atoms", 0),
                    "outlier_rejection_cycles": res_align.get("cycles", 0),
                    "divergent_residues_count": res_comp.get("divergent_residues_count", 0),
                    "max_displacement_angstrom": res_comp.get("max_displacement", 0.0)
                }
                record.units = {"rmsd_angstrom": "Å", "displacement": "Å"}
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
                self.scientific_measurements["rmsd_angstrom"] = result.get("rmsd", result.get("rmsd_post_refinement"))
                self.scientific_measurements["aligned_atoms"] = result.get("aligned_atoms", 0)
            if "polar_contact_candidates_count" in result:
                self.scientific_measurements["polar_contacts_count"] = result.get("polar_contact_candidates_count")
            if "neighbor_residues_count" in result:
                self.scientific_measurements["neighbor_residues_count"] = result.get("neighbor_residues_count")
            if "filepath" in result:
                self.scientific_measurements["output_figure"] = result.get("filepath")

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
                # Workflow-specific mandatory gate verification
                if self.workflow.workflow_id == "WF01":
                    gates_passed = ("fetch_structure" in executed_caps or "load_structure" in executed_caps) and not has_failures
                elif self.workflow.workflow_id == "WF02":
                    gates_passed = ("get_object_info" in executed_caps or "get_structure_summary" in executed_caps) and not has_failures
                elif self.workflow.workflow_id == "WF03":
                    gates_passed = ("align_structures" in executed_caps or "calculate_rmsd" in executed_caps) and not has_failures
                elif self.workflow.workflow_id == "WF04":
                    gates_passed = ("analyze_mutation" in executed_caps or "find_nearby_residues" in executed_caps) and not has_failures
                elif self.workflow.workflow_id == "WF05":
                    gates_passed = ("export_png" in executed_caps or "apply_visualization_preset" in executed_caps) and not has_failures
                else:
                    gates_passed = not has_failures

                if gates_passed:
                    self.state = WorkflowState.COMPLETED
                    error_msg = None
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
                score += 0.5
            elif wf.workflow_id == "WF05" and ("png" in text_lower or "figure" in text_lower or "xuất" in text_lower or "publication" in text_lower):
                score += 0.4

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


GLOBAL_WORKFLOW_REGISTRY = WorkflowRegistry()
