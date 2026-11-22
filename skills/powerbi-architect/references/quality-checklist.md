# Quality checklist — run before saying "done"

Report each item as PASS / WARN (with reason) / FAIL. Severity: **B** blocker · **I** important · **S** suggestion.

## Model
- [B] Star schema; each fact has a stated grain; dimensions conformed
- [I] Tables named `ft_<subject>` (facts) and `dm_<entity>` (dimensions); helpers prefixed `_`
- [B] Only used columns imported (audit done; cut list documented)
- [B] One Power Query step per source table; no hard‑coded servers (parameters)
- [B] Auto date/time off; one marked date table; relationships dimension → fact, single direction
- [I] No calculated columns in facts; no bidirectional/M:M without ADR
- [I] Keys and raw numeric columns hidden; `summarizeBy: none`; sort‑by columns set
- [I] Table descriptions with grain, source file and connection

## DAX
- [B] Every measure: description (business sentence), format string, display folder
- [B] Control totals reconcile with a trusted source (Gate 2)
- [I] Base → derived layering; `DIVIDE`; variables; column predicates
- [S] Calculation groups / field parameters where they remove duplication

## Report
- [B] Every page answers one stated question; Documentation page present
- [B] Numbers formatted consistently; titles in business language
- [I] Headline (conclusion) + ≤ 4 KPIs + ≤ 3 explanation visuals + detail/drill
- [I] App shell as in report-design §0 (sidebar 220, white panel, 56 px top bar) on multi-page reports
- [I] 4‑px grid alignment, rows of 88 · 248 · 248, one gutter (16), one radius (8); nothing outside the page
- [I] One font family (Segoe UI without a brand font); sizes only from the scale (9 · 10 · 12 · 20)
- [I] ≤ 2 slicers on the page, dropdown 176×40 in the top bar; the rest in the filter pane
- [I] Theme applied; one accent colour; meaningful color only
- [I] Alt text, tab order, contrast, no color‑only encoding
- [S] Tooltips add context; empty states; mobile layout if used on phones

## Custom visuals (if any)
- [B] ADR proving native/AppSource options don't fit
- [B] `privileges: []`, no network/eval/innerHTML, lint + package clean
- [I] Landing page, keyboard, high contrast, tooltips, context menu, highlights, localization

## Project
- [B] No data or secrets in the repo; `.gitignore` covers pbix/abf/localSettings
- [B] Project validator clean (`pbw validar` or `scripts/audit_pbip.py`) and the `.pbip` opens in Desktop
- [I] README sections complete; CHANGELOG + version updated; design docs match implementation
- [I] `.pbit` exported to `3-entrega/` (human)
