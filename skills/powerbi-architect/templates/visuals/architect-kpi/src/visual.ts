"use strict";

/*
 * Architect KPI: label, value, a pill with the variation, a note and a small trend.
 * With a Period the card shows the latest period and compares it with the one before (or with Reference,
 * when given), like Power BI's native KPI. Drawing lives in ../../core/kpi.ts, shared with the preview.
 */

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import { valueFormatter } from "powerbi-visuals-utils-formattingutils";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import ILocalizationManager = powerbi.extensibility.ILocalizationManager;
import DataView = powerbi.DataView;
import DataViewValueColumn = powerbi.DataViewValueColumn;
import PrimitiveValue = powerbi.PrimitiveValue;
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;

import { VisualFormattingSettingsModel } from "./settings";
import { renderKpi, KpiModel } from "../../core/kpi";
import { Tokens, Tone, brandTokens, highContrastTokens, el, clear } from "../../core/dom";

function num(v: PrimitiveValue | undefined): number | null {
    return typeof v === "number" && isFinite(v) ? v : null;
}

export class Visual implements IVisual {
    private readonly host: IVisualHost;
    private readonly root: HTMLElement;
    private readonly localization: ILocalizationManager;
    private readonly settingsService = new FormattingSettingsService();
    private settings: VisualFormattingSettingsModel = new VisualFormattingSettingsModel();
    private tips: VisualTooltipDataItem[] = [];

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.localization = options.host.createLocalizationManager();
        this.root = options.element;
        this.root.classList.add("architect-root");
        this.root.tabIndex = 0;
        this.root.addEventListener("contextmenu", (event: MouseEvent) => {
            if (this.host.hostCapabilities.allowInteractions) {
                this.host.createSelectionManager().showContextMenu({}, { x: event.clientX, y: event.clientY });
            }
            event.preventDefault();
        });
        this.root.addEventListener("mousemove", (event: MouseEvent) => {
            if (this.tips.length) {
                this.host.tooltipService.show({ coordinates: [event.clientX, event.clientY], isTouchEvent: false,
                    identities: [], dataItems: this.tips });
            }
        });
        this.root.addEventListener("mouseleave", () => this.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));
    }

    public update(options: VisualUpdateOptions): void {
        this.host.eventService.renderingStarted(options);
        try {
            const dataView: DataView | undefined = options.dataViews && options.dataViews[0];
            this.settings = this.settingsService.populateFormattingSettingsModel(VisualFormattingSettingsModel, dataView);
            const model = this.toModel(dataView);
            const { width, height } = options.viewport;
            if (!model) {
                this.landing();
            } else {
                renderKpi(this.root, model, width, height, this.tokens());
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

    private format(v: number | null, column: DataViewValueColumn | undefined, compact: boolean): string {
        if (v === null || !column) {
            return "—";
        }
        const f = valueFormatter.create({ format: column.source.format, value: compact ? Math.abs(v) : 0,
            cultureSelector: this.host.locale });
        return f.format(v);
    }

    private toModel(dataView: DataView | undefined): KpiModel | null {
        const cat = dataView && dataView.categorical;
        const values = cat && cat.values;
        const valueCol = values && values.filter(v => v.source.roles && v.source.roles["value"])[0];
        if (!valueCol || !valueCol.values.length) {
            return null;
        }
        const refCol = values ? values.filter(v => v.source.roles && v.source.roles["reference"])[0] : undefined;
        const tipCols = values ? values.filter(v => v.source.roles && v.source.roles["tooltips"]) : [];
        const noteCol = values ? values.filter(v => v.source.roles && v.source.roles["note"])[0] : undefined;
        const period = cat && cat.categories && cat.categories[0];
        // Another visual highlighting a slice: the card shows the highlighted part, like a native card.
        const series = valueCol.highlights || valueCol.values;
        const n = series.length;
        const last = n - 1;
        const current = num(series[last]);
        const periodText = (i: number): string => {
            if (!period) {
                return "";
            }
            const f = valueFormatter.create({ format: period.source.format, cultureSelector: this.host.locale });
            return f.format(period.values[i]);
        };

        let base: number | null = null;
        const noteText = noteCol ? noteCol.values[noteCol.values.length - 1] : null;
        let note = this.settings.kpi.note.value || (noteText === null || noteText === undefined ? "" : String(noteText));
        if (refCol) {
            base = num(refCol.values[last]);
            note = note || `${this.localization.getDisplayName("Note_Reference")} ${this.format(base, refCol, true)}`;
        } else if (period && n > 1) {
            base = num(series[last - 1]);
            note = note || `vs ${periodText(last - 1)}`;
        }

        let delta: string | undefined;
        let tone: Tone = "neutral";
        if (current !== null && base !== null && base !== 0) {
            const percent = /%/.test(valueCol.source.format || "");
            const diff = percent ? (current - base) * 100 : (current - base) / Math.abs(base) * 100;
            const shown = Math.abs(diff).toLocaleString(this.host.locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
            const arrow = diff > 0 ? "▲" : diff < 0 ? "▼" : "=";
            delta = `${arrow} ${shown}${percent ? " p.p." : "%"}`;
            if (diff !== 0) {
                tone = (diff > 0) === this.settings.kpi.higherIsBetter.value ? "good" : "bad";
            }
        }

        const label = valueCol.source.displayName;
        const valueText = this.format(current, valueCol, true);
        this.tips = [
            ...(period ? [{ displayName: period.source.displayName, value: periodText(last) }] : []),
            { displayName: label, value: this.format(current, valueCol, false) },
            ...(refCol ? [{ displayName: refCol.source.displayName, value: this.format(base, refCol, false) }] : []),
            ...tipCols.map(c => ({ displayName: c.source.displayName, value: this.format(num(c.values[last]), c, false) }))
        ];
        const spark = String(this.settings.kpi.spark.value.value) as KpiModel["spark"];
        return {
            label, value: valueText, delta, tone, note: delta ? note : note || undefined, spark,
            points: period ? series.map(v => num(v)).filter((v): v is number => v !== null) : undefined
        };
    }

    private landing(): void {
        this.tips = [];
        clear(this.root);
        const box = el("div", "height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;" +
            "gap:4px;font:12px 'Segoe UI',sans-serif;color:#71717A;text-align:center;padding:8px;box-sizing:border-box");
        box.appendChild(el("strong", "color:#18181B", this.localization.getDisplayName("Landing_Title")));
        box.appendChild(el("span", "", this.localization.getDisplayName("Landing_Hint")));
        this.root.appendChild(box);
    }
}
