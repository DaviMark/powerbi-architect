# Modern visuals (experimental)

**Not yet opened in Power BI Desktop.** These files pass Microsoft's `visualContainer` schema and every
formatting property name and value exists in the official report theme schema, but the JSON that
Desktop writes for these visuals changes between versions and the query role names below come from
documentation, not from a saved report. Use them only after creating one of each in Desktop, saving and
comparing; then replace these files with what Desktop wrote and remove this notice.

| Folder | Visual | Why it is better | Unverified |
|---|---|---|---|
| `card-visual/` | `cardVisual`, the new card | value, label and reference labels (target, previous period) in one visual, so a KPI is one object instead of a card plus a variation line | query role `Data`; label `position` |
| `button-slicer/` | `advancedSlicerVisual`, the button slicer | segment buttons in the top bar instead of a dropdown when there are ≤ 4 options | query role `Values`; layout objects |
| `icon-button/` | `actionButton` with an icon and `PageNavigation` | navigation buttons with Tabler icons inside pages ("Ver clientes →") | icon image binding; `navigationSection` takes the target page id |

Until they are verified, the layout engine and the example use the classic `card` and the dropdown
`slicer`, which are known to work.
