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

const CENTER = [
    { value: "total", displayName: "Total" },
    { value: "first", displayName: "Share of the first slice" }
];

class HeaderCard extends Card {
    title = new formattingSettings.TextInput({ name: "title", displayName: "Title", value: "", placeholder: "" });
    centerNote = new formattingSettings.TextInput({ name: "centerNote", displayName: "Text under the number", value: "", placeholder: "" });
    name: string = "header";
    displayName: string = "Header";
    slices: Array<Slice> = [this.title, this.centerNote];
}

class RingCard extends Card {
    center = new formattingSettings.ItemDropdown({ name: "center", displayName: "Number in the centre", items: CENTER, value: CENTER[0] });
    higherIsBetter = new formattingSettings.ToggleSwitch({ name: "higherIsBetter", displayName: "Higher is better (goal mode)", value: true });
    name: string = "ring";
    displayName: string = "Ring";
    slices: Array<Slice> = [this.center, this.higherIsBetter];
}

export class VisualFormattingSettingsModel extends Model {
    brand = new BrandCard();
    header = new HeaderCard();
    ring = new RingCard();
    cards = [this.header, this.ring, this.brand];
}
