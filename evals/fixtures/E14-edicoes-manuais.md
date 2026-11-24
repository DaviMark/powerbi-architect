# E14 fixture: edits made by hand between two requests

The user said it plainly: when they change the PBIP by hand, the agent must notice on its own, keep the
change and build on it. This case reproduces that.

## Setup
1. Generate the sales kit: `python skills/powerbi-architect/scripts/new_project.py vendas <folder>`.
2. Take the snapshot the agent's last edit would leave: `python skills/powerbi-architect/scripts/pbip_changes.py accept <folder>`.
3. Edit by hand, as Power BI Desktop would (files saved with another indentation):
   - "Receita por regional" (Visão Geral): width 1024 → 500 and title → "Receita por regional (gestão comercial)";
   - a new bar chart "Receita por segmento" at x 748 in the freed space;
   - `_Medidas.tmdl`: `'Meta % Margem' = 0.30` → `0.32`.
4. Give the agent the prompt from `cases.md`. It is not told about the edits.

## Scoring
A script reads the folder after the run and checks the four "Must" items; the audit gives blockers and
harmony; the agent's reply is read for the "Should" item.
