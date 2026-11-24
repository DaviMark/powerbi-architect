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

class ListCard extends Card {
    title = new formattingSettings.TextInput({ name: "title", displayName: "Title", value: "", placeholder: "" });
    avatars = new formattingSettings.ToggleSwitch({ name: "avatars", displayName: "Avatars", value: true });
    name: string = "list";
    displayName: string = "List";
    slices: Array<Slice> = [this.title, this.avatars];
}

export class VisualFormattingSettingsModel extends Model {
    brand = new BrandCard();
    list = new ListCard();
    cards = [this.list, this.brand];
}
