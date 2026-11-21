"""Checks every code example in SKILL.md and references/ (CONTRIBUTING rule 2: examples must be valid).

Standard library only and offline. Full JSON Schema validation of PBIR examples runs in CI through
tools/validate_schemas.py --references (needs network and jsonschema).
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "powerbi-architect"
sys.path.insert(0, str(SKILL / "scripts"))
import audit_pbip as ap  # noqa: E402

FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)


def blocks(lang: str):
    for md in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
        text = md.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            if m.group(1) == lang:
                line = text.count("\n", 0, m.start()) + 1
                yield f"{md.relative_to(ROOT)}:{line}", m.group(2)


def strip_strings_and_comments(code: str, comments=("//", "--")) -> str:
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    for c in comments:
        code = re.sub(rf"{re.escape(c)}.*$", "", code, flags=re.M)
    return re.sub(r'"(?:[^"]|"")*"', '""', code)


def balanced(code: str, pairs=("()", "[]", "{}")) -> bool:
    stack, closing = [], {b: a for a, b in pairs}
    opening = {a for a, _ in pairs}
    for ch in code:
        if ch in opening:
            stack.append(ch)
        elif ch in closing:
            if not stack or stack.pop() != closing[ch]:
                return False
    return not stack


class TestReferenceExamples(unittest.TestCase):
    def test_json_blocks_parse(self):
        bad = []
        for where, code in blocks("json"):
            text = code.strip()
            candidates = [text, "{" + text + "}", "{" + text.rstrip(",") + "}"]
            if not any(self._parses(c) for c in candidates):
                bad.append(where)
        self.assertEqual(bad, [], "JSON examples that do not parse (also tried wrapping fragments in {})")

    @staticmethod
    def _parses(text: str) -> bool:
        try:
            json.loads(text)
            return True
        except ValueError:
            return False

    def test_tmdl_blocks_use_tabs_and_parse(self):
        bad = []
        for where, code in blocks("tmdl"):
            for n, line in enumerate(code.splitlines(), 1):
                if re.match(r"^ +\S", line) or re.match(r"^\t* +\t", line):
                    bad.append(f"{where} +{n}: indentation must use tabs")
            if re.search(r"^table ", code, re.M):
                tmp = ROOT / ".tmp" / "ref_tmdl.tmdl"
                tmp.parent.mkdir(exist_ok=True)
                tmp.write_text(code, encoding="utf-8")
                tables = ap.parse_table_file(tmp)
                declared = len(re.findall(r"^\t(?:measure|column) ", code, re.M))
                parsed = sum(len(t.columns) + len(t.measures) for t in tables)
                if declared != parsed:
                    bad.append(f"{where}: {declared} columns/measures declared, parser read {parsed}")
            if not balanced(strip_strings_and_comments(code, comments=("//",))):
                bad.append(f"{where}: unbalanced brackets")
        self.assertEqual(bad, [])

    def test_dax_blocks_are_balanced(self):
        bad = [w for w, code in blocks("dax") if not balanced(strip_strings_and_comments(code))]
        self.assertEqual(bad, [])

    def test_m_blocks_are_balanced(self):
        bad = []
        for where, code in blocks("m"):
            clean = strip_strings_and_comments(code, comments=("//",))
            if not balanced(clean) or (re.search(r"\blet\b", clean) and not re.search(r"\bin\b", clean)):
                bad.append(where)
        self.assertEqual(bad, [])

    def test_schema_urls_point_to_microsoft(self):
        bad = [f"{w}: {u}" for w, code in blocks("json")
               for u in re.findall(r'"\$schema":\s*"([^"]+)"', code)
               if not u.startswith("https://developer.microsoft.com/json-schemas/fabric/")]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
