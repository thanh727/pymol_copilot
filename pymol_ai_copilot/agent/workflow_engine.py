"""
Scientific Workflow Engine for PyMOL AI Copilot.

Declaratively defines structured scientific workflows (WF01 to WF05+), provides entity
and intent resolution, context-dependent tool scoping, precondition/postcondition gates,
and scientific provenance tracking.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Tuple


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
