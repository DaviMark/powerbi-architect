"use strict";

/*
 * Architect List: rows to act on, with an avatar and the name (plus a grey second line), the status as a
 * soft chip, the values right-aligned and an optional progress bar. Drawing lives in ../../core/list.ts,
 * shared with the skill's preview.
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
import DataViewMetadataColumn = powerbi.DataViewMetadataColumn;
import PrimitiveValue = powerbi.PrimitiveValue;
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;

import { VisualFormattingSettingsModel } from "./settings";
import { renderList, ListModel, ListColumn, ListCell } from "../../core/list";
import { Tokens, brandTokens, highContrastTokens, el, clear } from "../../core/dom";

interface Slot { index: number; column: DataViewMetadataColumn }

export class Visual implements IVisual {
    private readonly host: IVisualHost;
    private readonly root: HTMLElement;
    private readonly selection: ISelectionManager;
    private readonly localization: ILocalizationManager;
    private readonly settingsService = new FormattingSettingsService();
    private settings: VisualFormattingSettingsModel = new VisualFormattingSettingsModel();
    private ids: ISelectionId[] = [];
    private tips: VisualTooltipDataItem[][] = [];
    private rows: HTMLElement[] = [];

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.root = options.element;
        this.root.classList.add("architect-root");
        this.selection = options.host.createSelectionManager();
        this.localization = options.host.createLocalizationManager();
        this.selection.registerOnSelectCallback(() => this.syncSelection());
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
                this.rows = [];
                renderList(this.root, model, options.viewport.width, options.viewport.height, this.tokens(),
                    (row, i) => this.bind(row, i));
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

    private text(v: PrimitiveValue, column: DataViewMetadataColumn): string {
        if (v === null || v === undefined) {
            return "";
        }
        return valueFormatter.create({ format: column.format, cultureSelector: this.host.locale }).format(v);
    }

    private toModel(dataView: DataView | undefined): ListModel | null {
        const table = dataView && dataView.table;
        if (!table || !table.rows || !table.rows.length) {
            return null;
        }
        const slots = (role: string): Slot[] => table.columns
            .map((column, index) => ({ index, column }))
            .filter(s => s.column.roles && s.column.roles[role]);
        const item = slots("item")[0];
        if (!item) {
            return null;
        }
        const detail = slots("detail")[0];
        const status = slots("status")[0];
        const values = slots("values");
        const progress = slots("progress")[0];
        const tooltips = slots("tooltips");

        const columns: ListColumn[] = [
            ...(status ? [{ title: status.column.displayName, kind: "status" as const }] : []),
            ...values.map(v => ({ title: v.column.displayName, kind: (v.column.type && v.column.type.numeric ? "number" : "text") as ListCell["kind"] })),
            ...(progress ? [{ title: progress.column.displayName, kind: "progress" as const }] : [])
        ];
        this.ids = table.rows.map((_r, i) => this.host.createSelectionIdBuilder().withTable(table, i).createSelectionId());
        this.tips = table.rows.map(r => [item, detail, status, ...values, progress, ...tooltips]
            .filter((s): s is Slot => !!s)
            .map(s => ({ displayName: s.column.displayName, value: this.text(r[s.index], s.column) })));

        return {
            title: this.settings.list.title.value || undefined,
            itemTitle: item.column.displayName,
            columns,
            avatars: this.settings.list.avatars.value,
            rows: table.rows.map(r => ({
                item: this.text(r[item.index], item.column),
                sub: detail ? this.text(r[detail.index], detail.column) : undefined,
                cells: [
                    ...(status ? [{ kind: "status" as const, text: this.text(r[status.index], status.column) }] : []),
                    ...values.map(v => ({ kind: (v.column.type && v.column.type.numeric ? "number" : "text") as "number" | "text",
                        text: this.text(r[v.index], v.column) })),
                    ...(progress ? [{ kind: "progress" as const, value: Number(r[progress.index]) || 0,
                        text: this.text(r[progress.index], progress.column) }] : [])
                ]
            }))
        };
    }

    private bind(row: HTMLElement, i: number): void {
        this.rows[i] = row;
        row.classList.add("architect-row");
        row.tabIndex = 0;
        row.setAttribute("role", "row");
        row.addEventListener("mousemove", (event: MouseEvent) => {
            this.host.tooltipService.show({ coordinates: [event.clientX, event.clientY], isTouchEvent: false,
                identities: [this.ids[i]], dataItems: this.tips[i] });
        });
        row.addEventListener("mouseleave", () => this.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));
        if (!this.host.hostCapabilities.allowInteractions) {
            return;
        }
        const pick = (multi: boolean) => this.selection.select(this.ids[i], multi).then(() => this.syncSelection());
        row.addEventListener("click", (event: MouseEvent) => pick(event.ctrlKey || event.metaKey));
        row.addEventListener("keydown", (event: KeyboardEvent) => {
            if (event.key === "Enter" || event.key === " ") {
                pick(event.ctrlKey || event.metaKey);
                event.preventDefault();
            }
        });
        row.addEventListener("contextmenu", (event: MouseEvent) => {
            this.selection.showContextMenu(this.ids[i], { x: event.clientX, y: event.clientY });
            event.preventDefault();
            event.stopPropagation();
        });
    }

    private syncSelection(): void {
        const chosen = this.selection.getSelectionIds() as ISelectionId[];
        this.rows.forEach((row, i) => {
            const on = !chosen.length || chosen.some(id => id.equals(this.ids[i]));
            row.style.opacity = on ? "1" : "0.4";
            row.setAttribute("aria-selected", String(chosen.length > 0 && on));
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
