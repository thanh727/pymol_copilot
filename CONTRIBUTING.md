# Contributing to PyMOL AI Copilot

Thank you for helping build reliable, reproducible AI-assisted structural biology tooling.

## Ways to help

- Report reproducible PyMOL integration bugs and scientific edge cases.
- Propose workflows, improve validation, documentation, accessibility or tests.
- Submit focused fixes for tool safety, structure analysis and macOS compatibility.

Before a substantial feature or architecture change, please open an
[issue](https://github.com/thanh727/pymol_copilot/issues) for discussion.

## Development and pull requests

1. Fork the repository, create a descriptive branch and keep changes focused.
2. Follow the existing Python structure and document user-visible behavior.
3. Include tests or a small reproducible example, especially for structural
   calculations, mutation numbering, distance cutoffs and safety checks.
4. Run the relevant tests and lint checks described in the README / CI workflow.
5. Open a pull request explaining the motivation, scope, testing and any
   scientific limitations or potential compatibility issues.

Do not include credentials, private structures, protected patient data,
unlicensed third-party code, or files whose redistribution you cannot authorize.

## Intellectual property and contribution licensing

The project's original code is distributed under the **MIT License** in
[LICENSE](LICENSE). By submitting a contribution for inclusion in the project,
you agree to make your contribution available under the same MIT License,
unless a different arrangement is expressly agreed in writing before
acceptance. **Copyright is not transferred to the maintainer.** Contributors
retain copyright in their own original work.

Contribute only material you authored or are entitled to license and distribute.
Clearly identify reused code, scientific datasets, image assets and any
third-party notices. Do not remove existing copyright or license notices.
If you are contributing as part of your employment or research appointment,
make sure you have the necessary institutional permission.

To help document provenance, use a Developer Certificate of Origin (DCO)
sign-off on new commits:

```bash
git commit -s -m "Describe your change"
```

The sign-off states that you have the right to submit your contribution under
the project's license. See the [DCO 1.1](https://developercertificate.org/).
This request applies to new contributions; it does not retroactively
establish provenance of existing code.

## Scientific integrity

Do not present inferred or geometric contacts as experimentally proven
interactions. Provide enough information to reproduce reported structural
results, state uncertainty and avoid destructive behavior by default.

## Vulnerability reports

Do not disclose exploitable security vulnerabilities in a public issue.
See [SECURITY.md](SECURITY.md) for responsible reporting.
