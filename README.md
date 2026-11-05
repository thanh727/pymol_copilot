# PyMOL AI Copilot

**PyMOL AI Copilot** is a native, local-first Agentic AI plugin designed for PyMOL Open-Source on macOS (Apple Silicon & Intel). It allows structural biologists and computational chemists to inspect, manipulate, analyze, and visualize molecular structures in PyMOL using natural language.

---

## 🔬 System Overview & Architecture

PyMOL AI Copilot implements an autonomous execution loop:
$$\text{Observe} \longrightarrow \text{Plan} \longrightarrow \text{Select Tool} \longrightarrow \text{Execute} \longrightarrow \text{Inspect Result} \longrightarrow \text{Continue or Finish}$$

```
pymol_ai_copilot/
├── __init__.py                # Plugin package initialization & exports
├── plugin.py                  # Official PyMOL __init_plugin__() entry point & CLI extension
├── config.py                  # User settings, persistent configuration, and paths
├── ui/
│   ├── __init__.py
│   └── chat_panel.py          # Native PyQt6 non-modal, persistent chat dialog with QThread
├── agent/
│   ├── __init__.py
│   ├── controller.py          # Multi-step autonomous agent execution loop
│   ├── ollama_client.py       # Local Ollama REST client with dual tool-call parsing
│   ├── prompts.py             # Domain-specific structural biology system prompts
│   ├── tools.py               # Concrete implementations of 33+ PyMOL tools
│   └── tool_registry.py       # Strict whitelist registry and Ollama function schemas
├── pymol_bridge/
│   ├── __init__.py
│   ├── executor.py            # Thread-safe PyMOL command dispatcher & script recorder
│   ├── structure_inspector.py # Atom counts, chains, ligands, and bounding box inspection
│   └── visualization.py       # Publication presets, ray-tracing, and color palettes
├── analysis/
│   ├── __init__.py
│   ├── alignment.py           # Sequence-informed and structure-based alignments (RMSD)
│   ├── contacts.py            # Interatomic distances, contact residues, polar candidates
│   └── mutation.py            # Point mutation parsing, residue validation, and neighborhood
├── tests/                     # 32+ automated unit, mock, and live PyMOL integration tests
├── install.py                 # Automated one-click installer / uninstaller
├── requirements.txt           # Minimal environment dependencies
└── README.md                  # Comprehensive documentation and prompt guides
```

---

## 🛠️ Detected Environment & Prerequisites

The plugin is tailored for macOS with Apple Silicon (`arm64`) or Intel (`x86_64`) running PyMOL Open-Source:

- **macOS:** Apple Silicon (`arm64`) or Intel (`x86_64`).
- **Python:** Python 3.10+ (PyMOL's bundled environment at `/opt/homebrew/Cellar/pymol/.../libexec/bin/python` or active virtualenv).
- **Qt Bindings:** PyQt6 (via `pymol.Qt`).
- **Local LLM Engine:** [Ollama](https://ollama.com/) running at `http://127.0.0.1:11434`.
- **Supported Models:** Any tool-calling model, including:
  - `qwen2.5-coder:7b` (fast, deterministic tool calling)
  - `qwen2.5-coder:14b`
  - `gemma4:latest` (supports native tool calls and reasoning)
  - `llama3.1`, `mistral`, etc.

---

## 🚀 Installation

### Automated One-Click Installation

Run the installation script using PyMOL's Python interpreter:

```bash
/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/bin/python install.py
```

This will:
1. Link `pymol_ai_copilot` into `~/.pymol/startup/pymol_ai_copilot`.
2. Register the user startup directory in PyMOL's plugin configuration (`~/.pymolpluginsrc.py`).
3. Verify that PyMOL discovers the plugin automatically upon launch.

### Uninstalling

To remove the plugin:

```bash
/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/bin/python install.py --uninstall
```

---

## 🖥️ Launching the Plugin in PyMOL

1. Open PyMOL:
   ```bash
   pymol
   ```
2. Open the AI Copilot:
   - **Menu:** Click **Plugin** $\rightarrow$ **AI Copilot**
   - **Command Line:** Type `ai_copilot` in the PyMOL prompt.

The persistent, non-modal chat panel will appear without freezing or restarting your PyMOL session.

---

## 💡 Key Features & Capabilities

### 1. Structure Inspection & Live Session Awareness
The agent automatically inspects the active PyMOL session:
- Detects loaded molecular objects, total atoms, chains, and bounding boxes.
- Identifies organic ligands, solvent (water), and inorganic ions.
- Tracks active selections.

### 2. Autonomous Multi-Step Tool Execution
The agent can execute multiple tools sequentially to fulfill complex requests.
- **Example:** Observe context $\rightarrow$ Select binding pocket $\rightarrow$ Show sticks $\rightarrow$ Zoom camera $\rightarrow$ Find polar contact candidates $\rightarrow$ Explain results.
- Configurable maximum step threshold (default: 8 steps).
- Stop button enables immediate safe cancellation.

### 3. Scientific Analysis
- **Mutation Inspection:** Parses standard notation (e.g., `R132H`, `Arg132His`, `A:R132H`). Verifies whether the residue at that sequence position matches the expected wildtype amino acid. Highlights the local sphere (e.g. 5.0 Å) and computes polar contact candidates.
- **Contact & Distance Analysis:** Measures inter-atomic distances, classifies pocket residues (hydrophobic, positive, negative, aromatic), and identifies geometric polar contact candidates ($\le 3.5\text{ \AA}$).
  > [!NOTE]
  > Distance-based polar contacts are strictly reported as geometric candidates, not experimentally verified hydrogen bonds.
- **Structure Comparison:** Aligns structures using sequence-guided refinement (`align`), structural superposition (`super`), or combinatorial extension (`cealign`). Calculates all-atom, backbone, or $C\alpha$ RMSD.

### 4. Publication-Ready Visual Presets
One-click and natural language presets:
- **Cartoon Chains:** Clean cartoon representation with distinct chain colors on a pure white background.
- **Ligand Binding Pocket:** Transparent protein cartoon + sticks for pocket residues within 5.0 Å + highlighted ligand + polar contact dashes.
- **Mutation Neighborhood:** Stick and sphere highlighting of mutation site + cyan sticks for surrounding residues within 5.0 Å.
- **Epitope Localization:** Highlights epitope residues against antigen surface.

### 5. Script & Data Export
- **Export PyMOL Script (`.pml`):** Exports a reproducible macro recording every command executed by the agent.
- **Save Session (`.pse`):** Saves the current session state.
- **Render Image (`.png`):** Exports high-resolution (default $1920\times1080$, 300 DPI) ray-traced figures.
- **Export Chat Log:** Saves full conversation transcripts in JSON or text.

---

## 🔒 Security & Reliability Guarantees

- **No Code Execution:** Never executes arbitrary LLM-generated code via `eval()`, `exec()`, or `cmd.do()`.
- **Strict Tool Whitelist:** All actions must map to verified, type-checked Python functions in the `ToolRegistry`.
- **Thread Safety:** LLM network calls and planning run inside a dedicated Qt background thread (`AgentWorker`). PyMOL's OpenGL viewport remains fluid and responsive.
- **Non-Destructive Defaults:** Never silently overwrites user files without a clear file path or confirmation.

---

## 💬 Example Natural-Language Prompts

### Visualization
- *"Show the loaded protein as a cartoon, color each chain differently, and set the background to white."*
- *"Hide all water molecules and show the protein surface with 50% transparency."*
- *"Zoom in on chain A and orient the view along its principal axes."*

### Binding Pocket & Ligand Interactions
- *"Find all residues within 5 angstroms of the ligand and show them as sticks."*
- *"Identify potential polar contacts between the ligand and surrounding protein residues."*
- *"Inspect the binding pocket and classify hydrophobic and aromatic residues."*

### Mutation Analysis
- *"Analyze mutation R132H in chain A and show residues within 5 angstroms."*
- *"Check if residue 28 in chain B is a Lysine, and highlight its local structural environment."*
- *"Compare the mutant object with wildtype, align them, and report the $C\alpha$ displacement at residue 132."*

### Structure Comparison & Alignment
- *"Align protein2 onto protein1 using structural superposition and report the calculated RMSD."*
- *"Calculate the $C\alpha$ RMSD between the two proteins."*
- *"Identify residues with significant structural deviation between the two aligned structures."*

### Publication Figure Preparation
- *"Prepare a publication-quality figure of the ligand binding pocket and export it as pocket.png with ray tracing enabled."*
- *"Export all actions performed in this session as a PyMOL script (.pml)."*

---

## 🧪 Testing & Verification

The test suite contains 32 automated unit, mock, and PyMOL integration tests:

```bash
# Run all tests using PyMOL's Python interpreter
/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/bin/python -m unittest discover -s pymol_ai_copilot/tests -v
```

### Verified Test Categories:
- `test_config.py`: Configuration persistence and path resolving.
- `test_tool_registry.py`: Whitelist validation, schema extraction, error trapping.
- `test_ollama_client.py`: Ollama REST API parsing (native `tool_calls`, JSON Lines, code blocks).
- `test_analysis.py`: Mutation string parser, residue translation, contact categories.
- `test_pymol_integration.py`: Live PyMOL headless (`-qc`) execution of representations, measurements, selections, RMSD, PNG, and PML exports.
- `test_agent_controller.py`: Autonomous Observe $\rightarrow$ Plan $\rightarrow$ Execute $\rightarrow$ Inspect $\rightarrow$ Finish cycle.

---

## ❓ Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Ollama Offline" badge in UI** | Ollama daemon is not running | Run `ollama serve` or open Ollama app on your Mac. |
| **No models in dropdown** | No models installed in Ollama | Pull a model: `ollama pull qwen2.5-coder:7b`. Then click the **⟳** refresh button. |
| **Menu item missing in PyMOL** | Startup path was not loaded | Type `ai_copilot` in the PyMOL prompt, or re-run `/path/to/python install.py`. |
| **Alignment fails with "No alignment found"** | Structures have < 4 residues or no sequence correspondence | Use `method="super"` for structural superposition without sequence identity. |
| **PyMOL GUI freezes during chat** | Non-threaded execution | PyMOL AI Copilot uses `AgentWorker(QThread)` to prevent freezing. Ensure you launch via the official plugin interface. |

---

## 📄 License
Open-Source. Distributed under the MIT License.
