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
/**
 * Shrinks the font of a one-line text until it fits its box (measured, so it holds for any font the
 * viewer's machine falls back to). Needs the node in the document; does nothing otherwise.
 */
function shrinkToFit(node, min) {
    let size = parseFloat(node.style.fontSize) || 0;
    while (node.isConnected && size > min && node.scrollWidth > node.clientWidth + 0.5) {
        size -= 1;
        node.style.fontSize = `${size}px`;
    }
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
    const labelEl = el("div", `font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;` +
        `color:${t.muted};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:14px;` +
        `max-width:${w - padX * 2}px`, m.label);
    card.appendChild(labelEl);
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
    let noteEl;
    if (m.note) {
        noteEl = el("span", `font-size:11px;color:${t.muted};overflow:hidden;text-overflow:ellipsis;min-width:0;` +
            "display:inline-block", m.note);
        foot.appendChild(noteEl);
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
    shrinkToFit(valueEl, 14);
    shrinkToFit(labelEl, 9);
    if (noteEl) {
        shrinkToFit(noteEl, 9);
    }
}

// ---- list.ts
/**
 * A list for people to act on: an avatar and the name (with a grey second line), status as a soft chip,
 * progress as a thin bar, numbers right-aligned. Sticky header; the body scrolls when rows do not fit.
 */
function renderList(root, m, w, h, t, hook) {
    // Measured after drawing: when the table is wider than the card (a wider fallback font, long headers),
    // draw it again tighter, then without the least important columns.
    for (let level = 0; level <= m.columns.length + 4; level++) {
        const wrap = drawList(root, m, w, h, t, hook, level);
        if (!wrap.isConnected || wrap.scrollWidth <= w + 1) {
            return;
        }
    }
}
function drawList(root, m, w, h, t, hook, level) {
    clear(root);
    const twoLines = m.rows.some(r => r.sub);
    const rowH = twoLines ? 52 : 36;
    const avatars = m.avatars !== false;
    const titleH = m.title ? 40 : 0;
    // Narrow cards: tighter cells and a shorter progress track, so every column stays in view.
    const width = (c) => c.kind === "progress" ? 140 : c.kind === "status" ? 110 : 96;
    const need = (avatars ? 220 : 160) + m.columns.reduce((s, c) => s + width(c), 0);
    const tight = need > w || level > 0;
    const pad = tight ? 8 : 12;
    const trackW = tight ? 48 : 72;
    // A phone (under 420 px): keep the columns that fit, the first number first, then status, then the rest.
    const order = m.columns.map((c, i) => i).sort((a, b) => rank(m.columns[a], a, m.columns) - rank(m.columns[b], b, m.columns));
    const keep = new Set();
    // the header text is often the widest part of a column: uppercase 10 px with letter spacing, ~7 px a letter
    const fit = (c) => Math.max(c.kind === "progress" ? 108 : c.kind === "status" ? 96 : 64, c.title.length * 7) + pad * 2;
    let used = avatars ? 190 : 130;
    order.forEach(i => {
        const cw = fit(m.columns[i]);
        if (!keep.size || used + cw <= w || w >= 420) {
            keep.add(i);
            used += cw;
        }
    });
    order.slice().reverse().filter(i => keep.has(i)).slice(0, Math.max(0, level - 1))
        .forEach(i => {
        if (keep.size > 1) {
            keep.delete(i);
        }
    });
    const columns = m.columns.filter((_c, i) => keep.has(i));
    const frame = el("div", `box-sizing:border-box;width:${w}px;height:${h}px;display:flex;flex-direction:column;` +
        `font-family:${t.font};color:${t.ink}`);
    let titleEl;
    if (m.title) {
        titleEl = frame.appendChild(el("div", `flex:none;height:${titleH}px;box-sizing:border-box;padding:14px 16px 0;font-size:13px;` +
            "font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", m.title));
    }
    const wrap = el("div", `box-sizing:border-box;width:${w}px;height:${h - titleH}px;overflow:auto;font-size:12px`);
    const table = el("table", "width:100%;border-collapse:collapse;table-layout:auto");
    table.setAttribute("role", "grid");
    const head = el("thead", "");
    const hr = el("tr", "");
    const th = (text, right) => el("th", `position:sticky;top:0;z-index:1;background:${t.surface};` +
        `text-align:${right ? "right" : "left"};font-size:10px;font-weight:600;letter-spacing:.05em;` +
        `text-transform:uppercase;color:${t.muted};padding:8px ${pad}px;line-height:13px;border-bottom:1px solid ${t.faint};white-space:nowrap`, text);
    hr.appendChild(th(m.itemTitle, false));
    columns.forEach(c => hr.appendChild(th(c.title, c.kind === "number")));
    head.appendChild(hr);
    table.appendChild(head);
    const fitNames = [];
    const body = el("tbody", "");
    m.rows.forEach((r, i) => {
        const tr = el("tr", `height:${rowH}px;border-bottom:1px solid ${t.faint}`);
        const first = el("td", `padding:0 ${pad}px;white-space:nowrap`);
        const box = el("div", "display:flex;align-items:center;gap:10px;min-width:0");
        if (avatars) {
            const [bg, fg] = t.highContrast ? [t.surface, t.ink] : avatarColours(r.item);
            box.appendChild(el("span", `flex:none;width:28px;height:28px;border-radius:50%;display:inline-flex;` +
                `align-items:center;justify-content:center;font-size:11px;font-weight:600;background:${bg};color:${fg}`, initials(r.item)));
        }
        const names = el("div", `display:flex;flex-direction:column;min-width:0;line-height:16px;max-width:${Math.max(80, (w >= 420 ? Math.max(96, w * 0.45) : w - 140) - level * 24)}px`);
        // On a phone a long name takes two lines instead of losing letters.
        const nameEl = el("span", "font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis" + (w < 420
            ? ";white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical" : ""), r.item);
        names.appendChild(nameEl);
        fitNames.push(nameEl);
        if (r.sub) {
            names.appendChild(el("span", `font-size:11px;color:${t.muted};overflow:hidden;text-overflow:ellipsis`, r.sub));
        }
        box.appendChild(names);
        first.appendChild(box);
        tr.appendChild(first);
        r.cells.forEach((c, j) => {
            if (keep.has(j)) {
                tr.appendChild(cell(c, t, pad, trackW));
            }
        });
        body.appendChild(tr);
        if (hook) {
            hook(tr, i);
        }
    });
    table.appendChild(body);
    wrap.appendChild(table);
    frame.appendChild(wrap);
    root.appendChild(frame);
    fitNames.forEach(n => shrinkToFit(n, 10)); // a long name loses a little size before it loses letters
    if (titleEl) {
        shrinkToFit(titleEl, 11);
    }
    return wrap;
}
/** Which columns a narrow list keeps first: the first number, then the status, then the others in order. */
function rank(c, i, all) {
    const firstNumber = all.findIndex(x => x.kind === "number");
    return i === firstNumber ? -2 : c.kind === "status" ? -1 : i;
}
function cell(c, t, pad, trackW) {
    const td = el("td", `padding:0 ${pad}px;white-space:nowrap;text-align:${c.kind === "number" ? "right" : "left"};` +
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
        const track = el("div", `width:${trackW}px;height:6px;border-radius:3px;background:${t.highContrast ? t.surface : "#F4F4F5"};` +
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
    let note;
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
    if (w >= 420) { // narrow (a phone): the headline note already names the comparison
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
            const last = i === n - 1; // the last label ends at the plot's edge, never past it
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
    box.appendChild(svg);
    root.appendChild(box);
    if (note) {
        shrinkToFit(note, 8);
    }
}

// ---- ring.ts
const GAP = 0.012; // gap between slices, as a share of the circle
/** Shades of the accent: the largest slice is the accent itself, the rest fade towards the context grey. */
function ringColours(n, t) {
    if (t.highContrast) {
        return Array.from({ length: n }, (_v, i) => i === 0 ? t.accent : t.track);
    }
    const steps = [0, 0.38, 0.6, 0.76, 0.86, 0.92];
    return Array.from({ length: n }, (_v, i) => tint(t.accent, steps[Math.min(i, steps.length - 1)]));
}
function arc(cx, cy, r, from, to) {
    const a0 = (from - 0.25) * Math.PI * 2, a1 = (to - 0.25) * Math.PI * 2;
    const large = to - from > 0.5 ? 1 : 0;
    const p = (a) => `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
    return `M${p(a0)} A${r.toFixed(2)},${r.toFixed(2)} 0 ${large} 1 ${p(a1)}`;
}
/**
 * Card: title on top; the ring with the number in its centre; a legend of the slices with value and share
 * at the right (or under the ring when the card is narrow). `hook` binds events to each slice and row.
 */
function renderRing(root, m, w, h, t, hook) {
    clear(root);
    const pad = 16;
    const card = el("div", `position:relative;box-sizing:border-box;width:${w}px;height:${h}px;padding:${pad}px;` +
        `font-family:${t.font};color:${t.ink};overflow:hidden;display:flex;flex-direction:column;gap:12px`);
    card.setAttribute("role", "figure");
    card.setAttribute("aria-label", [m.title, m.center, m.centerNote].filter(Boolean).join(", "));
    card.appendChild(el("div", "font-size:14px;font-weight:600;line-height:20px;white-space:nowrap;overflow:hidden;" +
        "text-overflow:ellipsis", m.title));
    const bodyH = h - pad * 2 - 32;
    const side = w >= 300 && bodyH < (w - pad * 2) * 0.9; // a tall card stacks: ring on top, legend under it
    const legendRows = m.goal ? m.goal.legend : m.parts;
    const legendH = legendRows.length * 28;
    const narrow = w < 360; // a phone: a smaller ring, and the legend keeps the label and the value
    const size = Math.max(64, Math.floor(side ? Math.min(bodyH, (w - pad * 2) * (narrow ? 0.34 : 0.4))
        : Math.min(w - pad * 2, bodyH - legendH - 12, 240)));
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
    }
    else {
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
    holder.appendChild(svg);
    const mid = el("div", "position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;" +
        "justify-content:center;text-align:center;pointer-events:none");
    const big = size >= 140 ? 22 : size >= 104 ? 18 : 15;
    const centerEl = el("div", `font-size:${big}px;font-weight:600;letter-spacing:-.01em;line-height:1.15;` +
        `font-variant-numeric:tabular-nums;white-space:nowrap;max-width:${size - stroke * 2 - 8}px;overflow:hidden;` +
        "text-overflow:ellipsis", m.center);
    mid.appendChild(centerEl);
    if (m.centerNote) {
        mid.appendChild(el("div", `font-size:11px;color:${t.muted};line-height:14px;margin-top:2px;white-space:nowrap`, m.centerNote));
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
    shrinkToFit(centerEl, 9);
}
window.PBIArchitect = { TOKENS, brandTokens, tint, renderKpi, renderList, renderTrend, renderRing, ringColours, toneOf };
})();
