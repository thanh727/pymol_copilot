# PyMOL AI Copilot — Capability Matrix & API Atlas

**Environment:** PyMOL 3.1.0 Open-Source (Homebrew `arm64`), Python 3.14.3, macOS 27.2  
**Inventory Scope:** 488 discovered public callables and PML keywords (440 Python API callables, 312 PML keywords)  
**Registered AI Tools:** 47 verified, typed, and tested tools  
**Policy:** **Discovery does NOT imply authorization.** All unreviewed PyMOL API functions default to **LLM-disallowed**.

---

## 1. Executive Summary & Security Policy

PyMOL AI Copilot strictly enforces an allowlist architecture. The agent never executes arbitrary PyMOL scripts or Python expressions via `cmd.do()`, `exec()`, or `eval()`. Instead, each action must map to a typed, parameter-validated Python adapter registered in `GLOBAL_REGISTRY`.

### Status Definitions
- **`implemented/tested`**: Tool has a typed adapter in `agent/tools.py`, is registered in `GLOBAL_REGISTRY`, and is validated with automated regression and live Ollama tests.
- **`implemented/untested`**: Code exists but lacks targeted test suite coverage.
- **`candidate (safe)`**: Read-only or bounded view function suitable for future pipeline increments (e.g. SASA, electron density).
- **`dangerous/blocked (Tier X)`**: Arbitrary code execution (`cmd.do`, `python`, `system`), unconstrained file system modifications, or session wipes (`quit`, `reinitialize`). NEVER exposed to LLM.
- **`mutation (Tier D)`**: Structural coordinates or covalent changes requiring explicit user confirmation and undo snapshots.
- **`not available in open-source`**: Commercial or incentive-only features.

---

## 2. 17 Capability Domains Matrix

### 01 Input, retrieval, files
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `fetch_structure` | `cmd.fetch` | **implemented/tested** | Downloads PDB/AlphaFold structures with accession validation and non-destructive collision disambiguation. |
| `load_structure` | `cmd.load` | **implemented/tested** | Loads local PDB, mmCIF, mol2, sdf files with path sandboxing against traversal. |
| `save_session` | `cmd.save` | **implemented/tested** | Saves full session state as reproducible `.pse` file. |
| `export_png` | `cmd.png` / `cmd.ray` | **implemented/tested** | Renders and exports high-resolution ray-traced PNG figures. |
| `export_pml` | Script recorder | **implemented/tested** | Exports reproducible PML script reproducing all performed actions. |
| `export_analysis_json` | JSON adapter | **implemented/tested** | Exports structured scientific data (RMSD, contacts, mutations). |
| `export_analysis_csv` | CSV adapter | **implemented/tested** | Exports tabular scientific measurements. |
| `export_ligand_contacts` | Ligand export adapter | **implemented/tested** | Exports ligand contact profiles and polar interactions to CSV/JSON. |
| `export_sasa_analysis` | SASA export adapter | **implemented/tested** | Exports per-residue SASA (Å²) and RSA (%) tables to CSV/JSON. |
| *None (unexposed)* | `cmd.load_traj` | **candidate (safe)** | Load MD trajectory frames into an existing object. |
| *None (unexposed)* | `cmd.read_pdbstr` / `read_molstr` | **candidate (safe)** | Load structure from in-memory string. |

### 02 Object and session management
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `list_objects` | `cmd.get_names` | **implemented/tested** | Lists all loaded molecular objects and active selections. |
| *None (unexposed)* | `cmd.create` / `cmd.copy` | **candidate (safe)** | Duplicate or extract specific subsets into isolated objects for safe inspection. |
| *None (unexposed)* | `cmd.delete` / `cmd.remove` | **mutation (Tier D)** | Destructive object/atom removal; requires explicit confirmation. |
| *None (unexposed)* | `cmd.reinitialize` | **dangerous/blocked (Tier X)** | Session wipe; blocked from model exposure. |

### 03 Structure inspection
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `get_chains` | `cmd.get_chains` | **implemented/tested** | Retrieves chain identifiers across all loaded objects. |
| `count_atoms` | `cmd.count_atoms` | **implemented/tested** | Counts total atoms matching arbitrary selection. |
| `get_residues` | `cmd.iterate` | **implemented/tested** | Extracts sequence of residues (resn, resi, chain) for objects/chains. |
| `get_selection_info` | `cmd.iterate` | **implemented/tested** | Detailed breakdown of atom counts, residues, and chains. |
| `get_object_info` | `cmd.count_atoms` / `cmd.get_extent` | **implemented/tested** | Structural statistics: protein/nucleic/ligand atoms, bounding box, dimensions. |
| `get_structure_summary` | Composite | **implemented/tested** | Compact high-level structural context suitable for LLM prompt context. |
| *None (unexposed)* | `cmd.get_symmetry` | **candidate (safe)** | Read crystallographic space group, unit cell parameters. |
| *None (unexposed)* | `cmd.get_coords` | **candidate (safe)** | Extract raw atomic coordinates. |

### 04 Selection and atom queries
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `select_residues` | `cmd.select` | **implemented/tested** | Creates named PyMOL selection (e.g. active site, binding pocket). |
| *None (unexposed)* | `cmd.indicate` / `cmd.mask` | **candidate (safe)** | Visual indication markers. |

### 05 Representation and color
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `show_representation` | `cmd.show` / `cmd.show_as` | **implemented/tested** | Displays cartoon, sticks, spheres, surface, lines, ribbons. |
| `hide_representation` | `cmd.hide` | **implemented/tested** | Hides specific representations or everything. |
| `color_selection` | `cmd.color` / `cmd.spectrum` / `util` | **implemented/tested** | Applies colors by name, rainbow spectrum, chain, or secondary structure. |
| `highlight_residues` | `cmd.show` + `cmd.color` | **implemented/tested** | Highlights specific residues as sticks/spheres with distinct color. |
| `set_transparency` | `cmd.set` | **implemented/tested** | Sets surface or cartoon transparency (0.0 to 1.0). |
| `label_residues` | `cmd.label` | **implemented/tested** | Draws 3D text labels in PyMOL viewport. |
| `apply_visualization_preset` | Composite | **implemented/tested** | Applies presets: cartoon_by_chain, binding_pocket, mutation_neighborhood, epitope. |
| `visualize_ligand_pocket` | Composite | **implemented/tested** | Publication styling for ligand pocket: cartoon receptor, sticks for ligand & pocket, polar contact dashes. |
| `visualize_epitope` | Composite | **implemented/tested** | Visualizes mapped linear/conformational epitope using contrasting surface highlight or sticks. |

### 06 Camera and viewport
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `orient_selection` | `cmd.orient` | **implemented/tested** | Aligns camera with principal inertial axes of selection. |
| `zoom_selection` | `cmd.zoom` | **implemented/tested** | Centers and zooms viewport onto selection. |
| `reset_view` | `cmd.reset` | **implemented/tested** | Resets viewport camera to default. |
| `set_background` | `cmd.bg_color` | **implemented/tested** | Sets viewport background color (e.g. white, black). |

### 07 Distances and geometry
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `calculate_distances` | `cmd.distance` + NumPy | **implemented/tested** | Measures pairwise interatomic distances; verified against independent NumPy math. |
| `find_nearby_residues` | `cmd.iterate` + selection | **implemented/tested** | Finds all polymer residues within cutoff of target selection. |
| `find_polar_contact_candidates` | `cmd.distance` + geometry | **implemented/tested** | Identifies geometric polar donor/acceptor pairs <= 3.5 Å. |
| `inspect_binding_pocket` | Composite | **implemented/tested** | Comprehensive pocket analysis: contacts, hydrophobic, polar, aromatic residues. |
| `identify_ligands` | `cmd.iterate` + heuristics | **implemented/tested** | Identifies bound biologically relevant ligands, excluding solvent and crystallization additives. |
| `analyze_ligand_interactions` | NumPy pairwise distances | **implemented/tested** | Calculates minimum heavy-atom distances and identifies geometric polar contact candidates (< 3.5 Å). |

### 08 Structure alignment
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `align_structures` | `cmd.align` / `super` / `cealign` | **implemented/tested** | Superimposes mobile onto target reference structure with outlier rejection cycles. |
| `calculate_rmsd` | `cmd.rms_cur` / `cmd.align` | **implemented/tested** | Calculates CA, backbone, or all-atom RMSD without or with superposition. |
| `compare_residues` | NumPy distance per-residue | **implemented/tested** | Identifies specific residue positions with CA displacement > threshold. |
| `identify_mutations` | Sequence alignment + coords | **implemented/tested** | Compares wildtype and mutant structures, reporting local CA displacements. |
| `map_epitope_sequence` | Sequence search + NumPy | **implemented/tested** | Maps linear peptide sequences or residue lists to 3D coords, computing spatial centroid & clustering. |
| `compare_wt_mutant` | Composite superposition | **implemented/tested** | Sequence-aware alignment of WT and mutant structures, CA/backbone displacement & contact deltas. |
| `batch_compare_structures` | Batch engine | **implemented/tested** | Aligns multiple structures against a reference, computing consistent pairwise metrics table (max 20). |

### 09 Surface and accessibility
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `calculate_sasa` | `cmd.get_area` (dot_solvent=1) | **implemented/tested** | Calculates total & per-residue absolute SASA (Å²) and relative accessibility RSA (%) via Tien et al. (2013). |
| `map_sasa_to_structure` | `cmd.get_area(load_b=1)` + `cmd.spectrum` | **implemented/tested** | Loads atomic SASA into B-factor column and renders continuous color spectrum on surface/cartoon. |
| `compare_sasa` | Composite SASA | **implemented/tested** | Computes per-residue Delta SASA = SASA(obj1) - SASA(obj2) between conformational states. |

### 10 Editing and mutations
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `analyze_mutation` | Inspector + contacts | **implemented/tested** | Verifies wildtype residue, inspects local neighborhood, calculates polar candidates. |
| *None (unexposed)* | `cmd.alter` / `cmd.alter_state` | **mutation (Tier D)** | Modifies residue names or coordinates; requires confirmation. |

### 11 Maps and volumetric
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| *None (unexposed)* | `cmd.isomesh` / `cmd.isosurface` | **candidate (safe)** | Renders electron density or electrostatic contour meshes. |

### 12 States and trajectories
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| *None (unexposed)* | `cmd.count_states` / `cmd.set_state` | **candidate (safe)** | Inspect and switch conformational ensemble states. |

### 13 Movies and scenes
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| *None (unexposed)* | `cmd.scene` | **candidate (safe)** | Store and recall PyMOL camera and visual scenes. |

### 14 Rendering and figures
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `export_png` | `cmd.png` + `cmd.ray` | **implemented/tested** | High-resolution ray-traced image rendering. |

### 15 Settings and configuration
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| `set_transparency` | `cmd.set transparency` | **implemented/tested** | Safely sets bounded transparency values. |
| `set_background` | `cmd.bg_color` | **implemented/tested** | Guarded background color settings. |
| *None (unexposed)* | `cmd.set` (unrestricted) | **dangerous/blocked (Tier X)** | Arbitrary global settings changes blocked; guarded task-specific presets used instead. |

### 16 Crystallography and symmetry
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| *None (unexposed)* | `cmd.symexp` | **candidate (safe)** | Generates symmetry-related crystal mates in unit cell. |

### 17 Command language and extension (BLOCKED TIER X)
| Copilot Tool | PyMOL API / PML | Status | Capabilities & Security Policy |
|---|---|:---:|---|
| *None (unexposed)* | `cmd.do` | **dangerous/blocked (Tier X)** | Arbitrary PML command execution. NEVER EXPOSED. |
| *None (unexposed)* | `cmd.system` / `cmd.python` | **dangerous/blocked (Tier X)** | Arbitrary shell / python exec. NEVER EXPOSED. |
| *None (unexposed)* | `cmd.extend` | **dangerous/blocked (Tier X)** | Plugin command overriding. NEVER EXPOSED. |
| *None (unexposed)* | `eval` / `exec` | **dangerous/blocked (Tier X)** | Arbitrary string evaluation. NEVER EXPOSED. |

---

## 3. Registered Tool Coverage Summary

- **Total Registered Tools in GLOBAL_REGISTRY:** 47 tools (35 foundational + 12 Phase 4 advanced structural biology tools)
- **Workflows Supported:** 10 deterministic reference workflows (WF01–WF10)
- **Test Suite Coverage:** 100+ automated unit, integration, scientific validation, and live acceptance tests (100% pass rate)
- **All 47 tools are strictly typed, parameter-validated, and mapped to specific PyMOL APIs.**

