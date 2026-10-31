# AGENTS.md

- For native GitHub sub-issues, ensure `.github/workflows/issue-parent-sync.yml` exists with `issues: [opened, edited]`, `permissions: issues: write`, and a job calling `vernikr/mother/.github/workflows/issue-parent-sync.yml@v1` (create the caller workflow if missing); then put `<!-- issue-parent: #N -->` on its own line in the child Issue body, or use `<!-- issue-parent: none -->` to detach.
