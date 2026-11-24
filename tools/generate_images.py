"""Regenerate the report images of the README and the guide. Run from the repository root:

    python tools/generate_images.py

Rebuilds examples/contas-a-receber from its layout.json with the skill's theme, then renders at 2x with
scripts/preview_pbir.py (needs Edge, Chrome or Chromium):

- docs/assets/exemplo-visao-geral.png, exemplo-diagnostico.png, exemplo-celular.png  (the example)
- docs/assets/kit-<kit>.png                                                           (each starter kit)
- docs/assets/reestilizar-antes.png, reestilizar-depois.png        (an amateur report, then restyled)

The component gallery has its own script: tools/generate_gallery.py.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "powerbi-architect" / "scripts"
THEME = ROOT / "skills" / "powerbi-architect" / "templates" / "theme" / "powerbi-architect-acessivel.json"
EXAMPLE = ROOT / "examples" / "contas-a-receber"
REPORT = EXAMPLE / "ContasReceber.Report"
ASSETS = ROOT / "docs" / "assets"
KITS = ("vendas", "financeiro", "rh", "estoque")
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))


def run(*args) -> None:
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"failed: {' '.join(map(str, args))}\n{r.stdout}\n{r.stderr}")


def render(report: Path, sample: Path, out: Path, *, mobile: bool = False) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    args = [SCRIPTS / "preview_pbir.py", report, "--png", out, "--png-scale", 2, "--out", out / "preview.html"]
    if sample.exists():
        args += ["--sample", sample]
    if mobile:
        args.append("--mobile")
    run(*args)
    return out


def main() -> int:
    from legacy_report import make_legacy
    import pbir_layout

    run(SCRIPTS / "pbir_layout.py", EXAMPLE / "layout.json", REPORT, "--theme", THEME)
    shutil.copy(THEME, REPORT / "StaticResources" / "RegisteredResources" / THEME.name)
    sample = EXAMPLE / "preview-sample.json"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        pages = render(REPORT, sample, tmp / "ex")
        shutil.copy(pages / "page-1.png", ASSETS / "exemplo-visao-geral.png")
        shutil.copy(pages / "page-2.png", ASSETS / "exemplo-diagnostico.png")
        phone = render(REPORT, sample, tmp / "phone", mobile=True)
        shutil.copy(phone / "page-1-mobile.png", ASSETS / "exemplo-celular.png")
        for kit in KITS:
            proj = tmp / f"kit-{kit}"
            run(SCRIPTS / "new_project.py", kit, proj)
            report = next(proj.glob("*.Report"))
            shutil.copy(render(report, proj / "preview-sample.json", tmp / f"png-{kit}") / "page-1.png",
                        ASSETS / f"kit-{kit}.png")
        proj = tmp / "restyle"
        shutil.copytree(EXAMPLE / "ContasReceber.SemanticModel", proj / "ContasReceber.SemanticModel")
        legacy = make_legacy(REPORT, proj / "ContasReceber.Report")
        shutil.copy(render(legacy, sample, tmp / "before") / "page-1.png", ASSETS / "reestilizar-antes.png")
        spec, _ = pbir_layout.extract(legacy)
        builder = pbir_layout.Builder(spec)
        builder.build(legacy)
        builder.register_resources(legacy, THEME)
        shutil.copy(render(legacy, sample, tmp / "after") / "page-1.png", ASSETS / "reestilizar-depois.png")
    print("[ok] images in docs/assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
