import { Tone, Tokens, el, sv, clear, shrinkToFit } from "./dom";

/** What the KPI card shows. Texts arrive formatted (Power BI's formatter, or the preview's sample). */
export interface KpiModel {
    label: string;
    value: string;
    delta?: string;          // "▲ 8,2%": drawn as a pill coloured by tone
    tone?: Tone;
    note?: string;           // "vs out/26", "meta 15%"
    points?: number[];       // the trend, oldest first; the last point is the current period
    spark?: "auto" | "bars" | "line" | "none";
}

/**
 * Card: label on top, the value large, a pill with the variation and a quiet note under it, and a small
 * trend at the right (bars when the values vary a lot, a line when they move within a narrow band).
 */
export function renderKpi(root: HTMLElement, m: KpiModel, w: number, h: number, t: Tokens): void {
    clear(root);
    const compact = h < 100;
    const padY = compact ? 10 : 16;
    const padX = compact ? 12 : 16;
    const valueSize = h >= 140 ? 32 : compact ? 22 : 26;
    const card = el("div", `position:relative;box-sizing:border-box;width:${w}px;height:${h}px;padding:${padY}px ${padX}px;` +
        `font-family:${t.font};color:${t.ink};overflow:hidden;display:flex;flex-direction:column;` +
        `justify-content:space-between`);
    card.setAttribute("role", "figure");
    card.setAttribute("aria-label", [m.label, m.value, m.delta, m.note].filter(Boolean).join(", "));

    const pts = (m.points || []).filter(p => isFinite(p));
    const sparkKind = m.spark === "none" || pts.length < 2 || w < 200 ? "none"
        : m.spark === "bars" || m.spark === "line" ? m.spark
            : Math.min(...pts) / (Math.max(...pts) || 1) < 0.6 ? "bars" : "line";
    const sw = sparkKind === "none" ? 0 : Math.round(Math.min(Math.max(w * 0.3, 64), 120));
    const sh = compact ? 28 : 36;

    card.appendChild(el("div", `font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;` +
        `color:${t.muted};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:14px;` +
        `max-width:${w - padX * 2}px`, m.label));
    const valueEl = el("div", `font-size:${valueSize}px;font-weight:600;letter-spacing:-.01em;line-height:1.1;` +
        `font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;` +
        `max-width:${w - padX * 2 - (sw ? sw + 12 : 0)}px`, m.value);
    card.appendChild(valueEl);

    const foot = el("div", "display:flex;align-items:center;gap:6px;min-height:18px;white-space:nowrap;overflow:hidden");
    if (m.delta) {
        const tone = t.tones[m.tone || "neutral"];
        const pill = el("span", `display:inline-flex;align-items:center;padding:1px 7px;border-radius:999px;font-size:11px;` +
            `font-weight:600;line-height:16px;background:${tone.bg};color:${tone.fg};font-variant-numeric:tabular-nums` +
            (t.highContrast ? `;border:1px solid ${tone.fg}` : ""), m.delta);
        foot.appendChild(pill);
    }
    if (m.note) {
        foot.appendChild(el("span", `font-size:11px;color:${t.muted};overflow:hidden;text-overflow:ellipsis`, m.note));
    }
    card.appendChild(foot);

    if (sparkKind !== "none") {
        const svg = sv("svg", { width: sw, height: sh, "aria-hidden": "true" });
        (svg as SVGElement).style.cssText = `position:absolute;right:${padX}px;top:${padY + 20}px`;
        const max = Math.max(...pts), min = Math.min(...pts);
        if (sparkKind === "bars") {
            const slot = sw / pts.length;
            const bw = Math.max(2, slot * 0.62);
            pts.forEach((p, i) => {
                const bh = Math.max(2, (max > 0 ? p / max : 0) * sh);
                svg.appendChild(sv("rect", {
                    x: (i * slot + (slot - bw) / 2).toFixed(1), y: (sh - bh).toFixed(1), width: bw.toFixed(1),
                    height: bh.toFixed(1), rx: Math.min(1.5, bw / 2), fill: i === pts.length - 1 ? t.accent : t.track
                }));
            });
        } else {
            const span = max - min || 1;
            const xy = pts.map((p, i) => [2 + i * (sw - 6) / (pts.length - 1), 3 + (sh - 6) * (1 - (p - min) / span)]);
            svg.appendChild(sv("polyline", {
                points: xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "), fill: "none",
                stroke: t.track, "stroke-width": 1.75, "stroke-linejoin": "round", "stroke-linecap": "round"
            }));
            const [lx, ly] = xy[xy.length - 1];
            svg.appendChild(sv("circle", { cx: lx.toFixed(1), cy: ly.toFixed(1), r: 2.75, fill: t.accent }));
        }
        card.appendChild(svg as unknown as HTMLElement);
    }
    root.appendChild(card);
    shrinkToFit(valueEl, 14);
}
