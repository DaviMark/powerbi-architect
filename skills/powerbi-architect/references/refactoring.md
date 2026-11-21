# Refactoring legacy dashboards

Goal: same answers (or better), a fraction of the model, zero Power Query logic, documented.

## 1. Get readable inputs
- Best: `.pbit` (*File › Export › Power BI template*) or PBIP (*File › Save as › .pbip*).
- Power BI Workspaces: `pbw refatorar` (folder `refatorar/`) or `pbw extrair arquivo.pbit` → Markdown + JSON.
- Standalone: `python <skill>/scripts/audit_pbip.py <pbip-folder>` for a PBIP; for a `.pbit`, unzip and
  read `DataModelSchema` (UTF‑16 JSON) and `Report/Layout` or `Report/definition/**`.

## 2. Inventory (fill this table)
| Item | Legacy | Target |
|---|---|---|
| Tables (source / calculated / auto date) | | |
| Columns imported / used | | |
| Power Query steps (max per table) | | 1 |
| Measures (documented) | | all |
| Relationships (bidirectional, M:M) | | 0 unless ADR |
| Pages / visuals | | |
| RLS roles | | |

## 3. Reverse‑engineer the questions
From pages, titles, visuals and measures, write the business questions the report answers. Mark each
as *inferred*. Ask the owner to confirm, delete obsolete ones and add missing ones — this is the
cheapest moment to simplify.

## 4. Redesign (Gate 1)
- New star schema at the right grain; conformed dimensions; one date table.
- **Column cut**: drop every column not used by measures, visuals, relationships, sorts or RLS
  (the extraction lists candidates — double‑check bare `[Column]` references and RLS filters).
- **Power Query → SQL**: translate each M step (filters → `WHERE`, merges → `JOIN`, type changes →
  `CAST`, added columns → expressions, groupings → `GROUP BY`, unpivots → `UNPIVOT`/`UNION`).
  Keep the order of operations; test row counts.
- **Calculated columns → SQL**; implicit measures → explicit; duplicated measures → one + parameter.
- **Parity map** in `trabalho-da-ia/desenho.md › Métricas`: `old measure → new measure (same/changed/removed, why)`.

## 5. Rebuild
Phases 2–7 of the workflow. Re‑create pages with the brand and the page archetypes; don't copy
legacy layouts that hurt comprehension — but keep what users rely on (names, filters) or explain changes.

## 6. Prove it
`trabalho-da-ia/conferencia.md` compares **legacy vs new** for the same filters: totals by period, top N entities,
a few known cases. Differences must be explained (bug fixed in legacy? rule clarified?) and approved.

## 7. Keep the trail
Never delete the extraction. Changelog entry: "Refatorado do legado <file> em <date> · tabelas X→Y ·
colunas A→B · etapas PQ N→1".
