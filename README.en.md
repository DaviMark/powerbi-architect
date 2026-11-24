<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="Power BI Architect" src="docs/assets/hero-light.svg" width="100%">
</picture>

**The Agent Skill that makes any AI think like a senior Power BI developer.** · [Português](README.md)

</div>

Your AI can *write* DAX. This skill teaches it to **think like a principal Power BI engineer and a
product designer**: import the minimum, model a star schema, keep Power Query at **one step**, document
every metric, design pages that answer one question in three seconds — and build a custom visual
(`.pbiviz`) **only when no native visual fits**.

Works with **GitHub Copilot, Claude Code, Cursor, OpenAI Codex, Gemini CLI** and any agent that
supports the open **[Agent Skills](https://agentskills.io)** format. Standalone or inside
**[Power BI Workspaces](https://github.com/DaviMark/powerbi-workspaces)**.

## Install

**Claude Code**, one command: `/plugin install powerbi-architect --marketplace DaviMark/powerbi-architect`

**No terminal** (Claude.ai and other tools that accept skill uploads): download
`powerbi-architect-vX.Y.Z.zip` from the [latest release](https://github.com/DaviMark/powerbi-architect/releases/latest).

**Every AI in your repository:**

```bash
git clone https://github.com/DaviMark/powerbi-architect.git
./powerbi-architect/install/install.sh /path/to/your/repo      # or --global, --link
# Windows: .\powerbi-architect\install\install.ps1 -Target C:\path\to\repo
```
The installer copies the skill into `.claude/skills/`, `.github/skills/` and `.agents/skills/`, then builds
the **Power BI knowledge graph** of your repo (see below). `--no-graph` / `-NoGraph` only copies files.
To update: `git pull` in the clone, then `--update` / `-Update` (`--status` / `-Status` shows versions).

**Measured, not promised:** in the [published evals](evals/results/2026-11-21/README.md) the same model met
**16 of 18** expected behaviors with the skill and **6 of 18** without it (blind grading, raw answers included).

## Knowledge graph: fewer tokens per question

On install, `scripts/pbi_graph.py` (Python stdlib, offline, metadata only) reads every PBIP project:
TMDL model, PBIR report, SQL loads, `ficha.toml`, docs. It writes `powerbi-graph/`:

- `GRAPH_REPORT.md`: one page with models, hubs, communities and findings. Findings include unused
  columns and measures, broken visual fields, shared sources and divergent measures.
- `wiki/<model>.md`: one card per model with tables, columns, DAX, relationships, pages and the fields
  each visual uses.
- `graph.json` (GraphRAG-ready) and `graph.html`, the **Power BI Explorer**: graph, star schema,
  measure catalogue with DAX, page wireframes, theme and findings, offline. `pbi_graph.py view` opens it.

![Power BI Explorer](docs/assets/explorer-grafo.png)

The agent reads the report and the card instead of dozens of `*.tmdl`/`visual.json` files. On the
small [example project](examples/contas-a-receber), ~18.9k tokens of source become a ~1k-token report and a
~1.3k-token card (19× fewer); savings grow with project size. For
targeted lookups it runs `query`, `explain`, `impact` ("what breaks if I change this measure?") and
`path`.

The installer also adds a short section to `AGENTS.md`/`CLAUDE.md`. It adds refresh hooks too: Claude
Code `SessionStart` + after edits, and git `post-commit/merge/checkout`. In Claude Code every report or
model edit is also audited; the agent hears about blockers or a page below harmony 90 at once. Everything is idempotent.
`pbi_graph.py uninstall` removes it all. Details:
[references/graph.md](skills/powerbi-architect/references/graph.md).

## Inside
- `SKILL.md` — eight laws, workflow with two human gates, visual decision tree.
- `references/` — modeling, one-step Power Query (8 connectors), DAX, TMDL, PBIR, product-grade report
  design, visual selection, custom visuals, documentation page (INFO.VIEW), refactoring, performance,
  security, quality checklist.
- `templates/pbiviz-bullet-kpi/` — a **verified** reference custom visual: type-checks, passes the
  official ESLint config and packages with `pbiviz package` with no recommended feature missing
  (rendering events, landing page, selection, context menu, tooltips, highlights, localization,
  keyboard, high contrast, allowInteractions, no network). Rebuilt in CI.
- `scripts/audit_pbip.py` — offline audit of any PBIP folder: rule codes with file and line, matching
  Tabular Editor Best Practice Analyzer IDs, `--json` / `--sarif`, suppressions
  ([rules, in Portuguese](docs/regras-auditoria.md)).
- `templates/pbir-pages/` and `templates/theme/` — schema-validated PBIR pages and an accessible theme.
- `examples/contas-a-receber/` — a complete PBIP project that follows every rule.

Reports follow the look of Twenty, the open-source CRM: grey canvas, quiet sidebar with the page navigator,
white panel with hairline borders, a thin top bar with breadcrumb and compact filters, one font family
(Segoe UI) in small sizes, one accent colour. Tables are named `ft_<subject>` (facts) and `dm_<entity>`
(dimensions). The audit flags oversized slicers, fonts outside the type scale and visuals off the 4 px grid.

![Overview page of the example project, with sample data](docs/assets/exemplo-visao-geral.png)

The agent never lays out a report by eye: it describes pages as rows of visuals and
`scripts/pbir_layout.py` computes every position on the 4 px grid (shell, icons, KPI lines, charts,
tables, drill-through, tooltip and phone layouts); `scripts/preview_pbir.py` draws each page so the agent
looks at it before delivering; `scripts/make_theme.py` builds a brand theme with checked contrast; and
`scripts/audit_pbip.py` scores each page's harmony from 0 to 100 (deliver at 90+).
- `scripts/pbi_graph.py` — offline knowledge graph + query/explain/impact/path (installed automatically).

Uses the Microsoft **Power BI Modeling MCP** when available (model edits + DAX validation).

## Contributing

DAX patterns, connectors, page archetypes, translations and evals are welcome, in English or Portuguese.
Agent ignored the skill? Something broken? Have an idea or eval results?
[Open an issue](https://github.com/DaviMark/powerbi-architect/issues/new/choose) using the matching
template. Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first PR; questions go to
[SUPPORT.md](SUPPORT.md), vulnerabilities to [SECURITY.md](SECURITY.md). Release notes:
[CHANGELOG.md](CHANGELOG.md).

MIT licensed. Power BI is a Microsoft trademark; this project is independent.
