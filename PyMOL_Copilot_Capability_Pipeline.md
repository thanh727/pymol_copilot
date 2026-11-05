# PyMOL Open-Source AI Copilot — Capability Atlas & Pipeline Blueprint

**Prepared:** 2026-11-05  
**Target:** Existing Homebrew PyMOL Open-Source 3.1.0, Apple Silicon macOS, Python 3.14, Ollama local  
**Project:** `/Users/thanhnt/Desktop/GitHub/pymol_copilot`  
**Status:** Architecture/research and implementation specification, **not** a claim that these tools are already implemented.

## Executive decision

The previous Copilot implemented 33 tools (according to the provided Gemini report), but it failed even at `fetch 1ubq`: missing capability in the tool whitelist, then repeated the same invalid action. Do **not** solve this with an unrestricted `cmd.do()` or Python interpreter tool. Create an extensible, discoverable **Capability Catalog**, **typed PyMOL adapters**, **scientific workflows**, **planning/execution policy**, and **verification layer**.

**Important scope distinction:** The official PyMOL Command Reference documents command-language actions, the Python API exports other functions, and PyMOL's `cmd.keyword` maps PML commands. This blueprint categorizes documented functionality; for a genuinely exhaustive inventory **of the installed version**, run the companion `pymol_api_inventory.py` under the same Python interpreter used by PyMOL. That script inventories public `pymol.cmd` callables and `cmd.keyword` command names, but intentionally does not cover arbitrary private C extensions, the complete settings database, third-party plugins or every Qt GUI action. Never auto-authorize an enumerated function.

## 1. Sources and evidence

1. **Official open-source repository**: https://github.com/schrodinger/pymol-open-source
2. **Public command reference**: https://pymol.org/pymol-command-ref.html
3. **Command categories**: https://pymolwiki.org/index.php/Category:Commands
4. **API exports**: https://github.com/schrodinger/pymol-open-source/blob/master/modules/pymol/api.py
5. **Command registry**: https://github.com/schrodinger/pymol-open-source/blob/master/modules/pymol/keywords.py
6. **cmd module and keyword initialization**: https://github.com/schrodinger/pymol-open-source/blob/master/modules/pymol/cmd.py
7. **Selection algebra**: https://pymolwiki.org/Selection_Algebra
8. **Alignment**: https://wiki.pymol.org/index.php/Align
9. **Relative SASA**: https://pymolwiki.org/index.php/Get_sasa_relative
10. **Trajectories**: https://pymolwiki.org/index.php/Load_Traj
11. **Scenes**: https://pymolwiki.org/Scene
12. **Plugin architecture**: https://wiki.pymol.org/index.php/PluginArchitecture
13. **Molecular models (`get_model`)**: https://pymolwiki.org/Get_Model

Availability and precise signatures must be confirmed locally on PyMOL 3.1.0. Documentation may include Incentive-only, old-version, or third-party features. Do not assume documented functionality automatically works in Open-Source 3.1.0.

## 2. Capability catalog: 17 functional domains

The following are **underlying PyMOL operations**, not proposed LLM-callable functions with the same name. Build typed, secure high-level wrappers around them.

| Domain | Underlying operations / capabilities | Representative user intents | Priority |
|---|---|---|---|
| Input, retrieval, files | `fetch`, `load`, `save`, `load_traj`, `read_pdbstr`, `get_pdbstr`, `load_model`, `png` | Load PDB, mmCIF, trajectory, save PSE | P0 |
| Object/session management | `create`, `copy`, `extract`, `group`, `set_name`, `delete`, `enable`, `disable`, `get_names`, `count_states` | Manage objects and states | P0/P2 |
| Structure inspection | `get_model`, `get_chains`, `count_atoms`, `get_coords`, `get_extent`, `get_symmetry`, `get_object_matrix`, `get_type` | Identify chains, residues, heteroatoms | P0 |
| Selections | `select`, `deselect`, `identify`, `index`, `mask`, `protect` + selection algebra | Select site or chain | P0 |
| Representations/colors | `show`, `show_as`, `hide`, `color`, `spectrum`, `set_color`, `label`, `dss` | Cartoon/sticks/surface coloring | P0 |
| Camera/view | `orient`, `zoom`, `center`, `reset`, `turn`, `rotate`, `clip`, `get_view`, `set_view`, `viewport` | Reframe and navigate | P0 |
| Measurements | `distance`, `get_distance`, `angle`, `get_angle`, `dihedral`, `get_dihedral` | Contacts and geometry | P0 |
| Structure alignment | `align`, `super`, `cealign`, `fit`, `pair_fit`, `rms`, `rms_cur`, `get_raw_alignment` | WT–mutant structural comparison | P1 |
| Surface & accessibility | `get_area`, `get_sasa_relative`, `show surface`, `dot_solvent` setting | SASA and surface exposure | P1 |
| Editing and construction | `alter`, `alter_state`, `create`, `bond`, `unbond`, `replace`, `fab`, `fragment`, `pseudoatom`, `h_add`, `undo` | Modification and variant staging | P3 |
| Maps and density | `map_new`, `map_set`, `map_trim`, `isomesh`, `isosurface`, `isodot`, `ramp_new`, `volume` (check installed support) | Experimental density or electrostatic maps | P2 |
| States/trajectories | `load_traj`, `split_states`, `join_states`, `frame`, `count_states`, `smooth` | Trajectory visualization | P2 |
| Movies and scenes | `scene`, `mset`, `mview`, `mdo`, `mplay`, `mstop`, `mpng` | Molecular animations | P2 |
| Rendering/export | `ray`, `draw`, `png`, `save`, `scene`, `bg_color`, display settings | Publication-ready figures | P1 |
| Settings | `get`, `set`, `unset`, `set_bond`, `get_setting_*`, `set_color` | Style and user preferences | P1/P3 |
| Crystallography | `get_symmetry`, `symexp`, maps, symmetry-related selections | Crystal mates and lattice context | P2 |
| Automation/extension | `extend`, `alias`, `run`, `do`, `python`, `system`, logging | Developer capability; not an LLM tool | **BLOCK** |

### Selection engine: a separate sub-system

The selection language is not a simple string concatenation language. Support:
- Identities: object, chain, `segi`, `resi` (including insertion codes), `resn`, `name`, `elem`, atom `index`/`id`, `alt`, `ss`.
- Classes: `polymer.protein`, `polymer.nucleic`, `organic`, `inorganic`, `solvent`, `hetatm`, `backbone`, `sidechain`.
- Operators: `and`, `or`, `not`, `byres`, `bychain`, `within`, `around`, `expand`, `neighbor`, `bound_to`.
- Strong identity model: `(object, state, chain, segi, resi_string, atom_name, altloc)`; never use just a sequence index.
- Named selections should be collision-free and have a lifecycle. Treat model-generated selection expressions as untrusted; either build from typed components or validate against a strict grammar and ensure the result is nonempty.

### Settings: not all `set` options are tools

PyMOL has a wide range of settings controlling cartoons, surfaces, light, ray-tracing, labels, stereo, antialiasing, colors and other behavior. Discover available setting names/types from the **installed** build. Provide task-level presets (`publication_white`, `surface_epitope`, `transparent_background`, etc.), plus a small allowlist of individual settings. Avoid a completely unrestricted `cmd.set(setting, value)` adapter.

### Scientific methods — cautions

- `align` returns a 7-element result including post-refinement RMSD and aligned atom count. Default refinement can reject outliers; report pre/post differences and atom selection, and use `cycles=0` when a no-rejection comparison is requested.
- `super`/`cealign` serve different structural similarity regimes. `cealign` takes target before mobile, unlike `align`/`super`; never swap argument roles accidentally.
- `rms_cur` computes RMSD without superposition, so it is **not** interchangeable with an alignment RMSD.
- `get_area` requires appropriate `dot_solvent` and dot density settings for SASA. Guard against changing the user's global settings by using temporary objects or restoring settings.
- `get_sasa_relative` measures relative residue accessibility; it does not establish epitope immunogenicity.
- Geometric polar contacts are not validated H-bonds; the latter require an explicit geometrical/chemical method with protonation/angle handling.
- `load_traj` appends trajectory frames as states to an existing molecular object; coordinate consistency and memory need validation.
- Open-source availability may differ for some volume-rendering, export and modeling functions; mark these as **verify in runtime**.

## 3. Architecture: five layers

```text
USER CHAT (Vietnamese or English)
   |
   v
INTENT + ENTITY RESOLUTION
   |  parse PDB IDs, object names, chains, ligands, states, units
   v
CONTEXT OBSERVER + CAPABILITY RETRIEVER
   |  inspect live scene, find eligible tool definitions (NOT all at once)
   v
WORKFLOW PLANNER / STEP VALIDATOR
   |  dependency graph, risk, user permissions, estimated cost
   v
TYPED TOOL ADAPTERS ------------------------> PyMOL `cmd` API
   |                                          (serialized execution)
   v
RESULT VALIDATOR + EVIDENCE STORE
   |  numerical results / provenance / screenshots / output files
   v
FINAL SCIENTIFIC RESPONSE + OPTIONAL EXPORT
```

### Layer A: capability discovery (offline + on startup)

Use `pymol_api_inventory.py` to write JSON/CSV/Markdown on the user's Mac. Cross-reference this with existing `tool_registry.py`, test coverage and supported Open-Source version.

Recommended capability schema:

```json
{
  "id": "structure.fetch_rcsb",
  "intent_tags": ["download", "pdb", "fetch", "tải cấu trúc"],
  "underlying_api": "cmd.fetch",
  "availability": "runtime-verified",
  "inputs": {"pdb_id": "PDB_ID", "object_name": "Optional[SafeObjectName]"},
  "effects": ["network", "creates_object"],
  "preconditions": ["valid_pdb_id", "object_name_available"],
  "postconditions": ["object_exists", "atom_count>0"],
  "risk": "bounded_network",
  "rollback": "remove_new_object_only",
  "requires_confirmation": false,
  "validation_tests": ["fetch_1ubq", "invalid_id", "offline", "collision"]
}
```

No function becomes callable by the LLM merely because it was discovered. Model-facing tools are code-reviewed wrappers with explicit schema and authorization.

### Layer B: bounded high-level adapters

Expose **meaningful operations**, not entire raw cmd namespace. Examples:

- `structure.fetch_rcsb(pdb_id, object_name=None, file_format='cif')`
- `structure.load_local(file_path, object_name=None)`
- `structure.inspect(object_name, include_ligands=True)`
- `selection.by_residue(object_name, chain, residue_id)`
- `selection.neighborhood(reference_selection, cutoff_angstrom, scope='protein')`
- `view.apply_style(object_name, preset)`
- `view.color_by_secondary_structure(object_name)`
- `measure.contacts(selection_a, selection_b, cutoff_angstrom=4.0)`
- `alignment.compare(mobile, target, method='align', atoms='CA', cycles=5)`
- `surface.residue_sasa(object_name, chain=None, state=1)`
- `io.export_figure(output_path, width, height, ray=True)`
- `io.save_session(output_path)`

Use strict types, validators, explicit dependencies, meaningful error codes, side-effect metadata, and runtime feature flags. The adapter decides which `cmd` methods to call, not the LLM.

### Layer C: workflow templates (DAG / state machine)

Define workflow manifests for commonly requested tasks; let LLM select and parameterize them.

| Workflow ID | User intent | Deterministic steps | Evidence |
|---|---|---|---|
| WF01 | Download and show PDB | validate ID → fetch → verify object → style → orient | object, atom count |
| WF02 | Load local structures | validate path → parse → load → inspect | source file, models |
| WF03 | Summarize structure | enumerate objects/chains/ligands/waters/residues | structured inventory |
| WF04 | Highlight residue | parse chain/resi/icode → resolve → select → display | resolved residue |
| WF05 | Local residue environment | resolve residue → neighbors within X Å → group by residue → display | contact table |
| WF06 | Ligand-pocket map | select ligand → select protein neighbors → distances → figure | contacts / distances |
| WF07 | Potential polar contacts | inspect donor/acceptor chemistry → geometry → label as candidates | atom pairs / method |
| WF08 | Two-protein superposition | inspect → choose chain/atoms → align → measure → figure | RMSD / N atoms |
| WF09 | WT vs mutant | sequence mapping → align → neighborhood differences → figures | correspondence / caveats |
| WF10 | Protein epitope mapping | map sequence or residue IDs → verify → highlight → surface | mapped coordinates |
| WF11 | Surface accessibility | prepare isolate → solvent-aware area → per-residue SASA | Å² / parameters |
| WF12 | Exposed site comparison | normalize chain states → accessibility → compare | relative SASA table |
| WF13 | Domain visualization | ingest ranges → map chain/residue → color → label | annotated ranges |
| WF14 | Heteromer interface | chain selection → interface contact graph → area heuristic | residue pairs / settings |
| WF15 | Secondary structure figure | classify SS → cartoon color → label → export | SS labels / png |
| WF16 | Multiple structural variants | load batch → align to reference → tabulate | pairwise RMSD matrix |
| WF17 | Density visualization | load map → verify grid → contour → view | map/grid/level |
| WF18 | Crystal packing | read symmetry → expand mates → interface review | symmetry operators |
| WF19 | MD trajectory viewing | topology → load trajectory → state count → movie | frames / state map |
| WF20 | Multi-state conformations | inspect states → align → compare geometry | state RMSDs |
| WF21 | Scientific figure package | scene presets → render panels → labels → export | PNG/PSE/PML |
| WF22 | Molecular movie | store scenes → schedule frames → render sequence | frame range / files |
| WF23 | Mutation modeling (advanced) | duplicate object → mutation wizard or modeling backend → inspect | edited model with caveats |
| WF24 | Save reproducible analysis | snapshot → record operations + inputs → export PSE/PML/JSON | provenance manifest |

**For each workflow:** declare input schema, preconditions, steps, dependencies, output schema, rollback policy, verification gates, expected resources, and user-facing error messages. Do not add unreachable or untested placeholder workflows to the exposed registry.

### Layer D: execution policy and failure recovery

1. Observe active PyMOL objects and selected residues before planning.
2. Retrieve top relevant tools/workflows from a small indexed catalog. A model should not receive the entire API documentation in its prompt.
3. Validate inputs and preconditions **before** a mutating or expensive step.
4. Acquire a PyMOL execution lock; respect GUI-thread requirements; never block Qt with network inference.
5. Execute one step; collect structured results; verify explicit postconditions.
6. If failure is deterministic (`TOOL_NOT_FOUND`, `INVALID_ARGUMENT`, `NOT_SUPPORTED`), suppress exact repeated signatures and stop or choose a different verified strategy.
7. Retry transient failures (`TIMEOUT`, `NETWORK_ERROR`) no more than a small configured number of times and only for idempotent operations.
8. Save or restore camera/style/working state where feasible. Require confirmation before destructive atom edits and irreversible overwrites.
9. Produce a final narrative based only on actual tool results; report units, selections, atom counts, states and caveats.
10. Log context, tool version, input parameters, outputs and warnings for audit and reproducibility.

Proposed result contract:

```json
{
  "status": "success | failed | partial | blocked",
  "error_code": null,
  "tool_id": "alignment.compare",
  "inputs": {"mobile": "variant", "target": "wildtype", "atoms": "CA"},
  "result": {"rmsd_angstrom": 0.0, "aligned_atoms": 0, "method": "align"},
  "warnings": [],
  "created_objects": [],
  "files": [],
  "provenance": {"pymol_version": "3.1.0", "workflow": "WF08"}
}
```

Values above are schema **placeholders**, never example scientific measurements.

### Layer E: validation and provenance

**Structure integrity**: non-empty objects; valid chain/residue/atom IDs; no silent deletion; correct state/altloc mapping.

**Scientific validation**: compare PyMOL distances against independent NumPy; verify alignment correspondences and transform flags; compare SASA against a controlled reference within an explicitly justified tolerance; compare before/after coordinates when visual-only tasks should preserve them.

**Rendering**: confirm output files exist, dimensions match request, relevant objects are in frame, background/labels are correct.

**Reproducibility**: persist input PDB ID/version or file hash, selection expressions, parameter values, PyMOL version, model ID, tool versions, effects, and result JSON. Distinguish PSE snapshot vs executable PML replay; PML does not automatically guarantee reproducibility when source structures/network fetches change.

## 4. Prioritization and roadmap

| Release | Capabilities | Definition of done |
|---|---|---|
| R0: Capability discovery | Local `cmd`/PML inventory; supported feature flags; tool registry audit | Actual Mac PyMOL inventory, unsupported functions explicitly marked |
| R1: Basic access + recovery | fetch/load/save, introspection, validated selections, error recovery | `fetch 1ubq` in chat succeeds, bad tools do not loop |
| R2: Structural science | distances, contacts, ligand binding site, align/super/cealign, SASA | Numerical cross-checks and scientific metadata |
| R3: Professional visualization | presets, scenes, figure export, multi-panel setup | Reproducible PNG/PSE output with accurate labeling |
| R4: Complex inputs | density maps, symmetry, trajectories, multi-state | Large-file and multi-state QA |
| R5: Controlled editing + extensions | mutation modeling, optional external structural tools | Explicit approvals, tested undo/rollback, no false functional inference |

## 5. Risk tiers

- **Tier A (read-only):** introspection, query coordinates, counts, measured results; normally no confirmation.
- **Tier B (visual only):** color/show/orient/zoom/camera; normally automatic with a reversible snapshot.
- **Tier C (bounded I/O):** RCSB fetch, local file load, saving PNG/PSE; allowlist sources/paths; avoid collision and overwrite.
- **Tier D (structural mutation):** remove/alter/bond/fuse, atom coordinates, object deletion; explicit confirmation plus dedicated undo/versioned copy.
- **Tier X (never expose as direct model tools):** `cmd.do`, `cmd.run`, `cmd.system`, Python evaluation, arbitrary shell/plugin code, `quit`/`reinitialize`, unconstrained file operations.

`cmd.iterate` and `cmd.alter` can evaluate Python expressions; use `cmd.get_model`/coordinate arrays or **constant internal expressions** controlled by code, never user/LLM-generated expressions.

## 6. Acceptance benchmarks

1. `Fetch 1UBQ` → one successful fetch, no hallucinated `1ubq.pdb` filename.
2. `Show ubiquitin cartoons and helices red` → actual model display changes; no molecular coordinates change.
3. `Find residues within 5 Å of residue 42 on 1UBQ` → state/chain/resi disambiguation, nonempty contact table, independently verified distances.
4. `Fetch 1AKE and inspect ligand pocket` → ligand identity discovered from actual structure, no blind assumption.
5. `Align two proteins` → explicit mobile/target, atom mapping, pre/post RMSD, count of matched atoms, transformation status.
6. `Calculate SASA` → report `dot_solvent`, probe radius, sampling density and Å².
7. `Load mmCIF` → chain/segi ambiguity and insertion code handled.
8. `Load missing file` → clean error, no repeated invalid tool call.
9. `Delete loaded protein` → explicit confirmation; refuses without approval.
10. `Export publication image` → actual PNG and session output verified.
11. `Out-of-scope: Calculate experimental binding affinity` → clear boundary; do not invent PyMOL tool outputs.
12. `Interrupt slow operation` → controlled cancellation; UI remains responsive; no half-written output silently marked complete.

## 7. Gemini implementation brief

> Read the attached capability blueprint and the runtime inventory generated by `pymol_api_inventory.py`. Inspect the existing project; compare its 33 current tool implementations with the installed PyMOL command registry. Create a machine-readable, version-aware `capabilities.json` and `workflow_registry.json`. Distinguish discovered PyMOL functions from *approved* LLM-facing tools. Prioritize R0 and R1 first, then implement/test R2 incrementally. Build typed adapters (not direct `cmd.do`), input validation, error-code-based fail-fast recovery, and scientific result metadata. Keep Ollama local, preserve the current Qt chat interface, and do not reinstall PyMOL. For each new workflow provide real headless tests and interactive GUI acceptance tests. Use the local installed PyMOL 3.1.0 Python interpreter. Generate `CAPABILITY_MATRIX.md` describing supported/not-supported/untested functionality and test evidence. Never report all capabilities as working merely because they appear in PyMOL documentation or the runtime inventory.

### Reference output files

- `pymol_api_inventory.py` — non-destructive local runtime scanner.
- `pymol_api_inventory.json` — generated on Mac; machine-readable discovered API names/signatures/risk suggestions.
- `pymol_api_inventory.csv` — generated on Mac; sortable audit matrix.
- `pymol_api_inventory.md` — generated on Mac; human-readable catalog.
- `CAPABILITY_MATRIX.md` — to be generated by Gemini **after** checking plugin support and tests.

**End of blueprint.**
