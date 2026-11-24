/*
 * Shared drawing core of the powerbi-architect visuals. Plain DOM, no Power BI API and no libraries, so the
 * same code draws inside Power BI (src/visual.ts of each visual) and in the skill's preview
 * (scripts/visuals.js, built by tools/build_visuals.py). Never innerHTML: text goes through textContent.
 */

export type Tone = "good" | "bad" | "warn" | "info" | "neutral";

export interface Tokens {
    font: string;
    accent: string;     // the focus: the current period, the progress, the trend's last point (brand colour)
    ink: string;        // values, titles
    muted: string;      // labels, axis text
    faint: string;      // gridlines, row separators
    track: string;      // bars that are context
    surface: string;    // header rows, hover
    tones: Record<Tone, { fg: string; bg: string }>;
    highContrast: boolean;
}

export const TOKENS: Tokens = {
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
export function highContrastTokens(foreground: string, background: string, selected: string): Tokens {
    const tone = { fg: foreground, bg: background };
    return {
        font: TOKENS.font, accent: foreground, ink: foreground, muted: foreground, faint: foreground, track: foreground,
        surface: background, tones: { good: tone, bad: tone, warn: tone, info: tone, neutral: { fg: selected, bg: background } },
        highContrast: true
    };
}

export function el<K extends keyof HTMLElementTagNameMap>(tag: K, css: string, text?: string): HTMLElementTagNameMap[K] {
    const node = document.createElement(tag);
    node.style.cssText = css;
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";

export function sv(tag: string, attrs: Record<string, string | number>): SVGElement {
    const node = document.createElementNS(SVG_NS, tag) as SVGElement;
    for (const k of Object.keys(attrs)) {
        node.setAttribute(k, String(attrs[k]));
    }
    return node;
}

export function clear(node: Element): void {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}

/** Round, readable axis ticks between 0 (or min) and max. */
export function niceTicks(lo: number, hi: number, count: number): number[] {
    if (!(hi > lo)) {
        return [lo];
    }
    const raw = (hi - lo) / Math.max(count - 1, 1);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => s >= raw) || raw;
    const out: number[] = [];
    for (let v = Math.floor(lo / step) * step; v <= hi + step * 0.001; v += step) {
        out.push(Math.round(v / step) * step);
    }
    if (out[out.length - 1] < hi) {
        out.push(out[out.length - 1] + step);
    }
    return out;
}

/** Status word to tone: the common Portuguese and English words of business lists. */
export function toneOf(status: string): Tone {
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
export function initials(name: string): string {
    const words = name.replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).filter(Boolean);
    return ((words[0] || "?")[0] + (words.length > 1 ? words[1][0] : (words[0] || "")[1] || "")).toUpperCase();
}

const AVATARS = [["#E0E7FF", "#3730A3"], ["#FCE7F3", "#9D174D"], ["#DCFCE7", "#166534"], ["#FEF3C7", "#92400E"],
    ["#E0F2FE", "#075985"], ["#F3E8FF", "#6B21A8"], ["#FFE4E6", "#9F1239"], ["#F4F4F5", "#3F3F46"]];

/** A stable soft colour per name (no randomness: the same name always gets the same colour). */
export function avatarColours(name: string): [string, string] {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
    }
    const pair = AVATARS[hash % AVATARS.length];
    return [pair[0], pair[1]];
}

/** The report's identity on top of the defaults: brand accent, text colours, font. Empty values keep the default. */
export function brandTokens(brand: Partial<Pick<Tokens, "font" | "accent" | "ink" | "muted" | "track">>): Tokens {
    const out: Tokens = { ...TOKENS, tones: TOKENS.tones };
    (Object.keys(brand) as Array<keyof typeof brand>).forEach(k => {
        const v = brand[k];
        if (v) {
            out[k] = k === "font" ? `'${v}', ${TOKENS.font}` : v;
        }
    });
    return out;
}

/** a mixed with white: share 0 keeps a, 1 is white. */
export function tint(hex: string, share: number): string {
    const h = hex.replace("#", "");
    if (!/^[0-9a-fA-F]{6}$/.test(h)) {
        return hex;
    }
    return "#" + [0, 2, 4].map(i => {
        const c = parseInt(h.slice(i, i + 2), 16);
        return Math.round(c + (255 - c) * share).toString(16).padStart(2, "0");
    }).join("");
}
