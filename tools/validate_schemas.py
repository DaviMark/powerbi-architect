#!/usr/bin/env python3
"""Validate PBIP/PBIR JSON files against Microsoft's published JSON schemas.

Development tool (not part of the skill): needs network access and `pip install jsonschema`.
Schemas are fetched from github.com/microsoft/json-schemas and cached in .tmp/schemas.

    python tools/validate_schemas.py [paths...]      default: examples/ and skills/**/templates/
    python tools/validate_schemas.py --references    JSON examples in SKILL.md and references/

Each file is validated against the schema in its own "$schema" property. Exit code 1 on errors.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

from jsonschema import Draft7Validator, validators
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".tmp" / "schemas"
MS = "https://developer.microsoft.com/json-schemas/"
RAW = "https://raw.githubusercontent.com/microsoft/json-schemas/main/"


def fetch(uri: str) -> dict:
    url = uri.replace(MS, RAW) if uri.startswith(MS) else uri
    cached = CACHE / url.replace("https://", "").replace("/", "_")
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (fixed host)
            cached.write_bytes(r.read())
    return json.loads(cached.read_text(encoding="utf-8-sig"))


def retrieve(uri: str) -> Resource:
    return Resource.from_contents(fetch(uri), default_specification=DRAFT7)


def show(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def validate(path: Path, registry: Registry) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    uri = data.get("$schema") if isinstance(data, dict) else None
    if not uri or not uri.startswith(MS):
        return []
    schema = fetch(uri)
    cls = validators.validator_for(schema, default=Draft7Validator)
    v = cls({**schema, "$id": schema.get("$id", uri)}, registry=registry)
    return [f"{show(path)}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:300]}"
            for e in sorted(v.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))]


def reference_snippets() -> list[Path]:
    """Write every complete JSON example with a Microsoft $schema from the references to .tmp/."""
    out_dir = ROOT / ".tmp" / "reference-snippets"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for md in sorted(ROOT.glob("skills/*/references/*.md")) + sorted(ROOT.glob("skills/*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        for m in re.finditer(r"^```json\n(.*?)^```", text, re.M | re.S):
            if MS not in m.group(1):
                continue
            line = text.count("\n", 0, m.start()) + 1
            f = out_dir / f"{md.stem}-line{line}.json"
            f.write_text(m.group(1), encoding="utf-8")
            files.append(f)
    return files


def main(argv: list[str]) -> int:
    if argv == ["--references"]:
        argv = [str(f) for f in reference_snippets()]
    targets = [Path(a).resolve() for a in argv] or [ROOT / "examples", *ROOT.glob("skills/*/templates")]
    files = sorted({f for t in targets for f in ([t] if t.is_file() else t.rglob("*.json"))
                    if "node_modules" not in f.parts})
    registry = Registry(retrieve=retrieve)
    errors, checked = [], 0
    for f in files:
        try:
            found = validate(f, registry)
        except json.JSONDecodeError as e:
            found = [f"{show(f)}: invalid JSON: {e}"]
        if found or '"$schema"' in f.read_text(encoding="utf-8-sig"):
            checked += 1
        errors += found
    for e in errors:
        print(e)
    print(f"{checked} file(s) with a Microsoft $schema checked, {len(errors)} error(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
