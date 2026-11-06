# Third-Party Notices and Attribution

## Scope

The root [MIT License](LICENSE) covers the original source code and project
documentation contributed to **PyMOL AI Copilot** by their respective
copyright holders under that license. It does **not** relicense third-party
software, scientific structures, model weights, logos or trademarks.

Runtime dependencies are installed separately; their licenses and any
redistribution obligations are controlled by their own publishers.

## Runtime integrations

| External project | Role | Licensing / attribution reference |
| --- | --- | --- |
| [Open-Source PyMOL](https://github.com/schrodinger/pymol-open-source) | Host molecular visualization application | [Schrödinger PyMOL license and trademark notice](https://github.com/schrodinger/pymol-open-source/blob/master/LICENSE); separate permissive terms |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | Graphical user interface bindings | Riverbank's **GPLv3 or commercial** licensing; [official details](https://en.riverbankcomputing.com/software/pyqt) |
| [NumPy](https://numpy.org/) | Numerical computing | Primarily BSD-3-Clause; see the [upstream license and bundled components](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| [Ollama](https://ollama.com/) | Separately installed local LLM runtime | Review upstream distribution terms; **model weights have model-specific licenses** |

**Important:** This plugin's MIT license does not eliminate obligations
that may arise from distributing a combined application or binaries with
GPL-licensed PyQt6. Verify PyQt6/Qt obligations for each distribution method,
especially packaged installers or commercial deployment. Users must comply
with the upstream licenses of installed dependencies and model weights.

## Test structures

The repository contains example molecular structure coordinate files:

- `pymol_ai_copilot/tests/data/1ubq.pdb` — PDB accession [1UBQ](https://www.rcsb.org/structure/1UBQ)
- `pymol_ai_copilot/tests/data/1ake.pdb` — PDB accession [1AKE](https://www.rcsb.org/structure/1AKE)
- `pymol_ai_copilot/tests/data/4ake.pdb` — PDB accession [4AKE](https://www.rcsb.org/structure/4AKE)
- `pymol_ai_copilot/tests/data/1ubq_r42a.pdb` — locally modified test model named for 1UBQ (R42A); its detailed generation provenance should be retained in project records

The wwPDB archive's deposited structure data are available under the
**CC0 1.0 Universal** dedication. Please cite the primary structure
publications and PDB accessions in scholarly use when practical.
See the [RCSB PDB usage policy](https://www.rcsb.org/pages/usage-policy).
The project's MIT license does not claim ownership of these data.

## Trademarks and independence

**PyMOL** is a trademark of Schrödinger, LLC. This independent community
plugin is not endorsed by or affiliated with Schrödinger or the PyMOL
maintainers. Product names remain the property of their respective owners.

## Third-party submissions

Contributors must preserve upstream notices and disclose origins and
licenses of any imported material. See [CONTRIBUTING.md](CONTRIBUTING.md).
