/* Built by tools/build_visuals.py from templates/visuals/core: do not edit. */
(function () {
"use strict";
// ---- dom.ts
/*
 * Shared drawing core of the powerbi-architect visuals. Plain DOM, no Power BI API and no libraries, so the
 * same code draws inside Power BI (src/visual.ts of each visual) and in the skill's preview
 * (scripts/visuals.js, built by tools/build_visuals.py). Never innerHTML: text goes through textContent.
 */
const TOKENS = {
    font: "'Segoe UI', wf_segoe-ui_normal, system-ui, sans-serif",
    accent: "#18181B",
    ink: "#18181B",
    muted: "#71717A",
    faint: "#EBEBEE",
    track: "#D4D4D8",
    surface: "#FAFAFA",
    tones: {
        good: { fg: "#15803D", bg: "#DCFCE7" },
        bad: { fg: "#B91C1C", bg: "#FEE2E2" },
        warn: { fg: "#B45309", bg: "#FEF3C7" },
        info: { fg: "#0369A1", bg: "#E0F2FE" },
        neutral: { fg: "#52525B", bg: "#F4F4F5" }
    },
    highContrast: false
};
/** Tokens for Windows high contrast: two colours, no tints. */
function highContrastTokens(foreground, background, selected) {
    const tone = { fg: foreground, bg: background };
    return {
        font: TOKENS.font, accent: foreground, ink: foreground, muted: foreground, faint: foreground, track: foreground,
        surface: background, tones: { good: tone, bad: tone, warn: tone, info: tone, neutral: { fg: selected, bg: background } },
        highContrast: true
    };
}
function el(tag, css, text) {
    const node = document.createElement(tag);
    node.style.cssText = css;
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}
const SVG_NS = "http://www.w3.org/2000/svg";
function sv(tag, attrs) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const k of Object.keys(attrs)) {
        node.setAttribute(k, String(attrs[k]));
    }
    return node;
}
function clear(node) {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}
/** Round, readable axis ticks between 0 (or min) and max. */
function niceTicks(lo, hi, count) {
    if (!(hi > lo)) {
        return [lo];
    }
    const raw = (hi - lo) / Math.max(count - 1, 1);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => s >= raw) || raw;
    const out = [];
    for (let v = Math.floor(lo / step) * step; v <= hi + step * 0.001; v += step) {
        out.push(Math.round(v / step) * step);
    }
    if (out[out.length - 1] < hi) {
        out.push(out[out.length - 1] + step);
    }
    return out;
}
/** Status word to tone: the common Portuguese and English words of business lists. */
function toneOf(status) {
    const s = status.toLowerCase();
    if (/(atras|vencid|crític|critic|cancel|bloque|reprov|perdid|falh|late|overdue|failed|lost|blocked|rejected)/.test(s)) {
        return "bad";
    }
    if (/(pendent|aguard|andamento|anális|analis|a vencer|em risco|parcial|pending|waiting|progress|review|risk)/.test(s)) {
        return "warn";
    }
    if (/(pago|quitad|conclu|entreg|aprovad|ativo|em dia|no prazo|ok\b|ganh|paid|done|delivered|approved|active|on time|won|success)/.test(s)) {
        return "good";
    }
    if (/(novo|nova|agendad|planejad|new|scheduled|planned)/.test(s)) {
        return "info";
    }
    return "neutral";
}
/** Two letters for an avatar: first letters of the first two words. */
function initials(name) {
    const words = name.replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).filter(Boolean);
    return ((words[0] || "?")[0] + (words.length > 1 ? words[1][0] : (words[0] || "")[1] || "")).toUpperCase();
}
const AVATARS = [["#E0E7FF", "#3730A3"], ["#FCE7F3", "#9D174D"], ["#DCFCE7", "#166534"], ["#FEF3C7", "#92400E"],
    ["#E0F2FE", "#075985"], ["#F3E8FF", "#6B21A8"], ["#FFE4E6", "#9F1239"], ["#F4F4F5", "#3F3F46"]];
/** A stable soft colour per name (no randomness: the same name always gets the same colour). */
function avatarColours(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
    }
    const pair = AVATARS[hash % AVATARS.length];
    return [pair[0], pair[1]];
}
/** The report's identity on top of the defaults: brand accent, text colours, font. Empty values keep the default. */
function brandTokens(brand) {
    const out = { ...TOKENS, tones: TOKENS.tones };
    Object.keys(brand).forEach(k => {
        const v = brand[k];
        if (v) {
            out[k] = k === "font" ? `'${v}', ${TOKENS.font}` : v;
        }
    });
    return out;
}
/** a mixed with white: share 0 keeps a, 1 is white. */
function tint(hex, share) {
    const h = hex.replace("#", "");
    if (!/^[0-9a-fA-F]{6}$/.test(h)) {
        return hex;
    }
    return "#" + [0, 2, 4].map(i => {
        const c = parseInt(h.slice(i, i + 2), 16);
        return Math.round(c + (255 - c) * share).toString(16).padStart(2, "0");
    }).join("");
}

// ---- kpi.ts
/**
 * Card: label on top, the value large, a pill with the variation and a quiet note under it, and a small
 * trend at the right (bars when the values vary a lot, a line when they move within a narrow band).
 */
function renderKpi(root, m, w, h, t) {
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
    card.appendChild(el("div", `font-size:${valueSize}px;font-weight:600;letter-spacing:-.01em;line-height:1.1;` +
        `font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;` +
        `max-width:${w - padX * 2 - (sw ? sw + 12 : 0)}px`, m.value));
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
        svg.style.cssText = `position:absolute;right:${padX}px;top:${padY + 20}px`;
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
        }
        else {
            const span = max - min || 1;
            const xy = pts.map((p, i) => [2 + i * (sw - 6) / (pts.length - 1), 3 + (sh - 6) * (1 - (p - min) / span)]);
            svg.appendChild(sv("polyline", {
                points: xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "), fill: "none",
                stroke: t.track, "stroke-width": 1.75, "stroke-linejoin": "round", "stroke-linecap": "round"
            }));
            const [lx, ly] = xy[xy.length - 1];
            svg.appendChild(sv("circle", { cx: lx.toFixed(1), cy: ly.toFixed(1), r: 2.75, fill: t.accent }));
        }
        card.appendChild(svg);
    }
    root.appendChild(card);
}

// ---- list.ts
/**
 * A list for people to act on: an avatar and the name (with a grey second line), status as a soft chip,
 * progress as a thin bar, numbers right-aligned. Sticky header; the body scrolls when rows do not fit.
 */
function renderList(root, m, w, h, t, hook) {
    clear(root);
    const twoLines = m.rows.some(r => r.sub);
    const rowH = twoLines ? 52 : 36;
    const avatars = m.avatars !== false;
    const titleH = m.title ? 40 : 0;
    const frame = el("div", `box-sizing:border-box;width:${w}px;height:${h}px;display:flex;flex-direction:column;` +
        `font-family:${t.font};color:${t.ink}`);
    if (m.title) {
        frame.appendChild(el("div", `flex:none;height:${titleH}px;box-sizing:border-box;padding:14px 16px 0;font-size:13px;` +
            "font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", m.title));
    }
    const wrap = el("div", `box-sizing:border-box;width:${w}px;height:${h - titleH}px;overflow:auto;font-size:12px`);
    const table = el("table", "width:100%;border-collapse:collapse;table-layout:auto");
    table.setAttribute("role", "grid");
    const head = el("thead", "");
    const hr = el("tr", "");
    const th = (text, right) => el("th", `position:sticky;top:0;z-index:1;background:${t.surface};` +
        `text-align:${right ? "right" : "left"};font-size:10px;font-weight:600;letter-spacing:.05em;` +
        `text-transform:uppercase;color:${t.muted};padding:8px 12px;line-height:13px;border-bottom:1px solid ${t.faint};white-space:nowrap`, text);
    hr.appendChild(th(m.itemTitle, false));
    m.columns.forEach(c => hr.appendChild(th(c.title, c.kind === "number")));
    head.appendChild(hr);
    table.appendChild(head);
    const body = el("tbody", "");
    m.rows.forEach((r, i) => {
        const tr = el("tr", `height:${rowH}px;border-bottom:1px solid ${t.faint}`);
        const first = el("td", "padding:0 12px;white-space:nowrap");
        const box = el("div", "display:flex;align-items:center;gap:10px;min-width:0");
        if (avatars) {
            const [bg, fg] = t.highContrast ? [t.surface, t.ink] : avatarColours(r.item);
            box.appendChild(el("span", `flex:none;width:28px;height:28px;border-radius:50%;display:inline-flex;` +
                `align-items:center;justify-content:center;font-size:11px;font-weight:600;background:${bg};color:${fg}`, initials(r.item)));
        }
        const names = el("div", "display:flex;flex-direction:column;min-width:0;line-height:16px");
        names.appendChild(el("span", "font-weight:600;overflow:hidden;text-overflow:ellipsis", r.item));
        if (r.sub) {
            names.appendChild(el("span", `font-size:11px;color:${t.muted};overflow:hidden;text-overflow:ellipsis`, r.sub));
        }
        box.appendChild(names);
        first.appendChild(box);
        tr.appendChild(first);
        r.cells.forEach(c => tr.appendChild(cell(c, t)));
        body.appendChild(tr);
        if (hook) {
            hook(tr, i);
        }
    });
    table.appendChild(body);
    wrap.appendChild(table);
    frame.appendChild(wrap);
    root.appendChild(frame);
}
function cell(c, t) {
    const td = el("td", `padding:0 12px;white-space:nowrap;text-align:${c.kind === "number" ? "right" : "left"};` +
        (c.kind === "number" ? "font-variant-numeric:tabular-nums" : ""));
    if (c.kind === "status") {
        const tone = t.tones[c.tone || toneOf(c.text)];
        const chip = el("span", `display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;` +
            `font-size:11px;font-weight:600;line-height:16px;background:${tone.bg};color:${tone.fg}` +
            (t.highContrast ? `;border:1px solid ${tone.fg}` : ""));
        chip.appendChild(el("span", `width:6px;height:6px;border-radius:50%;background:${tone.fg}`));
        chip.appendChild(document.createTextNode(c.text));
        td.appendChild(chip);
    }
    else if (c.kind === "progress") {
        const box = el("div", "display:flex;align-items:center;gap:8px");
        const track = el("div", `width:72px;height:6px;border-radius:3px;background:${t.highContrast ? t.surface : "#F4F4F5"};` +
            `overflow:hidden` + (t.highContrast ? `;border:1px solid ${t.ink}` : ""));
        track.appendChild(el("div", `width:${Math.max(0, Math.min(1, c.value)) * 100}%;height:100%;background:${t.accent}`));
        box.appendChild(track);
        box.appendChild(el("span", `font-size:11px;color:${t.muted};font-variant-numeric:tabular-nums`, c.text));
        td.appendChild(box);
    }
    else {
        td.textContent = c.text;
        if (c.kind === "text") {
            td.style.color = t.muted;
        }
    }
    return td;
}

// ---- trend.ts
/**
 * Header with the title, the headline number and a legend; dense columns on dashed gridlines. One column
 * is the focus (the latest period by default) in ink with its value above it; the rest are grey.
 */
function renderTrend(root, m, w, h, t, hook) {
    clear(root);
    const pad = 16;
    const box = el("div", `box-sizing:border-box;width:${w}px;height:${h}px;padding:${pad - 2}px ${pad}px ${pad - 4}px;` +
        `font-family:${t.font};color:${t.ink};display:flex;flex-direction:column`);
    const head = el("div", "display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex:none");
    const left = el("div", "display:flex;flex-direction:column;gap:2px;min-width:0");
    left.appendChild(el("div", "font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", m.title));
    if (m.total) {
        const line = el("div", "display:flex;align-items:baseline;gap:8px;margin-top:6px;white-space:nowrap");
        line.appendChild(el("span", "font-size:22px;font-weight:600;letter-spacing:-.01em;font-variant-numeric:tabular-nums", m.total));
        if (m.totalNote) {
            line.appendChild(el("span", `font-size:11px;color:${t.muted}`, m.totalNote));
        }
        left.appendChild(line);
    }
    head.appendChild(left);
    const legend = el("div", `display:flex;gap:14px;font-size:11px;color:${t.muted};white-space:nowrap;padding-top:2px`);
    const key = (colour, name) => {
        const k = el("span", "display:inline-flex;align-items:center;gap:6px");
        k.appendChild(el("span", `width:8px;height:8px;border-radius:2px;background:${colour}`));
        k.appendChild(document.createTextNode(name));
        legend.appendChild(k);
    };
    key(t.accent, m.seriesName);
    if (m.compare && m.compareName) {
        key(t.track, m.compareName);
    }
    head.appendChild(legend);
    box.appendChild(head);
    const plotH = h - (m.total ? 70 : 40) - pad;
    if (plotH < 60 || m.values.length === 0) {
        root.appendChild(box);
        return;
    }
    const plotW = w - pad * 2;
    const all = m.values.concat(m.compare || []).filter(v => isFinite(v));
    const ticks = niceTicks(Math.min(0, ...all), Math.max(...all, 0), 4);
    const lo = ticks[0], hi = ticks[ticks.length - 1];
    const axisW = Math.max(...ticks.map(v => m.tick(v).length)) * 6 + 8;
    const xLabelH = 18;
    const innerW = plotW - axisW, innerH = plotH - xLabelH - 18; // 18 px on top for the focus label
    const y = (v) => 18 + innerH * (1 - (v - lo) / (hi - lo || 1));
    const svg = sv("svg", { width: plotW, height: plotH, role: "img", "aria-label": m.title });
    svg.style.cssText = "display:block;margin-top:10px;overflow:visible";
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
        const draw = (v, x, colour, idx) => {
            const top = y(Math.max(v, 0)), base = y(Math.min(v, 0));
            const bar = sv("rect", { x: x.toFixed(1), y: top.toFixed(1), width: bw.toFixed(1),
                height: Math.max(1, base - top).toFixed(1), rx: Math.min(3, bw / 3), fill: colour });
            svg.appendChild(bar);
            if (hook && idx >= 0) {
                hook(bar, idx);
            }
        };
        if (pair) {
            draw(m.compare[i], cx - group / 2, t.track, -1);
            draw(m.values[i], cx + 1, i === focus || focus < 0 ? t.accent : tint(t.accent, 0.3), i);
        }
        else {
            draw(m.values[i], cx - bw / 2, i === focus ? t.accent : t.track, i);
        }
        if (i % every === (n - 1) % every || i === n - 1) {
            const lab = sv("text", { x: cx.toFixed(1), y: plotH - 4, "text-anchor": "middle", "font-size": 10,
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
    box.appendChild(svg);
    root.appendChild(box);
}
window.PBIArchitect = { TOKENS, brandTokens, tint, renderKpi, renderList, renderTrend, toneOf };
})();
