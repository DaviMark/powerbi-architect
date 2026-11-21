# Changelog

## [1.1.0] — 2026-11-21
### Added
- `scripts/pbi_graph.py`: offline Power BI knowledge graph (TMDL, PBIR, SQL, docs, Python) with
  `GRAPH_REPORT.md`, per-model cards, `graph.json`, `graph.html` and `query` / `explain` / `impact` /
  `path` commands. Findings: unused columns/measures, broken visual fields, shared sources, divergent measures.
- `pbi_graph.py install|uninstall`: agent instructions in `AGENTS.md`/`CLAUDE.md`, Claude Code hooks
  (SessionStart + after edits) and git hooks that keep the graph fresh.
- `references/graph.md`; `SKILL.md` §0 now says "graph before files".
- Installers build the graph after copying (`--no-graph`/`-NoGraph`, `--no-hooks`/`-NoHooks`).
### Changed
- Framework renamed: PBIP Blueprint → Power BI Workspaces (`config/workspaces.toml`, `tools/pbw.py`).
### Fixed
- `install.ps1` failed to parse in Windows PowerShell 5.1 (UTF-8 without BOM); now saved with BOM.

## [1.0.0] — 2026-11-23
### Added
- `SKILL.md` with eight laws, workflow and decision trees.
- References: workflow, modeling, power-query, dax, tmdl, pbir, report-design, visual-selection,
  custom-visuals, documentation, refactoring, performance, security, quality-checklist.
- Verified reference custom visual `templates/pbiviz-bullet-kpi` (API 5.11, pbiviz 7.2).
- `scripts/audit_pbip.py` offline PBIP audit.
- Installers for project/global (bash + PowerShell), evals, CI.
