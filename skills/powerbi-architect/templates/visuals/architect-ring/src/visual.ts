"use strict";

/*
 * Architect Ring: a ring with the number in its centre and a legend with value and share. Slices of a whole
 * (a category and a measure) or progress towards a target (a measure and a target, no category). Drawing
 * lives in ../../core/ring.ts, shared with the skill's preview.
 */

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import { valueFormatter } from "powerbi-visuals-utils-formattingutils";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import ISelectionManager = powerbi.extensibility.ISelectionManager;
import ISelectionId = powerbi.visuals.ISelectionId;
import ILocalizationManager = powerbi.extensibility.ILocalizationManager;
import DataView = powerbi.DataView;
import DataViewValueColumn = powerbi.DataViewValueColumn;
import PrimitiveValue = powerbi.PrimitiveValue;

import { VisualFormattingSettingsModel } from "./settings";
import { renderRing, RingModel } from "../../core/ring";
import { Tokens, brandTokens, highContrastTokens, el, clear } from "../../core/dom";

function num(v: PrimitiveValue | undefined): number {
    return typeof v === "number" && isFinite(v) ? v : 0;
}

export class Visual implements IVisual {
    private readonly host: IVisualHost;
    private readonly root: HTMLElement;
    private readonly selection: ISelectionManager;
    private readonly localization: ILocalizationManager;
    private readonly settingsService = new FormattingSettingsService();
    private settings: VisualFormattingSettingsModel = new VisualFormattingSettingsModel();
    private ids: ISelectionId[] = [];
    private nodes: Element[][] = [];

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.root = options.element;
        this.root.classList.add("architect-root");
        this.selection = options.host.createSelectionManager();
        this.localization = options.host.createLocalizationManager();
        this.selection.registerOnSelectCallback(() => this.syncSelection());
        this.root.addEventListener("click", () => {
            if (this.host.hostCapabilities.allowInteractions) {
                this.selection.clear().then(() => this.syncSelection());
            }
        });
        this.root.addEventListener("contextmenu", (event: MouseEvent) => {
            this.selection.showContextMenu({}, { x: event.clientX, y: event.clientY });
            event.preventDefault();
        });
    }

    public update(options: VisualUpdateOptions): void {
        this.host.eventService.renderingStarted(options);
        try {
            const dataView: DataView | undefined = options.dataViews && options.dataViews[0];
            this.settings = this.settingsService.populateFormattingSettingsModel(VisualFormattingSettingsModel, dataView);
            const model = this.toModel(dataView);
            if (!model) {
                this.landing();
            } else {
                this.nodes = [];
                renderRing(this.root, model, options.viewport.width, options.viewport.height, this.tokens(),
                    (node, i) => this.bind(node, i, model));
                this.syncSelection();
            }
            this.host.eventService.renderingFinished(options);
        } catch (error) {
            this.host.eventService.renderingFailed(options, String(error));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.settingsService.buildFormattingModel(this.settings);
    }

    private tokens(): Tokens {
        const cp = this.host.colorPalette;
        if (cp.isHighContrast) {
            return highContrastTokens(cp.foreground.value, cp.background.value, cp.foregroundSelected.value);
        }
        const b = this.settings.brand;
        return brandTokens({ accent: b.accent.value.value, ink: b.text.value.value, muted: b.secondary.value.value,
            track: b.context.value.value, font: b.fontFamily.value });
    }

    private formatter(column: DataViewValueColumn, compactFor: number) {
        return valueFormatter.create({ format: column.source.format, value: compactFor, cultureSelector: this.host.locale });
    }

    private percent(share: number): string {
        return share.toLocaleString(this.host.locale, { style: "percent", maximumFractionDigits: 0 });
    }

    private toModel(dataView: DataView | undefined): RingModel | null {
        const cat = dataView && dataView.categorical;
        const values = cat && cat.values;
        const valueCol = values && values.filter(v => v.source.roles && v.source.roles["value"])[0];
        if (!valueCol || !valueCol.values.length) {
            return null;
        }
        const header = this.settings.header;
        const title = header.title.value || valueCol.source.displayName;
        const category = cat && cat.categories && cat.categories[0];
        if (category) {
            const series = (valueCol.highlights || valueCol.values).map(num);
            const total = series.reduce((s, v) => s + Math.max(v, 0), 0);
            const compact = this.formatter(valueCol, Math.max(total, ...series));
            const catFormat = valueFormatter.create({ format: category.source.format, cultureSelector: this.host.locale });
            this.ids = category.values.map((_v, i) => this.host.createSelectionIdBuilder().withCategory(category, i).createSelectionId());
            const parts = category.values.map((v, i) => ({
                label: catFormat.format(v), value: series[i], text: compact.format(series[i]),
                share: total ? this.percent(Math.max(series[i], 0) / total) : undefined
            }));
            const first = String(this.settings.ring.center.value.value) === "first";
            return {
                title,
                center: first && total ? this.percent(Math.max(series[0], 0) / total) : compact.format(total),
                centerNote: header.centerNote.value || (first ? parts[0].label : undefined),
                parts
            };
        }
        const targetCol = values ? values.filter(v => v.source.roles && v.source.roles["target"])[0] : undefined;
        if (!targetCol) {
            return null;
        }
        this.ids = [];
        const value = num(valueCol.values[0]);
        const target = num(targetCol.values[0]);
        const compact = this.formatter(valueCol, Math.max(Math.abs(value), Math.abs(target)));
        const progress = target ? value / target : 0;
        const higher = this.settings.ring.higherIsBetter.value;
        const gap = target - value;
        const gapLabel = this.localization.getDisplayName(gap > 0 === higher ? "Legend_ToGo" : "Legend_Over");
        return {
            title,
            center: this.percent(progress),
            centerNote: header.centerNote.value || this.localization.getDisplayName("Center_OfTarget"),
            parts: [],
            goal: {
                progress,
                tone: (progress >= 1) === higher ? "good" : "neutral",
                legend: [
                    { label: valueCol.source.displayName, value, text: compact.format(value) },
                    { label: targetCol.source.displayName, value: target, text: compact.format(target) },
                    { label: gapLabel, value: Math.abs(gap), text: compact.format(Math.abs(gap)) }
                ]
            }
        };
    }

    private bind(node: Element, i: number, model: RingModel): void {
        (this.nodes[i] = this.nodes[i] || []).push(node);
        const part = model.parts[i];
        node.setAttribute("aria-label", `${part.label}: ${part.text}${part.share ? ` (${part.share})` : ""}`);
        if (node.tagName.toLowerCase() !== "path") {
            node.setAttribute("tabindex", "0");
            node.classList.add("architect-row");
        }
        (node as HTMLElement).style.cursor = "pointer";
        node.addEventListener("mousemove", (event: Event) => {
            const e = event as MouseEvent;
            this.host.tooltipService.show({ coordinates: [e.clientX, e.clientY], isTouchEvent: false,
                identities: [this.ids[i]], dataItems: [
                    { displayName: part.label, value: part.text },
                    ...(part.share ? [{ displayName: "%", value: part.share }] : [])
                ] });
        });
        node.addEventListener("mouseleave", () => this.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));
        if (!this.host.hostCapabilities.allowInteractions) {
            return;
        }
        const pick = (multi: boolean) => this.selection.select(this.ids[i], multi).then(() => this.syncSelection());
        node.addEventListener("click", (event: Event) => {
            const e = event as MouseEvent;
            pick(e.ctrlKey || e.metaKey);
            event.stopPropagation();
        });
        node.addEventListener("keydown", (event: Event) => {
            const e = event as KeyboardEvent;
            if (e.key === "Enter" || e.key === " ") {
                pick(e.ctrlKey || e.metaKey);
                event.preventDefault();
            }
        });
        node.addEventListener("contextmenu", (event: Event) => {
            const e = event as MouseEvent;
            this.selection.showContextMenu(this.ids[i], { x: e.clientX, y: e.clientY });
            event.preventDefault();
            event.stopPropagation();
        });
    }

    private syncSelection(): void {
        const chosen = this.selection.getSelectionIds() as ISelectionId[];
        this.nodes.forEach((group, i) => {
            const on = !chosen.length || chosen.some(id => id.equals(this.ids[i]));
            group.forEach(node => {
                (node as HTMLElement).style.opacity = on ? "1" : "0.4";
                node.setAttribute("aria-selected", String(chosen.length > 0 && on));
            });
        });
    }

    private landing(): void {
        clear(this.root);
        const box = el("div", "height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;" +
            "gap:4px;font:12px 'Segoe UI',sans-serif;color:#71717A;text-align:center;padding:8px;box-sizing:border-box");
        box.appendChild(el("strong", "color:#18181B", this.localization.getDisplayName("Landing_Title")));
        box.appendChild(el("span", "", this.localization.getDisplayName("Landing_Hint")));
        this.root.appendChild(box);
    }
}
