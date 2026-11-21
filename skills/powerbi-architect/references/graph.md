# Power BI knowledge graph (`scripts/pbi_graph.py`)

A persistent, offline graph of every PBIP project in the repository. It exists to save tokens: one
model card (~2k tokens) replaces reading a model's TMDL, PBIR and SQL files (often 30k+ tokens), and
`query`/`explain`/`impact` answer most lookups in a few hundred tokens.

Python 3.9+ standard library. No network, no data: it reads metadata files only.

## What it reads

| Source | Becomes |
|---|---|
| `*.SemanticModel/definition/**/*.tmdl` | model, tables (role: fact/dimension/date/measures/system), columns, measures with DAX, relationships, parameters, RLS roles |
| DAX in measures, calculated columns/tables, RLS | `uses_measure` / `uses_column` / `uses_table` / `filters` edges |
| M partitions | Power Query step count, parameters used, source objects read by `Value.NativeQuery` SQL |
| `*.Report/definition/**` (PBIR) | report → model binding, pages in order, visuals with type, title and every field they use (incl. filters, conditional formatting) |
| `*.sql` | SQL file → table (same name as the model table) and source objects (`FROM`/`JOIN`) |
| `trabalho-da-ia/ficha.toml` (Power BI Workspaces; legacy `ficha.toml`/`dashboard.toml`) | dashboard: status, owner, connection, refresh, classification |
| `*.md` inside a dashboard | doc nodes + `mentions` of the dashboard's tables/measures (INFERRED) |
| `*.py` | modules, top-level functions/classes, imports |

Edges are `EXTRACTED` (read from a file) or `INFERRED` (convention or name match).
Not graphed (reported in `GRAPH_REPORT.md`): `model.bim` models and legacy `report.json` reports. Save them as PBIP with TMDL and PBIR.

## Outputs (`powerbi-graph/`, git-ignored by default)

| File | Use |
|---|---|
| `GRAPH_REPORT.md` | first read: dashboards, models, hubs, communities, findings, suggested questions |
| `wiki/<model>.md` | model card: tables + columns (`UNUSED` flagged), relationships, measures with DAX and usage counts, pages → visuals → fields |
| `graph.json` | full graph (nodes, edges, communities, findings), GraphRAG-ready |
| `graph.html` | interactive view for humans (self-contained, offline) |
| `manifest.json` | fingerprints used by `update` |

## Commands

```bash
python scripts/pbi_graph.py install  [REPO] [--no-hooks] [--no-agents] [--commit-graph]
python scripts/pbi_graph.py build    [ROOT]            # full rebuild
python scripts/pbi_graph.py update   [ROOT] [--quiet]  # rebuild only if a file (or this script) changed
python scripts/pbi_graph.py query    "<question>" [--budget 1500] [--dfs]
python scripts/pbi_graph.py explain  "<name>"
python scripts/pbi_graph.py impact   "<name>"
python scripts/pbi_graph.py path     "<from>" "<to>"
python scripts/pbi_graph.py stats
python scripts/pbi_graph.py uninstall [REPO]
```

Names match accent- and case-insensitively: `"Saldo em Aberto"`, `"Fato Titulos[Dias Atraso]"` and
`"dias atraso"` all work.

## Findings it reports

- Visual fields not found in the model (broken after a rename).
- Columns imported but never used by a measure, visual, relationship, sort or RLS (law 3).
- Measures used by no visual and no other measure.
- Tables with no relationship, more than one Power Query step, measures without description.
- Pages with more than 8 data visuals, bidirectional relationships.
- Source objects read by more than one model (conformed-dimension / reuse candidates).
- The same measure name with different DAX in different models.

Treat findings as leads, not verdicts. A column can be used by an external Excel report or a
composite model the graph cannot see, so confirm with the user before you delete anything.

## How `install` wires it in

1. Builds `powerbi-graph/`. A `.gitignore` inside the folder keeps it out of Git; `--commit-graph` commits it instead.
2. Adds a marked section (`<!-- powerbi-graph:start/end -->`) to `AGENTS.md` and to `CLAUDE.md` (skipped
   when `CLAUDE.md` already imports `@AGENTS.md`), and to `.github/copilot-instructions.md` if that file exists.
3. Claude Code hooks in `.claude/settings.json`: `update --quiet` on `SessionStart` and after
   `Edit|Write|MultiEdit|NotebookEdit`.
4. Git hooks `post-commit`, `post-merge` and `post-checkout` run `update --quiet`. Existing hooks are kept, and the block is appended.

Every step is idempotent. `uninstall` removes exactly these blocks and the output folder.

## Agent rules

- Read `GRAPH_REPORT.md` → model card → `explain`. Open raw files only to edit them.
- Run `impact` before renaming or deleting a measure, column or table, and list the affected visuals in your plan.
- After editing outside Claude Code, run `update`. It costs nothing when nothing changed.
- The graph describes metadata. It never proves numbers are right, so Gate 2 still needs a check against a trusted source.
