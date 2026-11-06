# Security Policy

PyMOL AI Copilot controls scientific software using a local language-model
agent. Reports about unsafe tool execution, file access, malicious input,
dependency vulnerabilities or unintended disclosure are taken seriously.

## Supported versions

Security fixes are targeted at the latest code on the `main` branch.
Older snapshots and development forks are not guaranteed to receive patches.

## Reporting a vulnerability

**Please do not post vulnerability details, payloads or secrets in public
GitHub issues or pull requests.**

If GitHub's private vulnerability reporting feature is enabled, use the
repository's **Security** tab and its private reporting workflow.

If private reporting is unavailable, contact the maintainer through the
contact methods listed on the
[GitHub profile](https://github.com/thanh727) to establish a private
communication channel first. Do not send exploitation details until a
private channel is agreed.

Include affected versions, steps to reproduce, potential impact and any
suggested mitigation when reporting privately. Please allow time for triage
and coordinated remediation before public disclosure.

## Maintainer setup recommendation

The repository maintainer should enable **Private vulnerability reporting**
and **Dependabot alerts** under GitHub Settings -> Security & analysis,
where available. A SECURITY.md file does not enable those settings itself.
