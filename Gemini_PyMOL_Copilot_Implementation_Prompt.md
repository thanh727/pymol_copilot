# Gemini coding-agent prompt: Full PyMOL capability pipeline

You are the lead Python engineer and computational structural biologist responsible for upgrading the existing native PyMOL AI Copilot on macOS.

**Local project:** `/Users/thanhnt/Desktop/GitHub/pymol_copilot`  
**Installed environment:** PyMOL Open-Source 3.1.0 installed via Homebrew, Apple Silicon macOS, existing PyMOL Python environment, local Ollama ready. Verify rather than blindly trust these earlier diagnostic values.

**Reference attachments:** `PyMOL_Copilot_Capability_Pipeline.md` and `pymol_api_inventory.py`.

## Primary objective

Build a comprehensive, extensible pipeline that can eventually support all **appropriate and validated** PyMOL Open-Source features through an agentic AI assistant, without directly exposing arbitrary `pymol.cmd` calls or scripts to the LLM.

Do not reinstall PyMOL or replace the current plugin. Preserve the existing chat UI, the current working tools and Ollama integration.

## Mandatory sequence

1. Inspect the current repository. Run the existing tests and document the current 33-tool capabilities, including actual code/implementation state, not only tool schemas.
2. Run `pymol_api_inventory.py` with PyMOL's own Python interpreter. Save generated `pymol_api_inventory.json`, `.csv`, `.md` in the project documentation folder. Record versions, count and limitations.
3. Compare PyMOL command registry (`cmd.keyword`), Python public callables (`pymol.cmd`), installed package availability, and the already exposed tool registry. Build `CAPABILITY_MATRIX.md` with status: `implemented/tested`, `implemented/untested`, `not implemented`, `not available in open-source build`, `dangerous/not exposed`, `unknown`.
4. Implement a version-aware `CapabilityRegistry` storing description, native API mapping, arguments, preconditions, postconditions, side-effects, risk level, confirmation requirements, compatibility and tests. Discovery MUST NOT imply authorization.
5. Implement typed wrappers with strict schema validation. Support natural-language intent routing to approved tool subsets. Do not dump all commands into a single huge LLM prompt.
6. Implement a `WorkflowRegistry` with prerequisite checks, context-observation steps, tool execution DAG, rollback, validation and evidence. Use workflows from the supplied blueprint.
7. First repair `fetch_structure` and `load_structure`, missing-tool fail-fast error handling, and retry detection; regression test the exact scenario where the AI loops 8 times calling unregistered `load` or `fetch`.
8. Expand in priority: structure inspection and selection -> visualizations -> distance geometry -> alignment/RMSD -> surface accessibility -> ligand pockets -> scenes/figures -> maps -> trajectories -> controlled modeling.
9. Add one fully tested workflow per increment; keep the plugin usable at every milestone. Perform numerical cross-checks and use real protein structures. Maintain a strict boundary between visual observations, inferred hypotheses and computed scientific outputs.
10. Deliver a QA report with commands/tools tested, model tool-call compliance, live GUI status, scientific validation, regression tests, and known limits.

## Required agent behavior

- A natural-language instruction is resolved against actual loaded objects, atom/residue identities, chain/state identifiers and applicable tools.
- For PDB IDs, use a dedicated RCSB-fetch adapter (`cmd.fetch`) with input validation and verification that an object was really loaded.
- For local files, use a constrained `cmd.load` adapter with path checks and validated supported formats.
- If a requested capability is unavailable, stop early with a clear missing-capability error. No identical invalid call may be repeated.
- Only retry idempotent transient failures; never repeat unregistered tools, invalid arguments or destructive actions.
- Preserve original structure data and view state whenever possible, and obtain confirmation for irreversible changes.
- Never use arbitrary Python `eval`/`exec`, `cmd.do`, `cmd.run`, `cmd.system`, unconstrained `cmd.iterate`/`cmd.alter` expressions, or shell commands as general LLM tools.
- All numeric outputs must have units, atom selection, chain identifiers, residue mapping, object/state, algorithm/method and parameter provenance where applicable.
- If a query requires software outside PyMOL (e.g. molecular docking or free-energy calculations), label it as a separate verified extension and do not claim PyMOL itself can do it.

## Core test prompts

- "Tải về cấu trúc 1ubq và hiển thị dạng cartoon."
- "Identify all chains and any ligands in the current object."
- "Show residues within 5 Å of residue 42 in chain A; provide a table of minimum atom-atom distances."
- "Compare the two loaded protein structures using C-alpha alignment; report atom count and post-refinement RMSD."
- "Calculate per-residue relative solvent accessibility for chain A."
- "Prepare an image with a white background and export a new non-overwriting PNG."
- "Load a nonexistent local structure." (must fail cleanly)
- "Use tool `nonexistent_tool` eight times." (must fail fast, never loop)
- "Delete all molecules." (must request confirmation)

## Deliverables

- Completed and tested source modifications in the existing repository.
- Generated runtime inventory and `CAPABILITY_MATRIX.md`.
- Typed `CapabilityRegistry` and `WorkflowRegistry` with documentation and structured tool definitions.
- Enhanced multi-step controller with deterministic failures, bounded retries and cancellation.
- Expanded scientific adapters and tests.
- `QA_REPORT.md` with actual GUI vs headless tests distinguished.
- Git commits capturing changes and a migration/rollback plan.

Work incrementally. Do not promise future work or stop at conceptual recommendations: implement and test the highest-priority capabilities in this session, and transparently report any remainder.
