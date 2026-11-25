import { Tokens, el, sv, clear, niceTicks, tint, shrinkToFit } from "./dom";

export interface TrendModel {
    title: string;
    total?: string;          // headline in the header ("R$ 48,3 mi")
    totalNote?: string;      // "no período", "▲ 8% vs ano anterior"
    labels: string[];        // periods, oldest first
    values: number[];
    valueTexts: string[];
    seriesName: string;
    compare?: number[];      // a second series drawn as lighter bars beside (last year, plan)
    compareTexts?: string[];
    compareName?: string;
    highlight?: "last" | "max" | "none";
    tick: (v: number) => string;
}

export type BarHook = (bar: SVGElement, index: number) => void;

/**
 * Header with the title, the headline number and a legend; dense columns on dashed gridlines. One column
 * is the focus (the latest period by default) in ink with its value above it; the rest are grey.
 */
export function renderTrend(root: HTMLElement, m: TrendModel, w: number, h: number, t: Tokens, hook?: BarHook): void {
    clear(root);
    const pad = 16;
    const box = el("div", `box-sizing:border-box;width:${w}px;height:${h}px;padding:${pad - 2}px ${pad}px ${pad - 4}px;` +
        `font-family:${t.font};color:${t.ink};display:flex;flex-direction:column`);

    let note: HTMLElement | undefined;
    const head = el("div", "display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex:none");
    const left = el("div", "display:flex;flex-direction:column;gap:2px;min-width:0");
    left.appendChild(el("div", "font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", m.title));
    if (m.total) {
        const line = el("div", "display:flex;align-items:baseline;gap:8px;margin-top:6px;white-space:nowrap;min-width:0");
        line.appendChild(el("span", "font-size:22px;font-weight:600;letter-spacing:-.01em;font-variant-numeric:tabular-nums", m.total));
        if (m.totalNote) {
            // A phone keeps only the variation ("▲ 13,9%"): the period and the comparison do not fit.
            const short = w < 420 ? (m.totalNote.match(/[▲▼=]\s?[\d.,]+\s?%?/) || [m.totalNote])[0] : m.totalNote;
            note = el("span", `font-size:11px;color:${t.muted};overflow:hidden;text-overflow:ellipsis;min-width:0;` +
                `display:inline-block;max-width:${Math.max(40, w - pad * 2 - 130)}px`, short);
            line.appendChild(note);
        }
        left.appendChild(line);
    }
    head.appendChild(left);
    const legend = el("div", `display:flex;gap:14px;font-size:11px;color:${t.muted};white-space:nowrap;padding-top:2px`);
    const key = (colour: string, name: string) => {
        const k = el("span", "display:inline-flex;align-items:center;gap:6px");
        k.appendChild(el("span", `width:8px;height:8px;border-radius:2px;background:${colour}`));
        k.appendChild(document.createTextNode(name));
        legend.appendChild(k);
    };
    key(t.accent, m.seriesName);
    if (m.compare && m.compareName) {
        key(t.track, m.compareName);
    }
    if (w >= 420) {               // narrow (a phone): the headline note already names the comparison
        head.appendChild(legend);
    }
    box.appendChild(head);

    const plotH = h - (m.total ? 70 : 40) - pad;
    if (plotH < 60 || m.values.length === 0) {
        root.appendChild(box);
        if (note) {
            shrinkToFit(note, 8);
        }
        return;
    }
    const plotW = w - pad * 2;
    const all = m.values.concat(m.compare || []).filter(v => isFinite(v));
    const ticks = niceTicks(Math.min(0, ...all), Math.max(...all, 0), 4);
    const lo = ticks[0], hi = ticks[ticks.length - 1];
    const axisW = Math.max(...ticks.map(v => m.tick(v).length)) * 6 + 8;
    const xLabelH = 18;
    const innerW = plotW - axisW, innerH = plotH - xLabelH - 18;   // 18 px on top for the focus label
    const y = (v: number) => 18 + innerH * (1 - (v - lo) / (hi - lo || 1));

    const svg = sv("svg", { width: plotW, height: plotH, role: "img", "aria-label": m.title });
    (svg as SVGElement).style.cssText = "display:block;margin-top:10px;overflow:visible";
    ticks.forEach(v => {
        svg.appendChild(sv("line", { x1: axisW, x2: plotW, y1: y(v).toFixed(1), y2: y(v).toFixed(1), stroke: t.faint,
            "stroke-dasharray": v === lo ? "0" : "3 3" }));
        const lab = sv("text", { x: axisW - 8, y: (y(v) + 3.5).toFixed(1), "text-anchor": "end", "font-size": 10, fill: t.muted });
        lab.textContent = m.tick(v);
        svg.appendChild(lab);
    });

    const n = m.values.length;
    const slot = innerW / n;
    const pair = !!(m.compare && m.compare.length);
    const group = Math.min(slot * (pair ? 0.72 : 0.58), pair ? 28 : 18);
    const bw = pair ? group / 2 - 1 : group;
    const focus = m.highlight === "none" ? -1 : m.highlight === "max"
        ? m.values.indexOf(Math.max(...m.values)) : n - 1;
    const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(innerW / 52))));

    for (let i = 0; i < n; i++) {
        const cx = axisW + i * slot + slot / 2;
        const draw = (v: number, x: number, colour: string, idx: number) => {
            const top = y(Math.max(v, 0)), base = y(Math.min(v, 0));
            const bar = sv("rect", { x: x.toFixed(1), y: top.toFixed(1), width: bw.toFixed(1),
                height: Math.max(1, base - top).toFixed(1), rx: Math.min(3, bw / 3), fill: colour });
            svg.appendChild(bar);
            if (hook && idx >= 0) {
                hook(bar, idx);
            }
        };
        if (pair) {
            draw((m.compare as number[])[i], cx - group / 2, t.track, -1);
            draw(m.values[i], cx + 1, i === focus || focus < 0 ? t.accent : tint(t.accent, 0.3), i);
        } else {
            draw(m.values[i], cx - bw / 2, i === focus ? t.accent : t.track, i);
        }
        if (i % every === (n - 1) % every || i === n - 1) {
            const last = i === n - 1;   // the last label ends at the plot's edge, never past it
            const lab = sv("text", { x: (last ? Math.min(cx + slot / 2, plotW) : cx).toFixed(1), y: plotH - 4,
                "text-anchor": last ? "end" : "middle", "font-size": 10,
                fill: i === focus ? t.ink : t.muted, "font-weight": i === focus ? 600 : 400 });
            lab.textContent = m.labels[i] || "";
            svg.appendChild(lab);
        }
    }
    if (focus >= 0) {
        const cx = axisW + focus * slot + slot / 2 + (pair ? group / 4 : 0);
        const text = m.valueTexts[focus] || "";
        const tw = text.length * 6.4 + 14;
        const ty = Math.max(0, y(Math.max(m.values[focus], 0)) - 26);
        const tx = Math.min(Math.max(cx - tw / 2, axisW), plotW - tw);
        svg.appendChild(sv("rect", { x: tx.toFixed(1), y: ty.toFixed(1), width: tw.toFixed(1), height: 20, rx: 6, fill: t.accent }));
        const lab = sv("text", { x: (tx + tw / 2).toFixed(1), y: (ty + 14).toFixed(1), "text-anchor": "middle",
            "font-size": 11, "font-weight": 600, fill: t.highContrast ? t.surface : "#FFFFFF" });
        lab.textContent = text;
        svg.appendChild(lab);
    }
    box.appendChild(svg as unknown as HTMLElement);
    root.appendChild(box);
    if (note) {
        shrinkToFit(note, 8);
    }
}
