# PyMOL AI Copilot — Workflow Coverage & Capability Atlas

**Date:** November 2026  
**Environment:** PyMOL 3.1.0 Open-Source (Homebrew `arm64`), Python 3.14.3, macOS 27.2, Ollama (`qwen2.5-coder:7b`, `gemma4:latest`)  
**Baseline:** 488 discovered PyMOL API/PML functions | 35 authorized, typed tools | 5 reference workflows | 100% test pass rate  

---

## 1. Executive Summary

This document establishes the functional coverage, risk classification, and verification status for all scientific workflows and underlying PyMOL capabilities in the **PyMOL AI Copilot** agentic system.

In compliance with the project's security architecture:
1. **Discovery does NOT imply authorization:** All 488 discovered PyMOL APIs default to `LLM-disallowed`.
2. **Context-Dependent Tool Scoping:** Instead of exposing all tools to the LLM on every prompt, the `WorkflowRegistry` matches user intent and session context to activate scoped subsets of approved capabilities.
3. **Scientific Reliability:** Purely spatial/geometric contacts ($\le 3.5\text{ \AA}$ or $\le 5.0\text{ \AA}$) are explicitly classified as geometric approximations and distinguished from experimentally validated physical interactions or free energy changes.

---

## 2. Implemented & Verified Scientific Workflows

The following five reference workflows are fully implemented, tested in headless PyMOL, and validated with local Ollama models:

| Workflow ID | Name | User Intent Keywords | Required Capabilities | Verification Status |
| :---: | :--- | :--- | :--- | :---: |
| **WF01** | **Structure Acquisition** | `download`, `fetch`, `load pdb`, `tải về`, `tải cấu trúc`, `mở pdb` | `fetch_structure`, `load_structure`, `count_atoms`, `get_object_info`, `show_representation`, `color_selection`, `orient_selection` | **Implemented & Tested** |
| **WF02** | **Structural Inspection** | `describe`, `inspect`, `summary`, `features`, `mô tả`, `kiểm tra`, `tổng quan` | `list_objects`, `get_object_info`, `get_chains`, `get_residues`, `get_structure_summary`, `count_atoms` | **Implemented & Tested** |
| **WF03** | **Structure Comparison** | `compare`, `align`, `rmsd`, `superimpose`, `so sánh`, `căn chỉnh`, `tính rmsd` | `list_objects`, `get_chains`, `align_structures`, `calculate_rmsd`, `compare_residues`, `color_selection`, `export_analysis_json` | **Implemented & Tested** |
| **WF04** | **Mutation Neighborhood** | `mutation`, `analyze mutation`, `neighborhood`, `đột biến`, `phân tích đột biến`, `lân cận` | `list_objects`, `analyze_mutation`, `identify_mutations`, `find_nearby_residues`, `find_polar_contact_candidates`, `highlight_residues`, `label_residues`, `orient_selection` | **Implemented & Tested** |
| **WF05** | **Publication Visualization** | `publication`, `figure`, `render`, `export image`, `chất lượng xuất bản`, `xuất hình`, `chụp ảnh` | `apply_visualization_preset`, `show_representation`, `color_selection`, `set_background`, `set_transparency`, `orient_selection`, `zoom_selection`, `export_png`, `save_session`, `export_pml` | **Implemented & Tested** |

### Detailed Workflow Architecture:

#### WF01 — Structure Acquisition
- **Intent Recognition:** Regex pattern `(?:download|fetch|tải về|tải)\s+(?:pdb\s+)?([0-9][a-zA-Z0-9]{3}|af-[a-zA-Z0-9]+-f\d+)`.
- **Precondition Gates:** Valid 4-character PDB code or valid local molecular file path.
- **Deterministic Steps:**
  1. Validate accession syntax and format (`cif` default).
  2. Call `fetch_structure` via `PyMOLExecutor.run_safe(async_=0)`.
  3. Verify object presence in PyMOL session (`cmd.get_names`) and verify `atom_count > 0`.
  4. Query chains, atom breakdown, and detect organic ligands (e.g. `AP5` in 1AKE).
  5. Apply standard cartoon styling and orient camera along principal inertia axes.
- **Postcondition Gates:** Object exists in session; non-zero atom count verified.

#### WF02 — Structural Inspection
- **Intent Recognition:** Regex pattern `(?:describe|mô tả|inspect|kiểm tra)\s+(?:the\s+)?(?:loaded\s+)?(?:protein|structure|cấu trúc|object)`.
- **Precondition Gates:** At least one molecular object loaded in session.
- **Deterministic Steps:**
  1. Discover all active objects and named selections.
  2. Compute macro-statistics: total atoms, protein atoms, nucleic atoms, solvent molecules, and inorganic ions.
  3. Enumerate chains and extract full residue sequences with insertion code support.
  4. Classify non-polymer heteroatoms and organic ligands.
  5. Synthesize high-level structural summary including bounding box dimensions.
- **Postcondition Gates:** Structured inventory returned; detectable gaps or missing residues flagged.

#### WF03 — Structure Comparison & Alignment
- **Intent Recognition:** Keywords `compare`, `align`, `rmsd`, `so sánh`, `căn chỉnh`.
- **Precondition Gates:** Requires $\ge 2$ distinct loaded molecular objects.
- **Deterministic Steps:**
  1. Resolve mobile and target structures.
  2. Select alignment algorithm: `align` (sequence-informed refinement), `super` (structural superposition), or `cealign` (combinatorial extension).
  3. Superimpose mobile onto target with outlier rejection cycles ($2.0\text{ \AA}$ cutoff, 5 cycles).
  4. Measure strict unrefined coordinate $C\alpha$ RMSD.
  5. Identify divergent residue positions ($> 1.5\text{ \AA}$ displacement).
  6. Color structures distinctly and export structured analysis to JSON.
- **Postcondition Gates:** Floating-point RMSD value calculated; aligned atom count $> 0$.

#### WF04 — Mutation Neighborhood Analysis
- **Intent Recognition:** Regex pattern `\b(?:chain\s+([A-Za-z0-9])\s*:?\s*)?([A-Z][a-z]{0,2})[-_: ]?(\d+)[-_: ]?([A-Z][a-z]{0,2})\b`.
- **Precondition Gates:** Target protein loaded and specified residue position exists.
- **Deterministic Steps:**
  1. Parse mutation notation (wildtype, position, mutant, chain).
  2. Validate wildtype residue identity in loaded PDB model.
  3. Extract all spatial neighbor residues within radius (default $5.0\text{ \AA}$).
  4. Identify geometric polar contact candidates ($\le 3.5\text{ \AA}$ donor-acceptor pairs).
  5. Highlight mutation site as sticks/spheres with labels and local context sticks.
  6. Orient and zoom camera directly onto the mutation locus.
- **Postcondition Gates:** Verified wildtype match or explicit discrepancy warning; neighbor residue list populated.

#### WF05 — Publication Visualization
- **Intent Recognition:** Keywords `publication`, `figure`, `high quality`, `chất lượng xuất bản`, `xuất hình`.
- **Precondition Gates:** At least one molecular object loaded in session.
- **Deterministic Steps:**
  1. Inspect loaded objects and active selections.
  2. Apply coordinated publication preset (`cartoon_by_chain`, `binding_pocket`, `mutation_neighborhood`, `epitope`).
  3. Configure pure white background (`set_background(color="white")`).
  4. Orient camera along principal axes and apply framing buffer.
  5. Render high-resolution figure ($1920\times 1080$, 300 DPI) with PyMOL ray tracing.
  6. Export reproducible session state (`.pse`) and command macro script (`.pml`).
- **Postcondition Gates:** Output PNG and session files exist on disk with file size $> 0$ bytes.

---

## 3. Tool Coverage & PyMOL API Mapping

All 35 registered tools map directly to underlying PyMOL APIs and are cataloged in `CapabilityRegistry`:

| Tool Name | Capability ID | Underlying API | Risk Tier | Classification |
| :--- | :--- | :--- | :---: | :--- |
| `fetch_structure` | `io.fetch_structure` | `cmd.fetch` | Tier C | Bounded I/O |
| `load_structure` | `io.load_structure` | `cmd.load` | Tier C | Bounded I/O |
| `save_session` | `io.save_session` | `cmd.save` | Tier C | Bounded I/O |
| `export_png` | `io.export_png` | `cmd.png` / `cmd.ray` | Tier C | Bounded I/O |
| `export_pml` | `io.export_pml` | Script recorder | Tier C | Bounded I/O |
| `export_analysis_json` | `io.export_analysis_json` | `json.dump` | Tier C | Bounded I/O |
| `export_analysis_csv` | `io.export_analysis_csv` | `csv.DictWriter` | Tier C | Bounded I/O |
| `list_objects` | `session.list_objects` | `cmd.get_names` | Tier A | Read-Only |
| `get_chains` | `inspect.get_chains` | `cmd.get_chains` | Tier A | Read-Only |
| `count_atoms` | `inspect.count_atoms` | `cmd.count_atoms` | Tier A | Read-Only |
| `get_residues` | `inspect.get_residues` | `cmd.iterate` | Tier A | Read-Only |
| `get_selection_info` | `inspect.get_selection_info` | `cmd.iterate` | Tier A | Read-Only |
| `get_object_info` | `inspect.get_object_info` | `cmd.count_atoms` + `cmd.get_extent` | Tier A | Read-Only |
| `get_structure_summary` | `inspect.get_structure_summary` | Composite inspector | Tier A | Read-Only |
| `select_residues` | `selection.select_residues` | `cmd.select` | Tier B | View-Only |
| `show_representation` | `view.show_representation` | `cmd.show` / `cmd.show_as` | Tier B | View-Only |
| `hide_representation` | `view.hide_representation` | `cmd.hide` | Tier B | View-Only |
| `color_selection` | `view.color_selection` | `cmd.color` / `cmd.spectrum` | Tier B | View-Only |
| `highlight_residues` | `view.highlight_residues` | `cmd.show` + `cmd.color` | Tier B | View-Only |
| `set_transparency` | `view.set_transparency` | `cmd.set transparency` | Tier B | View-Only |
| `label_residues` | `view.label_residues` | `cmd.label` | Tier B | View-Only |
| `apply_visualization_preset` | `view.apply_visualization_preset` | Composite presets | Tier B | View-Only |
| `orient_selection` | `camera.orient_selection` | `cmd.orient` | Tier B | View-Only |
| `zoom_selection` | `camera.zoom_selection` | `cmd.zoom` | Tier B | View-Only |
| `reset_view` | `camera.reset_view` | `cmd.reset` | Tier B | View-Only |
| `set_background` | `camera.set_background` | `cmd.bg_color` | Tier B | View-Only |
| `calculate_distances` | `geometry.calculate_distances` | `cmd.distance` + NumPy | Tier A | Read-Only |
| `find_nearby_residues` | `geometry.find_nearby_residues` | `cmd.iterate` + selection | Tier A | Read-Only |
| `find_polar_contact_candidates` | `geometry.find_polar_contact_candidates` | `cmd.distance` + geometry | Tier A | Read-Only |
| `inspect_binding_pocket` | `geometry.inspect_binding_pocket` | Composite pocket analysis | Tier A | Read-Only |
| `align_structures` | `align.align_structures` | `cmd.align` / `super` / `cealign` | Tier A | Read-Only |
| `calculate_rmsd` | `align.calculate_rmsd` | `cmd.rms_cur` / `cmd.align` | Tier A | Read-Only |
| `compare_residues` | `align.compare_residues` | NumPy distance matrix | Tier A | Read-Only |
| `identify_mutations` | `align.identify_mutations` | Sequence alignment + coords | Tier A | Read-Only |
| `analyze_mutation` | `mutation.analyze_mutation` | Inspector + contacts | Tier A | Read-Only |

---

## 4. Unsupported & Blocked Capabilities (Tier X)

The following 15 discovered API functions are classified as **Tier X (Dangerous)** and are permanently blocked from autonomous execution:

```text
cmd.do              - Arbitrary PML script execution (Code injection hazard)
cmd.system          - Arbitrary shell execution
cmd.python          - Arbitrary Python interpreter evaluation
cmd.extend          - Command language monkey-patching
cmd.extendaa        - Command language extension
cmd.alias           - Command alias manipulation
cmd.quit            - Application termination
cmd.reinitialize    - Complete session wiping without confirmation
cmd.log_open        - Arbitrary file log writing
cmd.log_close       - Log stream termination
cmd.log_append      - Log stream appending
cmd.log_resume      - Log stream manipulation
eval() / exec()     - Dynamic runtime execution
```

Any attempt by an LLM to request these callables results in an immediate deterministic rejection:
`Tool is not an authorized capability. All unreviewed PyMOL APIs default to LLM-disallowed.`

---

## 5. Planned Capability Extensions (R3 & R4 Roadmap)

| Capability Domain | Candidate Operations | Target Workflow | Planned Risk Tier |
| :--- | :--- | :--- | :---: |
| **Surface & Accessibility** | `cmd.get_area`, `cmd.get_sasa_relative` | Relative residue SASA | Tier A (Read-Only) |
| **Maps & Volumetric** | `cmd.isomesh`, `cmd.isosurface`, `cmd.map_new` | Electron density contouring | Tier B (View-Only) |
| **States & Trajectories** | `cmd.load_traj`, `cmd.count_states`, `cmd.set_state` | Conformational ensemble browsing | Tier C (Bounded I/O) |
| **Crystallography & Symmetry** | `cmd.symexp`, `cmd.get_symmetry` | Unit cell & crystal packing | Tier B (View-Only) |

---

## 6. Verification Summary

- **Total Unit & Integration Tests:** 77 tests across 10 test modules.
- **Pass Rate:** $\mathbf{100\%}$ (0 failures, 0 errors).
- **Execution Speed:** $< 35\text{ seconds}$ for full headless + live Ollama suite.
