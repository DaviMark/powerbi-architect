import { Tone, Tokens, el, clear, toneOf, initials, avatarColours } from "./dom";

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
    const th = (text: string, right: boolean) => el("th", `position:sticky;top:0;z-index:1;background:${t.surface};` +
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
                `align-items:center;justify-content:center;font-size:11px;font-weight:600;background:${bg};color:${fg}`,
                initials(r.item)));
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

function cell(c: ListCell, t: Tokens): HTMLElement {
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
    } else if (c.kind === "progress") {
        const box = el("div", "display:flex;align-items:center;gap:8px");
        const track = el("div", `width:72px;height:6px;border-radius:3px;background:${t.highContrast ? t.surface : "#F4F4F5"};` +
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
