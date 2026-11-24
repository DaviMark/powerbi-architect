"use strict";

/*
 * Architect Trend: a header (title, the latest value and its variation, legend) over dense columns, with
 * one column in focus. Drawing lives in ../../core/trend.ts, shared with the skill's preview.
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
import { renderTrend, TrendModel } from "../../core/trend";
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
    private bars: SVGElement[] = [];

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
                this.bars = [];
                renderTrend(this.root, model, options.viewport.width, options.viewport.height, this.tokens(),
                    (bar, i) => this.bind(bar, i, model));
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

    private toModel(dataView: DataView | undefined): TrendModel | null {
        const cat = dataView && dataView.categorical;
        const period = cat && cat.categories && cat.categories[0];
        const values = cat && cat.values;
        const valueCol = values && values.filter(v => v.source.roles && v.source.roles["value"])[0];
        if (!period || !valueCol || !valueCol.values.length) {
            return null;
        }
        const compareCol = values ? values.filter(v => v.source.roles && v.source.roles["compare"])[0] : undefined;
        const series = (valueCol.highlights || valueCol.values).map(num);
        const compare = compareCol ? compareCol.values.map(num) : undefined;
        const peak = Math.max(...series.map(Math.abs), ...(compare || []).map(Math.abs));
        const full = this.formatter(valueCol, 0);
        const compact = this.formatter(valueCol, peak);
        const periodFormat = valueFormatter.create({ format: period.source.format, cultureSelector: this.host.locale });
        const labels = period.values.map(v => periodFormat.format(v));
        this.ids = period.values.map((_v, i) => this.host.createSelectionIdBuilder().withCategory(period, i).createSelectionId());

        const last = series.length - 1;
        let totalNote: string | undefined;
        const base = compare ? compare[last] : last > 0 ? series[last - 1] : 0;
        if (base) {
            const diff = (series[last] - base) / Math.abs(base) * 100;
            const shown = Math.abs(diff).toLocaleString(this.host.locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
            const against = compare ? compareCol?.source.displayName : labels[last - 1];
            totalNote = `${labels[last]} · ${diff > 0 ? "▲" : diff < 0 ? "▼" : "="} ${shown}% vs ${against}`;
        }
        return {
            title: this.settings.header.title.value || valueCol.source.displayName,
            total: this.settings.header.showHeadline.value ? compact.format(series[last]) : undefined,
            totalNote: this.settings.header.showHeadline.value ? totalNote : undefined,
            labels, values: series, valueTexts: series.map(v => compact.format(v)),
            seriesName: valueCol.source.displayName,
            compare, compareTexts: compare ? compare.map(v => full.format(v)) : undefined,
            compareName: compareCol ? compareCol.source.displayName : undefined,
            highlight: String(this.settings.focus.highlight.value.value) as TrendModel["highlight"],
            tick: (v: number) => compact.format(v)
        };
    }

    private bind(bar: SVGElement, i: number, model: TrendModel): void {
        this.bars[i] = bar;
        bar.setAttribute("tabindex", "0");
        bar.setAttribute("role", "listitem");
        bar.setAttribute("aria-label", `${model.labels[i]}: ${model.valueTexts[i]}`);
        bar.style.cursor = "pointer";
        bar.addEventListener("mousemove", (event: MouseEvent) => {
            this.host.tooltipService.show({ coordinates: [event.clientX, event.clientY], isTouchEvent: false,
                identities: [this.ids[i]], dataItems: [
                    { displayName: model.seriesName, value: model.valueTexts[i], header: model.labels[i] },
                    ...(model.compare && model.compareName && model.compareTexts
                        ? [{ displayName: model.compareName, value: model.compareTexts[i] }] : [])
                ] });
        });
        bar.addEventListener("mouseleave", () => this.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));
        if (!this.host.hostCapabilities.allowInteractions) {
            return;
        }
        const pick = (multi: boolean) => this.selection.select(this.ids[i], multi).then(() => this.syncSelection());
        bar.addEventListener("click", (event: MouseEvent) => {
            pick(event.ctrlKey || event.metaKey);
            event.stopPropagation();
        });
        bar.addEventListener("keydown", (event: KeyboardEvent) => {
            if (event.key === "Enter" || event.key === " ") {
                pick(event.ctrlKey || event.metaKey);
                event.preventDefault();
            }
        });
        bar.addEventListener("contextmenu", (event: MouseEvent) => {
            this.selection.showContextMenu(this.ids[i], { x: event.clientX, y: event.clientY });
            event.preventDefault();
            event.stopPropagation();
        });
    }

    private syncSelection(): void {
        const chosen = this.selection.getSelectionIds() as ISelectionId[];
        this.bars.forEach((bar, i) => {
            const on = !chosen.length || chosen.some(id => id.equals(this.ids[i]));
            bar.style.opacity = on ? "1" : "0.4";
            bar.setAttribute("aria-selected", String(chosen.length > 0 && on));
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
