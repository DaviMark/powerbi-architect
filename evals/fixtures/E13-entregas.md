# E13 fixture: a model the skill has never seen

The E11 model is the skill's own example, which favours the skill (it ships a layout for it). E13 uses
a logistics model that is not in the skill: entregas, transportadoras and cidades, with on-time rate,
average delay, returns and freight cost. The model is generated from
[`E13-entregas-modelo.json`](E13-entregas-modelo.json) by the kit engine, then the report is removed.

## Setup
```bash
python - <<'PY'
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, "skills/powerbi-architect/scripts")
import new_project
kit = json.loads(Path("evals/fixtures/E13-entregas-modelo.json").read_text(encoding="utf-8"))
out = Path(".tmp/e13")
new_project.generate(kit, out, "Entregas", "localhost", "dw", None)
rp = out / "Entregas.Report"
pbir = (rp / "definition.pbir").read_text(encoding="utf-8")
shutil.rmtree(rp); rp.mkdir(); (rp / "definition.pbir").write_text(pbir, encoding="utf-8")
for f in ("layout.json", "README.md", "preview-sample.json"):
    (out / f).unlink()
PY
```
Copy `.tmp/e13` once per condition. The agent with the skill may read `skills/powerbi-architect/`; the
agent without it may not read anything in this repository.

## Scoring
```bash
python skills/powerbi-architect/scripts/audit_pbip.py <folder> --json      # blockers, PBI019, PBI054
python skills/powerbi-architect/scripts/audit_pbip.py <folder>             # last line: harmony per page
python tools/validate_schemas.py <folder>/Entregas.Report                  # schema errors
python skills/powerbi-architect/scripts/preview_pbir.py <folder>/Entregas.Report --sample sample.json --png out/
```
The blind grader receives the two overview previews in random order as A and B, plus the brief, and
answers which better serves the logistics director and why, on hierarchy, alignment, readability,
colour with meaning and whether the page answers the question. It does not know a skill is involved.
