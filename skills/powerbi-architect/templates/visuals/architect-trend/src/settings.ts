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

const FOCUS = [
    { value: "last", displayName: "Latest period" },
    { value: "max", displayName: "Highest value" },
    { value: "none", displayName: "None" }
];

class HeaderCard extends Card {
    title = new formattingSettings.TextInput({ name: "title", displayName: "Title", value: "", placeholder: "" });
    showHeadline = new formattingSettings.ToggleSwitch({ name: "showHeadline", displayName: "Headline number", value: true });
    name: string = "header";
    displayName: string = "Header";
    slices: Array<Slice> = [this.title, this.showHeadline];
}

class FocusCard extends Card {
    highlight = new formattingSettings.ItemDropdown({ name: "highlight", displayName: "Column in focus", items: FOCUS, value: FOCUS[0] });
    name: string = "focus";
    displayName: string = "Focus";
    slices: Array<Slice> = [this.highlight];
}

export class VisualFormattingSettingsModel extends Model {
    brand = new BrandCard();
    header = new HeaderCard();
    focus = new FocusCard();
    cards = [this.header, this.focus, this.brand];
}
