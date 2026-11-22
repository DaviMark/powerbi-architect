"""How much of an agent's context the skill uses. Run from the repository root:

    python tools/context_cost.py [--markdown]

Three moments: the description is in context in every session (so the agent knows when to use the
skill), SKILL.md is read when the skill triggers, and each reference only when the task needs it.
Tokens are estimated as characters / 4, which is close for English Markdown and code; read them as
orders of magnitude, not exact counts. tests/test_skill.py keeps the budgets below.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "powerbi-architect"
BUDGET = {"description": 600, "SKILL.md": 12_500, "reference": 18_000}   # characters


def tokens(chars: int) -> int:
    return round(chars / 4)


def measure() -> list[tuple[str, str, int]]:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    desc = re.search(r"^description:\s*(.*)$", text, re.M).group(1)
    rows = [("sempre", "description (frontmatter)", len(desc)), ("ao acionar", "SKILL.md", len(text))]
    for ref in sorted((SKILL / "references").glob("*.md"), key=lambda p: -p.stat().st_size):
        rows.append(("sob demanda", f"references/{ref.name}", len(ref.read_text(encoding="utf-8"))))
    return rows


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = measure()
    md = "--markdown" in sys.argv
    if md:
        print("| Quando entra no contexto | Arquivo | Caracteres | Tokens (aprox.) |\n|---|---|---:|---:|")
    for when, name, chars in rows:
        print(f"| {when} | `{name}` | {chars:,} | {tokens(chars):,} |".replace(",", ".") if md
              else f"{when:<12} {name:<36} {chars:>7,} chars  ≈ {tokens(chars):>6,} tokens")
    refs = sum(c for w, _, c in rows if w == "sob demanda")
    always, trigger = rows[0][2], rows[0][2] + rows[1][2]
    summary = (f"Sempre: ≈ {tokens(always):,} tokens · ao acionar: ≈ {tokens(trigger):,} · "
               f"todas as referências juntas: ≈ {tokens(refs):,}")
    print(("\n" + summary.replace(",", ".")) if md else summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
