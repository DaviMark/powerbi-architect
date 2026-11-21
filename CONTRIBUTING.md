# Contributing

Welcome! Improvements to modeling guidance, DAX patterns, connectors, page archetypes, translations and
evals are all valuable.

Rules:
1. `SKILL.md` stays under 500 lines — detail goes to `references/` (progressive disclosure).
2. Be precise. Every syntax example (TMDL, PBIR, M, DAX, TypeScript) must be valid; say what you verified.
3. No real data, hosts or company names in examples.
4. `scripts/` stays standard-library Python and offline. `audit_pbip.py` is read-only; `pbi_graph.py`
   writes only its output folder and the marked blocks/hooks described in `references/graph.md`.
5. Run before a PR:
   ```bash
   python -m unittest discover -s tests -v
   ```
   Changing the custom visual? Build it: see `.github/workflows/ci.yml › pbiviz`.
6. Add or update an eval in `evals/cases.md` when you change behavior.

AI-facing files are written in English; the Portuguese README is the main human entry point
(English version in `README.en.md`).
