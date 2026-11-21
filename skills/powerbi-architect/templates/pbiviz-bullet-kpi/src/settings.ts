"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";

import FormattingSettingsCard = formattingSettings.SimpleCard;
import FormattingSettingsSlice = formattingSettings.Slice;
import FormattingSettingsModel = formattingSettings.Model;

/** "Bars" card in the format pane. Defaults are neutral; the report theme can override them. */
class BarsCard extends FormattingSettingsCard {
    actualColor = new formattingSettings.ColorPicker({
        name: "actualColor",
        displayName: "Actual",
        value: { value: "#1F3A5F" }
    });

    targetColor = new formattingSettings.ColorPicker({
        name: "targetColor",
        displayName: "Target",
        value: { value: "#1B1F24" }
    });

    trackColor = new formattingSettings.ColorPicker({
        name: "trackColor",
        displayName: "Track",
        value: { value: "#E3E6EA" }
    });

    name: string = "bars";
    displayName: string = "Bars";
    slices: Array<FormattingSettingsSlice> = [this.actualColor, this.targetColor, this.trackColor];
}

/** "Labels" card in the format pane. */
class LabelsCard extends FormattingSettingsCard {
    show = new formattingSettings.ToggleSwitch({
        name: "show",
        displayName: "Show",
        value: true
    });

    fontSize = new formattingSettings.NumUpDown({
        name: "fontSize",
        displayName: "Text size",
        value: 11
    });

    color = new formattingSettings.ColorPicker({
        name: "color",
        displayName: "Color",
        value: { value: "#5B6470" }
    });

    topLevelSlice = this.show;
    name: string = "labels";
    displayName: string = "Labels";
    slices: Array<FormattingSettingsSlice> = [this.fontSize, this.color];
}

export class VisualFormattingSettingsModel extends FormattingSettingsModel {
    bars = new BarsCard();
    labels = new LabelsCard();
    cards = [this.bars, this.labels];
}
