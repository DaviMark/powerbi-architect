"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";

import Card = formattingSettings.SimpleCard;
import Slice = formattingSettings.Slice;
import Model = formattingSettings.Model;

/** The report's identity. The theme fills it (make_theme.py writes visualStyles for these visuals). */
export class BrandCard extends Card {
    accent = new formattingSettings.ColorPicker({ name: "accent", displayName: "Accent", value: { value: "#18181B" } });
    text = new formattingSettings.ColorPicker({ name: "text", displayName: "Text", value: { value: "#18181B" } });
    secondary = new formattingSettings.ColorPicker({ name: "secondary", displayName: "Secondary text", value: { value: "#71717A" } });
    context = new formattingSettings.ColorPicker({ name: "context", displayName: "Context", value: { value: "#D4D4D8" } });
    fontFamily = new formattingSettings.FontPicker({ name: "fontFamily", displayName: "Font", value: "Segoe UI" });
    name: string = "brand";
    displayName: string = "Identity";
    slices: Array<Slice> = [this.accent, this.text, this.secondary, this.context, this.fontFamily];
}

const SPARK = [
    { value: "auto", displayName: "Automatic" },
    { value: "bars", displayName: "Columns" },
    { value: "line", displayName: "Line" },
    { value: "none", displayName: "None" }
];

class KpiCard extends Card {
    higherIsBetter = new formattingSettings.ToggleSwitch({ name: "higherIsBetter", displayName: "Higher is better", value: true });
    spark = new formattingSettings.ItemDropdown({ name: "spark", displayName: "Trend", items: SPARK, value: SPARK[0] });
    note = new formattingSettings.TextInput({ name: "note", displayName: "Note (replaces “vs previous”)", value: "", placeholder: "" });
    name: string = "kpi";
    displayName: string = "KPI";
    slices: Array<Slice> = [this.higherIsBetter, this.spark, this.note];
}

export class VisualFormattingSettingsModel extends Model {
    brand = new BrandCard();
    kpi = new KpiCard();
    cards = [this.kpi, this.brand];
}
