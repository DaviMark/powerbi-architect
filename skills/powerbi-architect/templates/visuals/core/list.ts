import { Tone, Tokens, el, clear, toneOf, initials, avatarColours, shrinkToFit } from "./dom";

export type ListCell =
    | { kind: "text"; text: string }
    | { kind: "number"; text: string }
    | { kind: "status"; text: string; tone?: Tone }
    | { kind: "progress"; value: number; text: string };

export interface ListColumn { title: string; kind: ListCell["kind"] }

export interface ListRow {
    item: string;            // first column: avatar + name
    sub?: string;            // grey line under the name
    cells: ListCell[];
}

export interface ListModel {
    title?: string;          // drawn above the header row, like the other visuals of the skill
    itemTitle: string;
    columns: ListColumn[];
    rows: ListRow[];
    avatars?: boolean;
}

/** Called for each drawn row element, so Power BI can attach selection, tooltips and keyboard. */
export type RowHook = (row: HTMLElement, index: number) => void;

/**
 * A list for people to act on: an avatar and the name (with a grey second line), status as a soft chip,
 * progress as a thin bar, numbers right-aligned. Sticky header; the body scrolls when rows do not fit.
 */
export function renderList(root: HTMLElement, m: ListModel, w: number, h: number, t: Tokens, hook?: RowHook): void {
    // Measured after drawing: when the table is wider than the card (a wider fallback font, long headers),
    // draw it again tighter, then without the least important columns.
    for (let level = 0; level <= m.columns.length + 4; level++) {
        const wrap = drawList(root, m, w, h, t, hook, level);
        if (!wrap.isConnected || wrap.scrollWidth <= w + 1) {
            return;
        }
    }
}

function drawList(root: HTMLElement, m: ListModel, w: number, h: number, t: Tokens, hook: RowHook | undefined,
    level: number): HTMLElement {
    clear(root);
    const twoLines = m.rows.some(r => r.sub);
    const rowH = twoLines ? 52 : 36;
    const avatars = m.avatars !== false;
    const titleH = m.title ? 40 : 0;
    // Narrow cards: tighter cells and a shorter progress track, so every column stays in view.
    const width = (c: ListColumn) => c.kind === "progress" ? 140 : c.kind === "status" ? 110 : 96;
    const need = (avatars ? 220 : 160) + m.columns.reduce((s, c) => s + width(c), 0);
    const tight = need > w || level > 0;
    const pad = tight ? 8 : 12;
    const trackW = tight ? 48 : 72;
    // A phone (under 420 px): keep the columns that fit, the first number first, then status, then the rest.
    const order = m.columns.map((c, i) => i).sort((a, b) => rank(m.columns[a], a, m.columns) - rank(m.columns[b], b, m.columns));
    const keep = new Set<number>();
    // the header text is often the widest part of a column: uppercase 10 px with letter spacing, ~7 px a letter
    const fit = (c: ListColumn) => Math.max(c.kind === "progress" ? 108 : c.kind === "status" ? 96 : 64, c.title.length * 7) + pad * 2;
    let used = avatars ? 190 : 130;
    order.forEach(i => {
        const cw = fit(m.columns[i]);
        if (!keep.size || used + cw <= w || w >= 420) {
            keep.add(i);
            used += cw;
        }
    });
    order.slice().reverse().filter(i => keep.has(i)).slice(0, Math.max(0, level - 1))
        .forEach(i => {                                    // past the first redraw: drop the least important
            if (keep.size > 1) {
                keep.delete(i);
            }
        });
    const columns = m.columns.filter((_c, i) => keep.has(i));
    const frame = el("div", `box-sizing:border-box;width:${w}px;height:${h}px;display:flex;flex-direction:column;` +
        `font-family:${t.font};color:${t.ink}`);
    let titleEl: HTMLElement | undefined;
    if (m.title) {
        titleEl = frame.appendChild(el("div", `flex:none;height:${titleH}px;box-sizing:border-box;padding:14px 16px 0;font-size:13px;` +
            "font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis", m.title));
    }
    const wrap = el("div", `box-sizing:border-box;width:${w}px;height:${h - titleH}px;overflow:auto;font-size:12px`);
    const table = el("table", "width:100%;border-collapse:collapse;table-layout:auto");
    table.setAttribute("role", "grid");

    const head = el("thead", "");
    const hr = el("tr", "");
    const th = (text: string, right: boolean) => el("th", `position:sticky;top:0;z-index:1;background:${t.surface};` +
        `text-align:${right ? "right" : "left"};font-size:10px;font-weight:600;letter-spacing:.05em;` +
        `text-transform:uppercase;color:${t.muted};padding:8px ${pad}px;line-height:13px;border-bottom:1px solid ${t.faint};white-space:nowrap`, text);
    hr.appendChild(th(m.itemTitle, false));
    columns.forEach(c => hr.appendChild(th(c.title, c.kind === "number")));
    head.appendChild(hr);
    table.appendChild(head);

    const fitNames: HTMLElement[] = [];
    const body = el("tbody", "");
    m.rows.forEach((r, i) => {
        const tr = el("tr", `height:${rowH}px;border-bottom:1px solid ${t.faint}`);
        const first = el("td", `padding:0 ${pad}px;white-space:nowrap`);
        const box = el("div", "display:flex;align-items:center;gap:10px;min-width:0");
        if (avatars) {
            const [bg, fg] = t.highContrast ? [t.surface, t.ink] : avatarColours(r.item);
            box.appendChild(el("span", `flex:none;width:28px;height:28px;border-radius:50%;display:inline-flex;` +
                `align-items:center;justify-content:center;font-size:11px;font-weight:600;background:${bg};color:${fg}`,
                initials(r.item)));
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
    fitNames.forEach(n => shrinkToFit(n, 10));   // a long name loses a little size before it loses letters
    if (titleEl) {
        shrinkToFit(titleEl, 11);
    }
    return wrap;
}

/** Which columns a narrow list keeps first: the first number, then the status, then the others in order. */
function rank(c: ListColumn, i: number, all: ListColumn[]): number {
    const firstNumber = all.findIndex(x => x.kind === "number");
    return i === firstNumber ? -2 : c.kind === "status" ? -1 : i;
}

function cell(c: ListCell, t: Tokens, pad: number, trackW: number): HTMLElement {
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
    } else if (c.kind === "progress") {
        const box = el("div", "display:flex;align-items:center;gap:8px");
        const track = el("div", `width:${trackW}px;height:6px;border-radius:3px;background:${t.highContrast ? t.surface : "#F4F4F5"};` +
            `overflow:hidden` + (t.highContrast ? `;border:1px solid ${t.ink}` : ""));
        track.appendChild(el("div", `width:${Math.max(0, Math.min(1, c.value)) * 100}%;height:100%;background:${t.accent}`));
        box.appendChild(track);
        box.appendChild(el("span", `font-size:11px;color:${t.muted};font-variant-numeric:tabular-nums`, c.text));
        td.appendChild(box);
    } else {
        td.textContent = c.text;
        if (c.kind === "text") {
            td.style.color = t.muted;
        }
    }
    return td;
}
