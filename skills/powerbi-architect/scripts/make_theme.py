#!/usr/bin/env python3
"""make_theme.py — brand theme from one colour (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Writes one theme JSON.

    python make_theme.py --primary "#0F766E" [--name "Acme"] [--font "Segoe UI"] [--out acme-theme.json]

Starts from the skill's Twenty-inspired theme (templates/theme) and swaps the accent for the brand
colour: focus series, table accent, links, sequential ramp, selected states. Every colour is checked
against white: text colours must reach 4.5:1 and graphical colours 3:1; the brand colour is darkened
step by step until it passes, and the report says by how much. Categorical colours after the first are
chosen from calm Radix tones (the scales Twenty uses) so that every pair stays distinguishable for
people with protanopia, deuteranopia and tritanopia (simulated with Machado et al. 2009), never close
to the good/bad status red and green. Fonts outside Power BI's supported list are
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


# ---------------------------------------------------------------------- colour-vision deficiency
# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB.
CVD = {"protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216),
                      (-0.003882, -0.048116, 1.051998)),
       "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413),
                        (-0.011820, 0.042940, 0.968881)),
       "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602),
                      (0.004733, 0.691367, 0.303900))}
STATUS = ("#CE2C31", "#00824D")          # good/bad colours of the theme: never categorical
# Steps 9–11 of the Radix scales (the colours Twenty is built on), without red and green.
CANDIDATES = ["#0090FF", "#0588F0", "#0D74CE", "#3E63DD", "#3358D4", "#3A5BC7", "#5B5BD6", "#5151CD", "#5753C6",
              "#6E56CF", "#654DC4", "#6550B9", "#8E4EC6", "#8347B9", "#8145B5", "#AB4ABA", "#A144AF", "#953EA3",
              "#D6409F", "#CF3897", "#C2298A", "#E93D82", "#DF3478", "#CB1D63", "#F76B15", "#EF5F00", "#CC4E00",
              "#AB6400", "#AD7F58", "#A07553", "#815E46", "#A18072", "#957468", "#7D5E54", "#978365", "#8C7A5E",
              "#71624B", "#00A2C7", "#0797B9", "#107D98", "#12A594", "#0D9B8A", "#008573", "#2C9DC0", "#00749E"]


def linear(h: str) -> tuple:
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in hex_to_rgb(h))


def lab(rgb_lin) -> tuple:
    r, g, b = rgb_lin
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x / 0.95047), f(y), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def simulate(h: str, kind: str) -> tuple:
    rgb = linear(h)
    return tuple(max(0.0, min(1.0, sum(row[j] * rgb[j] for j in range(3)))) for row in CVD[kind])


def distances(a: str, b: str) -> dict:
    """CIE76 ΔE between two colours as seen with normal vision and with each colour-vision deficiency."""
    def de(p, q):
        return sum((x - y) ** 2 for x, y in zip(lab(p), lab(q))) ** 0.5
    out = {"normal": de(linear(a), linear(b))}
    for kind in CVD:
        out[kind] = de(simulate(a, kind), simulate(b, kind))
    return out


def separation(a: str, b: str) -> float:
    """How far apart two colours stay for everyone (tritanopia is rarer and compresses blues: weighted)."""
    d = distances(a, b)
    return min(d["normal"], d["protanopia"], d["deuteranopia"], d["tritanopia"] * 1.6)


def worst_pair(palette: list) -> tuple:
    """(ΔE, colour, colour, vision) of the two colours most alike for someone."""
    worst = (999.0, "", "", "")
    for i, a in enumerate(palette):
        for b in palette[i + 1:]:
            for kind, v in distances(a, b).items():
                if v < worst[0]:
                    worst = (v, a, b, kind)
    return worst


def cvd_palette(accent: str, n: int = 6) -> list:
    """Accent first, then the calm candidate farthest from everything chosen, for every kind of vision."""
    base_l = lab(linear(accent))[0]
    pool = [c for c in CANDIDATES if contrast(c) >= 3 and all(separation(c, s) > 14 for s in STATUS)]

    def chroma(c):
        _, a, b = lab(linear(c))
        return (a * a + b * b) ** 0.5
    palette = [accent]
    while len(palette) < n and pool:
        best = max(pool, key=lambda c: min(separation(c, p) for p in palette)
                   - 0.35 * abs(lab(linear(c))[0] - base_l) - 0.15 * max(0.0, chroma(c) - 55))
        palette.append(best)
        pool.remove(best)
    return palette


def build(primary: str, name: str, font: str) -> tuple[dict, list[str]]:
    notes = []
    theme = json.loads(BASE.read_text(encoding="utf-8"))
    accent, steps = darken_until(primary, 4.5)
    if steps:
        notes.append(f"{primary.upper()} has {contrast(primary):.2f}:1 on white; darkened to {accent} "
                     f"({contrast(accent):.2f}:1) so it also works for text and selected states")
    palette = cvd_palette(accent)
    d, a, b, kind = worst_pair(palette)
    notes.append(f"6 categorical colours, distinguishable with protanopia, deuteranopia and tritanopia; the "
                 f"closest pair is {a} / {b} (ΔE {d:.0f} with {kind})")
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
    for stream in (sys.stdin, sys.stdout, sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
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
