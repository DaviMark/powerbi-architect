import { Tokens, el, sv, clear, tint, shrinkToFit } from "./dom";

/** One slice of the ring, or one line of the goal's legend. Texts arrive formatted. */
export interface RingPart {
    label: string;
    value: number;
    text: string;
    share?: string;          // "41%": the slice's part of the whole
}

/**
 * What the ring shows. Two uses:
 * - parts: a whole split into ≤ 6 slices (aging buckets, channels), the total or a rate in the centre;
 * - goal:  progress towards a target, the share reached in the centre and a tick at the target.
 */
export interface RingModel {
    title: string;
    center: string;           // "R$ 4,2 mi", "82%"
    centerNote?: string;      // "vencido", "da meta"
    parts: RingPart[];
    goal?: { progress: number; legend: RingPart[]; tone?: "good" | "bad" | "neutral" };
}

const GAP = 0.012;            // gap between slices, as a share of the circle

/** Shades of the accent: the largest slice is the accent itself, the rest fade towards the context grey. */
export function ringColours(n: number, t: Tokens): string[] {
    if (t.highContrast) {
        return Array.from({ length: n }, (_v, i) => i === 0 ? t.accent : t.track);
    }
    const steps = [0, 0.38, 0.6, 0.76, 0.86, 0.92];
    return Array.from({ length: n }, (_v, i) => tint(t.accent, steps[Math.min(i, steps.length - 1)]));
}

function arc(cx: number, cy: number, r: number, from: number, to: number): string {
    const a0 = (from - 0.25) * Math.PI * 2, a1 = (to - 0.25) * Math.PI * 2;
    const large = to - from > 0.5 ? 1 : 0;
    const p = (a: number) => `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
    return `M${p(a0)} A${r.toFixed(2)},${r.toFixed(2)} 0 ${large} 1 ${p(a1)}`;
}

/**
 * Card: title on top; the ring with the number in its centre; a legend of the slices with value and share
 * at the right (or under the ring when the card is narrow). `hook` binds events to each slice and row.
 */
export function renderRing(root: HTMLElement, m: RingModel, w: number, h: number, t: Tokens,
    hook?: (node: Element, i: number) => void): void {
    clear(root);
    const pad = 16;
    const card = el("div", `position:relative;box-sizing:border-box;width:${w}px;height:${h}px;padding:${pad}px;` +
        `font-family:${t.font};color:${t.ink};overflow:hidden;display:flex;flex-direction:column;gap:12px`);
    card.setAttribute("role", "figure");
    card.setAttribute("aria-label", [m.title, m.center, m.centerNote].filter(Boolean).join(", "));
    card.appendChild(el("div", "font-size:14px;font-weight:600;line-height:20px;white-space:nowrap;overflow:hidden;" +
        "text-overflow:ellipsis", m.title));

    const bodyH = h - pad * 2 - 32;
    const side = w >= 300;
    const legendRows = m.goal ? m.goal.legend : m.parts;
    const legendH = legendRows.length * 28;
    const narrow = w < 360;       // a phone: a smaller ring, and the legend keeps the label and the value
    const size = Math.max(64, Math.floor(side ? Math.min(bodyH, (w - pad * 2) * (narrow ? 0.34 : 0.4))
        : Math.min(w - pad * 2, bodyH - legendH - 12)));
    const body = el("div", `display:flex;${side ? "flex-direction:row" : "flex-direction:column"};align-items:center;` +
        `gap:${side && !narrow ? 20 : 12}px;flex:1;min-height:0`);

    const stroke = Math.max(8, Math.round(size * 0.11));
    const r = (size - stroke) / 2;
    const c = size / 2;
    const holder = el("div", `position:relative;width:${size}px;height:${size}px;flex:none`);
    const svg = sv("svg", { width: size, height: size, viewBox: `0 0 ${size} ${size}`, "aria-hidden": "true" });
    svg.appendChild(sv("circle", { cx: c, cy: c, r: r.toFixed(2), fill: "none", stroke: t.highContrast ? t.track : t.faint,
        "stroke-width": stroke }));

    const colours = ringColours(m.parts.length, t);
    if (m.goal) {
        const p = Math.max(0, Math.min(m.goal.progress, 1));
        const tone = m.goal.tone && m.goal.tone !== "neutral" && !t.highContrast ? t.tones[m.goal.tone].fg : t.accent;
        if (p > 0) {
            svg.appendChild(sv("path", { d: p >= 0.999 ? arc(c, c, r, 0, 0.9999) : arc(c, c, r, 0, p), fill: "none",
                stroke: tone, "stroke-width": stroke, "stroke-linecap": "round" }));
        }
    } else {
        const total = m.parts.reduce((s, x) => s + Math.max(x.value, 0), 0) || 1;
        let at = 0;
        m.parts.forEach((part, i) => {
            const share = Math.max(part.value, 0) / total;
            const gap = m.parts.length > 1 ? GAP : 0;
            if (share > gap) {
                const seg = sv("path", { d: arc(c, c, r, at + gap / 2, at + share - gap / 2), fill: "none", stroke: colours[i],
                    "stroke-width": stroke });
                svg.appendChild(seg);
                if (hook) {
                    hook(seg, i);
                }
            }
            at += share;
        });
    }
    holder.appendChild(svg as unknown as HTMLElement);
    const mid = el("div", "position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;" +
        "justify-content:center;text-align:center;pointer-events:none");
    const big = size >= 140 ? 22 : size >= 104 ? 18 : 15;
    const centerEl = el("div", `font-size:${big}px;font-weight:600;letter-spacing:-.01em;line-height:1.15;` +
        `font-variant-numeric:tabular-nums;white-space:nowrap;max-width:${size - stroke * 2 - 8}px;overflow:hidden;` +
        "text-overflow:ellipsis", m.center);
    mid.appendChild(centerEl);
    if (m.centerNote) {
        mid.appendChild(el("div", `font-size:11px;color:${t.muted};line-height:14px;margin-top:2px;white-space:nowrap`,
            m.centerNote));
    }
    holder.appendChild(mid);
    body.appendChild(holder);

    const legend = el("div", `display:flex;flex-direction:column;gap:0;flex:1;min-width:0;${side ? "" : "width:100%"}`);
    legend.setAttribute("role", "list");
    legendRows.forEach((part, i) => {
        const row = el("div", "display:flex;align-items:center;gap:8px;height:28px;font-size:12px;line-height:16px;" +
            (i ? `border-top:1px solid ${t.faint}` : ""));
        row.setAttribute("role", "listitem");
        const dot = m.goal ? (i === 0 ? t.accent : i === 1 ? t.muted : t.faint) : colours[i];
        row.appendChild(el("span", `width:8px;height:8px;border-radius:2px;flex:none;background:${dot}` +
            (t.highContrast ? `;border:1px solid ${t.ink}` : "")));
        row.appendChild(el("span", `flex:1;min-width:0;color:${t.muted};white-space:nowrap;overflow:hidden;` +
            "text-overflow:ellipsis", part.label));
        row.appendChild(el("span", "font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap", part.text));
        if (part.share && !narrow) {
            row.appendChild(el("span", `width:34px;text-align:right;color:${t.muted};font-variant-numeric:tabular-nums;` +
                "white-space:nowrap", part.share));
        }
        if (hook && !m.goal) {
            hook(row, i);
        }
        legend.appendChild(row);
    });
    body.appendChild(legend);
    card.appendChild(body);
    root.appendChild(card);
    shrinkToFit(centerEl, 11);
}
