#!/usr/bin/env python3
"""reconcile.py — prove the report's numbers against the source, row by row (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Reads two CSV files; writes nothing unless --out is given.

    python reconcile.py source.csv report.csv --keys "Ano-Mês,Regional" [--abs 0.01] [--rel 0.0001]
    python reconcile.py --dax "Valor Vencido,% Vencido" --by "dm_calendario[Ano-Mês],dm_regional[Regional]"

The first form compares a trusted result (the SQL on the warehouse, finance's closing file) with the
model's result (a DAX query exported from DAX Studio, the Power BI Modeling MCP or Desktop's performance
analyzer) on the same grain. Every numeric column present in both files is compared; keys missing on
either side are listed; the totals of each column are compared too. Exit code 1 when anything differs
beyond the tolerance, so it can gate a delivery or a CI job.

The second form prints the DAX query to export at that grain, and the SQL skeleton to match it.

CSV details handled: ',' or ';' separators, UTF-8 with or without BOM, pt-BR numbers ("1.234,56"),
percentages ("22,6%"), currency symbols, blanks as missing. Keys are compared as trimmed text.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path


def read(path: Path) -> tuple[list[str], list[dict]]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    header = list(rows[0].keys()) if rows else []
    return header, rows


def comma_decimal(rows: list[dict]) -> bool:
    """True when the file writes numbers the Brazilian way (1.234,56), decided once for the whole file."""
    cells = [v for r in rows[:500] for v in r.values() if isinstance(v, str)]
    br = sum(bool(re.search(r"\d\.\d{3},\d|\d,\d{1,2}%?$", c.strip())) for c in cells)
    us = sum(bool(re.search(r"\d,\d{3}\.\d|\d\.\d{1,2}%?$", c.strip())) for c in cells)
    return br > us


def number(raw: str | None, comma: bool = False) -> float | None:
    """'R$ 1.234,56' → 1234.56 (comma=True) · '1,234.56' → 1234.56 · '22,6%' → 0.226 · '' → None."""
    if raw is None:
        return None
    s = raw.strip()
    if not s or s.upper() in ("NULL", "NAN", "(BLANK)"):
        return None
    pct = s.endswith("%")
    s = re.sub(r"[^\d,.\-eE+]", "", s)
    if not s or s in "-+":
        return None
    s = s.replace(".", "").replace(",", ".") if comma else s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v / 100 if pct else v


def short(name: str) -> str:
    """'dm_regional[Regional]' and 'Regional' both match 'Regional'."""
    m = re.search(r"\[([^\]]+)\]\s*$", name)
    return (m.group(1) if m else name).strip().lower()


def reconcile(src: Path, rep: Path, keys: list[str], abs_tol: float, rel_tol: float) -> tuple[list[str], bool]:
    hs, rs = read(src)
    hr, rr = read(rep)
    map_s, map_r = {short(h): h for h in hs}, {short(h): h for h in hr}
    key_names = [short(k) for k in keys]
    missing = [k for k in key_names if k not in map_s or k not in map_r]
    if missing:
        raise ValueError(f"key column(s) {', '.join(missing)} not in both files "
                         f"(source: {', '.join(hs)}; report: {', '.join(hr)})")
    measures = [c for c in map_s if c in map_r and c not in key_names]
    if not measures:
        raise ValueError("no value column with the same name in both files")

    def index(rows, mp):
        out = {}
        for r in rows:
            k = tuple((r.get(mp[k]) or "").strip() for k in key_names)
            out[k] = r
        return out
    a, b = index(rs, map_s), index(rr, map_r)
    ca, cb = comma_decimal(rs), comma_decimal(rr)
    lines, bad = [], False
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    for label, keys_ in (("only in the source", only_a), ("only in the report", only_b)):
        if keys_:
            bad = True
            lines.append(f"{len(keys_)} key(s) {label}: " + "; ".join(" · ".join(k) for k in keys_[:8])
                         + (" …" if len(keys_) > 8 else ""))
    diffs = []
    totals = {m: [0.0, 0.0] for m in measures}
    for k in sorted(set(a) & set(b)):
        for m in measures:
            x, y = number(a[k].get(map_s[m]), ca), number(b[k].get(map_r[m]), cb)
            totals[m][0] += x or 0.0
            totals[m][1] += y or 0.0
            if x is None and y is None:
                continue
            if (x is None) != (y is None):
                diffs.append((k, m, x, y, float("inf")))
                continue
            d = abs(x - y)
            if d > abs_tol and d > rel_tol * max(abs(x), abs(y)):
                diffs.append((k, m, x, y, d))
    if diffs:
        bad = True
        lines.append(f"{len(diffs)} value(s) differ beyond ±{abs_tol:g}" + (f" and ±{rel_tol:g} relative" if rel_tol else "") + ":")
        for k, m, x, y, d in sorted(diffs, key=lambda t: -t[4] if t[4] != float("inf") else float("-inf"))[:25]:
            lines.append(f"  {' · '.join(k)} › {map_s[m]}: source {x if x is not None else 'blank'} · "
                         f"report {y if y is not None else 'blank'}" + (f" (Δ {y - x:+,.6g})" if x is not None and y is not None else ""))
    for m, (x, y) in totals.items():
        if "%" in m or "percent" in m or "taxa" in m:
            continue                       # a sum of percentages means nothing; the rows were compared above
        same = abs(x - y) <= max(abs_tol, rel_tol * max(abs(x), abs(y)))
        lines.append(f"total {map_s[m]}: source {x:,.6g} · report {y:,.6g} " + ("[ok]" if same else "[differs]"))
        bad = bad or not same
    lines.insert(0, f"{len(set(a) & set(b))} matching key(s), {len(measures)} value column(s): {', '.join(map_s[m] for m in measures)}")
    return lines, bad


def dax_template(measures: list[str], by: list[str]) -> str:
    groups = ",\n        ".join(by)
    cols = ",\n        ".join(f'"{m}", [{m}]' for m in measures)
    sql_cols = ", ".join((re.search(r"\[([^\]]+)\]", c) or re.match(r"(.*)", c)).group(1) for c in by)
    return (f"// Run in DAX Studio or through the Power BI Modeling MCP; export the result as CSV.\n"
            f"EVALUATE\n    SUMMARIZECOLUMNS (\n        {groups},\n        {cols}\n    )\n"
            f"ORDER BY {', '.join(by)}\n\n"
            f"-- Matching SQL on the warehouse (same grain, same filters, same business rules):\n"
            f"-- SELECT {sql_cols}, <each measure written from the fact columns>\n"
            f"-- FROM <fact> JOIN <dimensions> ON <keys>\n-- GROUP BY {sql_cols}\n-- ORDER BY {sql_cols};\n")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
    ap = argparse.ArgumentParser(prog="reconcile.py", description="Compare the report's numbers with the source.")
    ap.add_argument("source", nargs="?", type=Path, help="CSV from the trusted source (SQL, finance)")
    ap.add_argument("report", nargs="?", type=Path, help="CSV from the model (DAX query)")
    ap.add_argument("--keys", default="", help="comma-separated key columns (the grain), e.g. 'Ano-Mês,Regional'")
    ap.add_argument("--abs", type=float, default=0.01, help="absolute tolerance (default 0.01: one cent)")
    ap.add_argument("--rel", type=float, default=0.0, help="relative tolerance, e.g. 0.0001 for 0.01%% (default 0)")
    ap.add_argument("--dax", help="print the DAX query for these comma-separated measures")
    ap.add_argument("--by", default="", help="with --dax: comma-separated group-by columns, Table[Column]")
    args = ap.parse_intermixed_args(argv)
    if args.dax:
        print(dax_template([m.strip() for m in args.dax.split(",") if m.strip()],
                           [c.strip() for c in args.by.split(",") if c.strip()]))
        return 0
    if not args.source or not args.report or not args.keys:
        ap.error("source, report and --keys are required (or use --dax)")
    try:
        lines, bad = reconcile(args.source, args.report, [k.strip() for k in args.keys.split(",")], args.abs, args.rel)
    except (OSError, ValueError) as e:
        print(f"reconcile.py: error: {e}", file=sys.stderr)
        return 2
    for ln in lines:
        print(ln)
    print("[differs] the numbers do not match: find the cause before delivering" if bad
          else "[ok] every key and every value matches within the tolerance")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
