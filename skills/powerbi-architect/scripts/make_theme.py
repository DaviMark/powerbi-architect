#!/usr/bin/env python3
"""make_theme.py — brand theme from one colour (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Writes one theme JSON.

    python make_theme.py --primary "#0F766E" [--name "Acme"] [--font "Segoe UI"] [--out acme-theme.json]

Starts from the skill's Twenty-inspired theme (templates/theme) and swaps the accent for the brand
colour: focus series, table accent, links, sequential ramp, selected states. Every colour is checked
against white: text colours must reach 4.5:1 and graphical colours 3:1; the brand colour is darkened
step by step until it passes, and the report says by how much. Categorical colours after the first are
the theme's, reordered so none sits next to a similar hue. Fonts outside Power BI's supported list are
refused with the reason (they would fall back to another font in the service).
"""
from __future__ import annotations

import argparse
import colorsys
import copy
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "templates" / "theme" / "powerbi-architect-acessivel.json"
# Fonts that render in the Power BI service (subset of the supported list that reads as professional).
SUPPORTED_FONTS = {"Segoe UI", "Segoe UI Light", "Segoe UI Semibold", "Segoe UI Bold", "Arial", "Calibri",
                   "Candara", "Corbel", "Georgia", "Lucida Sans Unicode", "Tahoma", "Trebuchet MS", "Verdana"}


def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"colour must be #RRGGBB, got #{h}")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02X}" for c in rgb)


def luminance(h: str) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(h)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str = "#FFFFFF") -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def darken_until(h: str, target: float) -> tuple[str, int]:
    """Lower lightness in 2 % steps until the colour reaches `target` contrast on white."""
    r, g, b = hex_to_rgb(h)
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    steps = 0
    out = h.upper()
    while contrast(out) < target and light > 0:
        light = max(0.0, light - 0.02)
        steps += 1
        out = rgb_to_hex(colorsys.hls_to_rgb(hue, light, sat))
    return out, steps


def tint(h: str, amount: float) -> str:
    """Mix with white: amount 0 = colour, 1 = white."""
    return rgb_to_hex(tuple(c + (1 - c) * amount for c in hex_to_rgb(h)))


def hue_of(h: str) -> float:
    return colorsys.rgb_to_hls(*hex_to_rgb(h))[0]


def build(primary: str, name: str, font: str) -> tuple[dict, list[str]]:
    notes = []
    theme = json.loads(BASE.read_text(encoding="utf-8"))
    accent, steps = darken_until(primary, 4.5)
    if steps:
        notes.append(f"{primary.upper()} has {contrast(primary):.2f}:1 on white; darkened to {accent} "
                     f"({contrast(accent):.2f}:1) so it also works for text and selected states")
    # Candidates: the theme's colours plus more of Twenty's tag colours (all ≥ 4.3:1 on white).
    extra = ["#5753C6", "#CB1D63", "#2A7E3B", "#7C5E48"]   # never the good/bad status colours
    others = theme["dataColors"][1:] + [theme["dataColors"][0]] + extra
    others = sorted(others, key=lambda c: abs(((hue_of(c) - hue_of(accent) + 0.5) % 1) - 0.5), reverse=True)
    palette = [accent]
    for c in others:
        if len(palette) == 6:
            break
        if all(abs(((hue_of(c) - hue_of(p) + 0.5) % 1) - 0.5) > 0.06 for p in palette):
            palette.append(c)
    for c in palette:
        if contrast(c) < 3:
            raise ValueError(f"palette colour {c} is below 3:1 on white")
    t = copy.deepcopy(theme)
    t["name"] = name
    t["dataColors"] = palette
    t.update({"tableAccent": accent, "hyperlink": accent, "maximum": accent,
              "center": tint(accent, 0.55), "minimum": tint(accent, 0.88)})
    if font != "Segoe UI":
        if font not in SUPPORTED_FONTS:
            raise ValueError(f"'{font}' is not in Power BI's supported font list; the service would replace it. "
                             "Keep Segoe UI and use the brand font in images and slides only")
        semibold = font if font.startswith("Segoe UI") else font
        notes.append(f"font {font}: one family; titles use the same family (no semibold weight available)"
                     if not font.startswith("Segoe UI") else f"font {font}")
        for cls in t["textClasses"].values():
            cls["fontFace"] = semibold if cls["fontFace"].endswith("Semibold") else font
        raw = json.dumps(t["visualStyles"]).replace("Segoe UI Semibold", semibold).replace("Segoe UI", font)
        t["visualStyles"] = json.loads(raw)
    for k in ("foreground", "foregroundNeutralSecondary", "foregroundNeutralTertiary", "hyperlink"):
        if contrast(t[k]) < 4.5:
            raise ValueError(f"{k} {t[k]} is below 4.5:1 on white")
    return t, notes


def main() -> int:
    ap = argparse.ArgumentParser(prog="make_theme.py", description="Brand theme from one colour.")
    ap.add_argument("--primary", required=True, help="brand colour, #RRGGBB")
    ap.add_argument("--name", default="Power BI Architect")
    ap.add_argument("--font", default="Segoe UI", help="a font from Power BI's supported list (default Segoe UI)")
    ap.add_argument("--out", type=Path, default=Path("theme.json"))
    args = ap.parse_args()
    try:
        theme, notes = build(args.primary, args.name, args.font)
    except ValueError as e:
        print(f"make_theme.py: error: {e}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(theme, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for n in notes:
        print(f"- {n}")
    print(f"[ok] {args.out}: accent {theme['dataColors'][0]} ({contrast(theme['dataColors'][0]):.2f}:1), "
          f"{len(theme['dataColors'])} categorical colours, all ≥ 3:1 on white")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
