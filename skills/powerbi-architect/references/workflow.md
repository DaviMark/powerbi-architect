# Workflow — from brief to published report

## Contents
1. Mode detection · 2. Standalone folder layout · 3. Phase by phase · 4. Gate templates · 5. Communication

## 1. Mode detection

| You find | Mode | Rules |
|---|---|---|
| `AGENTS.md` + `workspaces.toml` + `_sistema/pbw.py` | **Power BI Workspaces** | Use its tree (`dashboards/<empresa>/<área>/<subárea>/<dashboard>/`, same layout as below), its CLI (`pbw novo · prototipo · abrir · sincronizar-sql · documentar · validar`), its gates. |
| A `.pbip` / `*.SemanticModel` / `*.Report` folder | **Existing PBIP** | Keep its structure; add `trabalho-da-ia/` and a `LEIA-ME.md` next to it if missing. |
| Only a `.pbix` | **Convert first** | Ask the user to *File › Save as › Power BI project (.pbip)* (or export a `.pbit` for analysis). You cannot edit `.pbix`. |
| Nothing yet | **Standalone** | Use the layout below. |

## 2. Dashboard layout (standalone and Power BI Workspaces)

```
<dashboard>/
├── LEIA-ME.md                "onde coloco o quê" + living documentation
├── 1-seu-pedido/             the user's — read, never rewrite
│   ├── PEDIDO.md             form: objective · audience · questions · §4 business rules · §5 visuals wanted · filters
│   └── anexos/               SQL they know, prints, PDFs
├── 2-power-bi/               <Name>.pbip + .Report/ + .SemanticModel/ — must open at EVERY step
├── 3-entrega/                <Name>.pbit (exported by the human)
└── trabalho-da-ia/           yours: ficha.toml · sql/<Table>.sql · desenho.md (Gate 1) ·
                              conferencia.md (Gate 2) · dicionario.md · historico.md · legado/
```

Numbered folders belong to the user; never ask them to open `trabalho-da-ia/` — summarize it in chat.
Visual identity is **per company**, never per dashboard: `identidade-visual/<empresa>/` (Power BI
Workspaces applies it to every dashboard of the company with `pbw identidade <empresa>`).

Folder and file names follow the project language (above: `pt-BR`, the Power BI Workspaces default).
`.gitignore` must contain `*.pbix`, `*.abf`, `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`.

**The PBIP is always openable.** Create it first (Power BI Workspaces: `pbw novo`; standalone: a
minimal PBIP with the Documentation page) and keep it valid after every change, so the user can open
it in Power BI Desktop at any moment.

## 3. Phase by phase

### Phase 0 — Intake
Read everything the user gave you. Produce **at most 5** questions, only those whose answer changes the
model. Good questions: *"Is 'revenue' net of returns?"*, *"One row per order or per order line?"*,
*"Should managers see only their branch?"*. Bad questions: anything you can infer or decide yourself.

### Phase 1 — Design + prototype (stop at Gate 1)
`trabalho-da-ia/desenho.md` (from PEDIDO §4 rules → Métricas, PEDIDO §5 visuals → Páginas):
1. **Modelo**: mermaid `erDiagram`; table list with **type, grain, key, imported columns, source**;
   "not imported and why"; relationship directions; storage mode.
2. **Métricas**: folder · name · business definition · DAX sketch · format · who validates.
3. **Páginas**: per page `### <Page>`, `**Pergunta:** …` and a table `| Zona | Visual | Campos | Por que |`
   with **one row per visual** (zones: Filtro, KPIs, Tendência, Explicação, Detalhe).
4. **Decisões**: context → decision → consequence for anything non‑obvious.

Then draw the **prototype** so the user sees the pages in Power BI Desktop before any data: in Power BI
Workspaces run `pbw prototipo <dashboard>`; standalone, create the pages as PBIR textboxes (grey boxes
on the 8‑px grid naming the planned visual and fields, plus a footer with the word `PROTÓTIPO`).

### Phase 2 — Data (SQL)
- Write in the **dialect of the connection** (T‑SQL, HANA SQL, BigQuery Standard SQL, PostgreSQL,
  Snowflake, Databricks SQL, Oracle, MySQL). See `power-query.md` › dialect notes.
- Header tags (Power BI Workspaces reads them): `-- @table`, `-- @description`, `-- @grain`, optional
  `-- @connection`, `-- @mode`.
- Explicit columns, aliases = final model column names (`AS [Data Vencimento]`), CAST every type,
  business filters in `WHERE`, integer keys, no `ORDER BY`, no `SELECT *`.
- Prefer stable **views** in a `bi`/`analytics` schema when you can ask the DBA; the SQL file then
  becomes a thin `SELECT` from the view.

### Phase 3 — Model
- Declare every column (`dataType`, `sourceColumn` = alias, `summarizeBy: none`, hide keys and raw
  numerics used only by measures, `sortByColumn` for month/weekday names and ordinal buckets).
- Relationships: dimension `1` → fact `*`, single direction. Date relationship on the main date.
- Measures in a dedicated measure table (`_Medidas` / `_Measures`), with description, format, folder.
- Helper tables: `dm_calendario` (or source date dim), `_Documentacao`, `_Cargas` (see `documentation.md`).
- With the MCP: open the PBIP folder, apply changes in a transaction, run DAX checks, save.

### Phase 4 — Report
Replace each prototype page by the real page with the same name (see `report-design.md`, `pbir.md`);
a real page has no `PROTÓTIPO` text. Apply the brand theme. Keep the Documentation page. Set alt text
and tab order.

### Phase 5 — Custom visual
Only via the decision tree (SKILL.md §4). See `custom-visuals.md`.

### Phase 6 — Verify (stop at Gate 2)
- Structural: validator (`pbw validar` or `scripts/audit_pbip.py`), JSON parse, no hard‑coded hosts,
  the PBIP opens.
- Numerical: DAX checks in `trabalho-da-ia/conferencia.md` with control totals and reconciliation identities
  (e.g. `[Vencido] + [A vencer] = [Saldo]`) and reference numbers from a trusted
  source (SQL run by the user, ERP report, legacy dashboard). Ask the user to refresh in Desktop and
  fill "obtained" — or run the checks yourself through the MCP.

### Phase 7 — Document
`LEIA-ME.md` (all sections), `trabalho-da-ia/historico.md`, version (SemVer), dictionary generation,
catalog update. Ask the user to export the `.pbit` (*File › Export › Power BI template*).

## 4. Gate templates

**Gate 1 message (keep it short):**
```
Design + prototype ready for approval — <dashboard>
• Model: 1 fact (<grain>), 3 dimensions, dm_calendario · 19 columns imported (of 63 available)
• Metrics: 8 (Valores 3 · Indicadores 2 · Contagens 2 · Textos 1)
• Pages: Visão Geral (question: …), Documentação
• Open decisions: <1–3 bullets, each with your recommendation>
Open it: pbw abrir <dashboard> (grey boxes = planned visuals) · details: trabalho-da-ia/desenho.md
Approve, or tell me what to change.
```

**Gate 2 message:**
```
Implementation done — validator: 0 errors, 2 warnings (explained below).
Please open it (pbw abrir <dashboard>), Refresh, then compare trabalho-da-ia/conferencia.md (4 checks).
If all match I'll mark it for review and update LEIA-ME/histórico.
```

## 5. Communication

Decisions, not narration. Lists over paragraphs at gates. Always say what you did **not** verify.
