"""Build the skill's custom visuals. Run from the repository root (needs Node.js 18+):

    python tools/build_visuals.py            # preview bundle + the three .pbiviz packages
    python tools/build_visuals.py --preview  # only the preview bundle (fast)

1. Compiles the shared drawing core (templates/visuals/core/*.ts) into one plain script,
   scripts/visuals.js, that preview_pbir.py embeds: the preview draws with the same code as Power BI.
2. For each visual (templates/visuals/architect-*), copies it with the core into .tmp/visuals, installs the
   toolchain, runs the official ESLint config and `pbiviz package`, and copies the package to
   templates/visuals/dist/<name>.pbiviz.

Downloads npm packages (powerbi-visuals-tools and the visuals' dependencies) into .tmp only.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISUALS = ROOT / "skills" / "powerbi-architect" / "templates" / "visuals"
CORE = VISUALS / "core"
BUNDLE = ROOT / "skills" / "powerbi-architect" / "scripts" / "visuals.js"
WORK = ROOT / ".tmp" / "visuals"
ORDER = ["dom", "kpi", "list", "trend"]
NPM = "npm.cmd" if sys.platform == "win32" else "npm"
NPX = "npx.cmd" if sys.platform == "win32" else "npx"


def sh(cmd: list, cwd: Path) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"failed in {cwd}: {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")


def toolchain() -> Path:
    tools = WORK / "_tools"
    if not (tools / "node_modules" / ".bin").exists():
        tools.mkdir(parents=True, exist_ok=True)
        (tools / "package.json").write_text('{"name":"tools","private":true}', encoding="utf-8")
        sh([NPM, "install", "--no-audit", "--no-fund", "powerbi-visuals-tools@7", "typescript@5.5.4"], tools)
    return tools


def preview_bundle(tools: Path) -> None:
    out = WORK / "_core"
    shutil.rmtree(out, ignore_errors=True)
    sh([NPX, "tsc", *[str(CORE / f"{n}.ts") for n in ORDER], "--target", "es2019", "--module", "es2020",
        "--lib", "es2019,dom", "--strict", "--skipLibCheck", "--moduleResolution", "node",
        "--typeRoots", str(CORE), "--outDir", str(out)], tools)
    parts = []
    for n in ORDER:
        js = (out / f"{n}.js").read_text(encoding="utf-8")
        js = re.sub(r"^import .*?;\s*$", "", js, flags=re.M)
        js = re.sub(r"^export (?=(const|function|let|class) )", "", js, flags=re.M)
        js = re.sub(r"^export \{\};?\s*$", "", js, flags=re.M)
        parts.append(f"// ---- {n}.ts\n{js.strip()}\n")
    body = "\n".join(parts)
    BUNDLE.write_text("/* Built by tools/build_visuals.py from templates/visuals/core: do not edit. */\n"
                      "(function () {\n\"use strict\";\n" + body +
                      "window.PBIArchitect = { TOKENS, brandTokens, tint, renderKpi, renderList, renderTrend, toneOf };\n})();\n",
                      encoding="utf-8", newline="\n")
    print(f"[ok] {BUNDLE.relative_to(ROOT)}")


def package(name: str, tools: Path) -> None:
    src = VISUALS / name
    dest = WORK / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    shutil.rmtree(WORK / "core", ignore_errors=True)
    shutil.copytree(CORE, WORK / "core")
    sh([NPM, "install", "--no-audit", "--no-fund"], dest)
    sh([NPX, "eslint", "."], dest)
    sh([NPX, "pbiviz", "package"], dest)
    built = next((dest / "dist").glob("*.pbiviz"))
    (VISUALS / "dist").mkdir(exist_ok=True)
    shutil.copy(built, VISUALS / "dist" / f"{name}.pbiviz")
    guid = json.loads((src / "pbiviz.json").read_text(encoding="utf-8"))["visual"]["guid"]
    print(f"[ok] {name}: dist/{name}.pbiviz ({guid})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", action="store_true", help="only the preview bundle")
    a = ap.parse_args()
    tools = toolchain()
    preview_bundle(tools)
    if not a.preview:
        for project in sorted(VISUALS.glob("architect-*")):
            package(project.name, tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
