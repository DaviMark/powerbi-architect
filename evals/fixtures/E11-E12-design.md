# E11 / E12 fixture: design cases scored by the repository's own tools

## E11 setup
1. Copy `examples/contas-a-receber/ContasReceber.SemanticModel` and `ContasReceber.pbip` to an empty folder.
2. Create `ContasReceber.Report/definition.pbir` pointing at `../ContasReceber.SemanticModel` (copy it from
   the example). Do not copy any other report file.
3. Give the agent the prompt from `cases.md`, with the folder as its working directory.

## Scoring (no human or model grader)
```bash
python skills/powerbi-architect/scripts/audit_pbip.py <folder> --json        # blockers, PBI046/047/048/052
python skills/powerbi-architect/scripts/audit_pbip.py <folder>               # last line: harmony per page
python tools/validate_schemas.py <folder>/ContasReceber.Report               # schema errors
```
For E12, validate `theme.json` against the report theme schema (Microsoft's `powerbi-desktop-samples`
repository) and compute contrast with `scripts/make_theme.py`'s `contrast()`.
