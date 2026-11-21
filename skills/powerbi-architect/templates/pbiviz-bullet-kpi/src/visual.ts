"use strict";

/*
 * Bullet KPI — actual vs target per category.
 * Reference implementation of the powerbi-architect skill checklist:
 * rendering events · landing page · selection + multi-select · context menu · tooltips ·
 * keyboard focus · high contrast · formatting model · no network · no HTML injection · no dynamic code.
 */

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import { select, Selection } from "d3-selection";
import { scaleLinear } from "d3-scale";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import IVisualEventService = powerbi.extensibility.IVisualEventService;
import ISelectionManager = powerbi.extensibility.ISelectionManager;
import ISelectionId = powerbi.visuals.ISelectionId;
import DataView = powerbi.DataView;
import PrimitiveValue = powerbi.PrimitiveValue;
import ILocalizationManager = powerbi.extensibility.ILocalizationManager;
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;

import { VisualFormattingSettingsModel } from "./settings";

interface BulletRow {
    category: string;
    actual: number;
    highlight: number | null;
    target: number | null;
    extraTooltips: VisualTooltipDataItem[];
    actualText: string;
    targetText: string;
    selectionId: ISelectionId;
}

interface Palette {
    actual: string;
    target: string;
    track: string;
    text: string;
    isHighContrast: boolean;
}

const ROW_HEIGHT = 36;
const LABEL_WIDTH = 120;
const VALUE_WIDTH = 88;

function toNumber(value: PrimitiveValue): number | null {
    return typeof value === "number" && isFinite(value) ? value : null;
}

function formatNumber(value: number | null): string {
    return value === null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export class Visual implements IVisual {
    private readonly host: IVisualHost;
    private readonly events: IVisualEventService;
    private readonly selectionManager: ISelectionManager;
    private readonly localization: ILocalizationManager;
    private readonly formattingSettingsService: FormattingSettingsService;
    private readonly root: Selection<HTMLDivElement, unknown, null, undefined>;
    private readonly landing: Selection<HTMLDivElement, unknown, null, undefined>;
    private readonly svg: Selection<SVGSVGElement, unknown, null, undefined>;
    private formattingSettings: VisualFormattingSettingsModel;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.events = options.host.eventService;
        this.selectionManager = options.host.createSelectionManager();
        this.localization = options.host.createLocalizationManager();
        this.formattingSettingsService = new FormattingSettingsService();

        this.root = select(options.element).append("div").classed("bullet-root", true);
        this.landing = this.root.append("div").classed("bullet-landing", true);
        this.svg = this.root.append("svg").classed("bullet-svg", true).attr("role", "list");

        // Clicking empty space clears the selection
        this.svg.on("click", () => {
            if (!this.host.hostCapabilities.allowInteractions) {
                return;
            }
            this.selectionManager.clear();
            this.syncSelection();
        });
        // Right click on empty space opens the default context menu
        this.svg.on("contextmenu", (event: MouseEvent) => {
            this.selectionManager.showContextMenu({}, { x: event.clientX, y: event.clientY });
            event.preventDefault();
        });
        this.selectionManager.registerOnSelectCallback(() => this.syncSelection());
    }

    public update(options: VisualUpdateOptions): void {
        this.events.renderingStarted(options);
        try {
            const dataView: DataView | undefined = options.dataViews && options.dataViews[0];
            this.formattingSettings = this.formattingSettingsService
                .populateFormattingSettingsModel(VisualFormattingSettingsModel, dataView);

            const rows = this.toRows(dataView);
            if (rows.length === 0) {
                this.showLanding();
            } else {
                this.render(rows, options.viewport.width, options.viewport.height);
            }
            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.formattingSettingsService.buildFormattingModel(this.formattingSettings);
    }

    private toRows(dataView: DataView | undefined): BulletRow[] {
        const categorical = dataView && dataView.categorical;
        const category = categorical && categorical.categories && categorical.categories[0];
        const values = categorical && categorical.values;
        if (!category || !values) {
            return [];
        }
        const actualColumn = values.filter(v => v.source.roles && v.source.roles["actual"])[0];
        const targetColumn = values.filter(v => v.source.roles && v.source.roles["target"])[0];
        const tooltipColumns = values.filter(v => v.source.roles && v.source.roles["tooltips"]);
        if (!actualColumn) {
            return [];
        }
        return category.values.map((value, i) => {
            const actual = toNumber(actualColumn.values[i]) ?? 0;
            const target = targetColumn ? toNumber(targetColumn.values[i]) : null;
            const highlight = actualColumn.highlights ? toNumber(actualColumn.highlights[i]) ?? 0 : null;
            return {
                category: value === null || value === undefined ? "(blank)" : String(value),
                actual,
                highlight,
                target,
                extraTooltips: tooltipColumns.map(col => ({
                    displayName: col.source.displayName,
                    value: formatNumber(toNumber(col.values[i]))
                })),
                actualText: formatNumber(actual),
                targetText: formatNumber(target),
                selectionId: this.host.createSelectionIdBuilder().withCategory(category, i).createSelectionId()
            };
        });
    }

    private palette(): Palette {
        const cp = this.host.colorPalette;
        const bars = this.formattingSettings.bars;
        if (cp.isHighContrast) {
            return {
                actual: cp.foreground.value,
                target: cp.foregroundSelected.value,
                track: cp.background.value,
                text: cp.foreground.value,
                isHighContrast: true
            };
        }
        return {
            actual: bars.actualColor.value.value,
            target: bars.targetColor.value.value,
            track: bars.trackColor.value.value,
            text: this.formattingSettings.labels.color.value.value,
            isHighContrast: false
        };
    }

    private showLanding(): void {
        this.svg.style("display", "none");
        this.landing.style("display", "flex").selectAll("*").remove();
        this.landing.append("strong").text(this.localization.getDisplayName("Landing_Title"));
        this.landing.append("span").text(this.localization.getDisplayName("Landing_Hint"));
    }

    private render(rows: BulletRow[], width: number, height: number): void {
        this.landing.style("display", "none");
        this.svg.style("display", null).attr("width", width).attr("height", Math.max(height, rows.length * ROW_HEIGHT));

        const colors = this.palette();
        const labels = this.formattingSettings.labels;
        const showLabels = labels.show.value;
        const fontSize = `${labels.fontSize.value}px`;
        const barX = showLabels ? LABEL_WIDTH : 8;
        const barWidth = Math.max(10, width - barX - (showLabels ? VALUE_WIDTH : 8));
        const maxValue = Math.max(1, ...rows.map(r => Math.max(r.actual, r.target ?? 0)));
        const x = scaleLinear().domain([0, maxValue]).range([0, barWidth]);

        const groups = this.svg.selectAll<SVGGElement, BulletRow>("g.bullet-row")
            .data(rows, (d: BulletRow) => d.category)
            .join(enter => {
                const g = enter.append("g").classed("bullet-row", true)
                    .attr("role", "listitem").attr("tabindex", 0).attr("focusable", true);
                g.append("text").classed("bullet-label", true);
                g.append("rect").classed("bullet-track", true);
                g.append("rect").classed("bullet-actual", true);
                g.append("rect").classed("bullet-highlight", true);
                g.append("line").classed("bullet-target", true);
                g.append("text").classed("bullet-value", true);
                return g;
            });

        groups.attr("transform", (_d, i) => `translate(0, ${i * ROW_HEIGHT})`)
            .attr("aria-label", d => `${d.category}: ${d.actualText}${d.target === null ? "" : ` of ${d.targetText}`}`);

        groups.select<SVGTextElement>("text.bullet-label")
            .attr("x", 4).attr("y", ROW_HEIGHT / 2).attr("dy", "0.35em")
            .style("display", showLabels ? null : "none")
            .style("font-size", fontSize).style("fill", colors.text)
            .text(d => d.category);

        groups.select<SVGRectElement>("rect.bullet-track")
            .attr("x", barX).attr("y", 8).attr("width", barWidth).attr("height", ROW_HEIGHT - 16)
            .style("fill", colors.track)
            .style("stroke", colors.isHighContrast ? colors.text : null);

        groups.select<SVGRectElement>("rect.bullet-actual")
            .attr("x", barX).attr("y", 13).attr("height", ROW_HEIGHT - 26)
            .attr("width", d => Math.max(0, x(d.actual)))
            .style("fill", colors.actual)
            .style("fill-opacity", d => d.highlight === null ? 1 : 0.35);

        // Highlights: when another visual cross-highlights, show the highlighted share solid
        groups.select<SVGRectElement>("rect.bullet-highlight")
            .style("display", d => d.highlight === null ? "none" : null)
            .attr("x", barX).attr("y", 13).attr("height", ROW_HEIGHT - 26)
            .attr("width", d => Math.max(0, x(d.highlight ?? 0)))
            .style("fill", colors.actual);

        groups.select<SVGLineElement>("line.bullet-target")
            .style("display", d => d.target === null ? "none" : null)
            .attr("x1", d => barX + x(d.target ?? 0)).attr("x2", d => barX + x(d.target ?? 0))
            .attr("y1", 6).attr("y2", ROW_HEIGHT - 6)
            .style("stroke", colors.target).style("stroke-width", 2);

        groups.select<SVGTextElement>("text.bullet-value")
            .attr("x", width - 4).attr("y", ROW_HEIGHT / 2).attr("dy", "0.35em").attr("text-anchor", "end")
            .style("display", showLabels ? null : "none")
            .style("font-size", fontSize).style("fill", colors.text)
            .text(d => d.actualText);

        this.bindInteractions(groups);
        this.syncSelection();
    }

    private bindInteractions(groups: Selection<SVGGElement, BulletRow, SVGSVGElement, unknown>): void {
        const t = (key: string) => this.localization.getDisplayName(key);
        groups.on("mousemove", (event: MouseEvent, d: BulletRow) => {
            this.host.tooltipService.show({
                coordinates: [event.clientX, event.clientY],
                isTouchEvent: false,
                identities: [d.selectionId],
                dataItems: [
                    { displayName: t("Tip_Category"), value: d.category },
                    { displayName: t("Tip_Actual"), value: d.actualText },
                    { displayName: t("Tip_Target"), value: d.targetText },
                    ...d.extraTooltips
                ]
            });
        });
        groups.on("mouseleave", () => this.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));

        // Respect hosts where interactions are disabled (e.g. dashboards tiles, some embeds)
        if (!this.host.hostCapabilities.allowInteractions) {
            groups.on("click", null).on("keydown", null).on("contextmenu", null);
            return;
        }
        groups.on("click", (event: MouseEvent, d: BulletRow) => {
            this.selectionManager.select(d.selectionId, event.ctrlKey || event.metaKey)
                .then(() => this.syncSelection());
            event.stopPropagation();
        });
        groups.on("keydown", (event: KeyboardEvent, d: BulletRow) => {
            if (event.key === "Enter" || event.key === " ") {
                this.selectionManager.select(d.selectionId, event.ctrlKey || event.metaKey)
                    .then(() => this.syncSelection());
                event.preventDefault();
            }
        });
        groups.on("contextmenu", (event: MouseEvent, d: BulletRow) => {
            this.selectionManager.showContextMenu(d.selectionId, { x: event.clientX, y: event.clientY });
            event.preventDefault();
            event.stopPropagation();
        });
    }

    private syncSelection(): void {
        const ids = this.selectionManager.getSelectionIds() as ISelectionId[];
        const hasSelection = ids.length > 0;
        this.svg.selectAll<SVGGElement, BulletRow>("g.bullet-row")
            .style("opacity", d => !hasSelection || ids.some(id => id.equals(d.selectionId)) ? 1 : 0.4)
            .attr("aria-selected", d => hasSelection && ids.some(id => id.equals(d.selectionId)));
    }
}
