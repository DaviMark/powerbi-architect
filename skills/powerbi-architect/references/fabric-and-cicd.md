# Fabric, Direct Lake and CI/CD

## 1. Direct Lake

Storage mode for semantic models whose tables are Delta tables in OneLake (Fabric lakehouse or
warehouse). Columns are loaded into memory on demand from the Delta files, so there is no import refresh
copying data, and queries run at import speed when the data fits the capacity's guardrails.

**Choose Direct Lake when** the data already lands in a Fabric lakehouse/warehouse, tables are large, and
freshness matters. Stay with Import when the source is outside Fabric, the model is small, or you need
features Direct Lake tables do not support.

Design rules (they are the same eight laws, enforced earlier in the pipeline):
- **Star schema in the lakehouse.** Facts and dimensions are Delta tables (or warehouse tables/views)
  shaped by notebooks, pipelines or SQL, never by Power Query. Law 4 becomes "zero logic in the model".
- **Only needed columns.** Expose a gold-layer table or view with the columns the model needs; Direct Lake
  loads columns on demand, but every column still costs memory, framing time and confusion.
- **No calculated columns or calculated tables built on Direct Lake tables.** Compute them in the lakehouse.
  Measures, calculation groups and field parameters work as usual.
- **V-Order and file layout** (few large Parquet files, regular `OPTIMIZE`) are what keep queries fast;
  ask the data engineer, not the model, to fix slow scans.
- **Guardrails:** each capacity SKU limits rows per table, model size in memory and files per table. Above
  them, a Direct Lake **on SQL endpoint** model falls back to DirectQuery (slower), and a Direct Lake **on
  OneLake** model fails the query instead. Check the current limits for the user's SKU in the Microsoft
  docs before promising performance.
- **Framing** (the "refresh" of a Direct Lake model) only points the model at the latest Delta version.
  Decide with the user whether it is automatic (follows the lakehouse) or scheduled after the load
  pipeline finishes, so users never see a half-loaded day.
- **Security:** RLS defined in the model works; security defined in the SQL endpoint forces DirectQuery
  fallback in Direct Lake on SQL endpoint. Prefer model RLS and record the choice.
- **Mixing modes:** Direct Lake tables can live with Import tables in the same model only in newer
  versions/flavors; confirm support before designing a composite model, and record it as an ADR.

Editing: Direct Lake models are edited in the Fabric web modeling experience, in Desktop (live edit), or
as TMDL in a Git-connected workspace. The partition of a Direct Lake table has `mode: directLake` and an
entity source pointing at the lakehouse table; create the first table with the tools, then copy its shape.

## 2. Source control and environments

- **PBIP in Git** is the unit of work: TMDL + PBIR, reviewed in pull requests. Never commit `.pbix`, cache
  (`.pbi/cache.abf`) or `localSettings.json` (audit rule PBI001).
- **Fabric Git integration** connects a workspace to a branch (Azure DevOps or GitHub). Typical flow:
  feature branch → PR with review and CI → merge to `main` → workspace synced from `main` (Dev).
- **Deployment pipelines** promote Dev → Test → Prod and swap connections with deployment rules or
  parameters. Parameters (`Servidor`, `Banco`) are what make the same TMDL work in every stage, which is
  why law 4 forbids hard-coded servers (audit rule PBI003).
- **fabric-cicd** (Microsoft's Python library) deploys items from a repository folder to a workspace and
  replaces environment values from a `parameter.yml`; use it when deployments run from CI instead of the
  deployment pipeline UI.
- The two human gates do not move: design approval before building, number confirmation before Prod.

## 3. CI for Power BI repositories

Run on every pull request, all offline except where noted:

```yaml
# .github/workflows/powerbi.yml (excerpt)
- run: python .claude/skills/powerbi-architect/scripts/audit_pbip.py . --sarif > audit.sarif
  continue-on-error: true
- uses: github/codeql-action/upload-sarif@<pinned-sha>   # shows findings in the PR (Code scanning)
  with: { sarif_file: audit.sarif }
- run: python .claude/skills/powerbi-architect/scripts/audit_pbip.py . --fail-on blocker
- run: python .claude/skills/powerbi-architect/scripts/pbi_graph.py build . --quiet   # keeps the graph fresh
```

- Severity policy: block the merge on `blocker`; report `important` and `suggestion` in the PR.
  Tighten to `--fail-on important` once the backlog is clean.
- Suppress a rule only with a reason, in `.pbiaudit.json` or a TMDL annotation (see `--help`); existing
  Tabular Editor `BestPracticeAnalyzer_IgnoreRules` annotations are honored.
- Teams that already run the Best Practice Analyzer (Tabular Editor CLI) can keep it: the audit reports
  the equivalent BPA rule IDs, so findings line up.
- Pin every third-party action by commit SHA and give jobs read-only permissions.
