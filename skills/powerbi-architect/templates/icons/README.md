# Icons

16 px navigation icons for the sidebar (64×64 PNG, grey `#666666`, 1.75 stroke), rendered from
[Tabler Icons](https://tabler.io/icons) (MIT licence, see `LICENSE-tabler`), the icon family Twenty uses.
PNG is used because every Power BI surface renders it.

| File | Use for |
|---|---|
| `layout-dashboard.png` | overview / home page |
| `chart-bar.png` | diagnostic and analysis pages |
| `list-details.png` | operational lists and tables |
| `user.png` | entity detail (customer, product, employee) |
| `file-description.png` | documentation page |
| `arrow-left.png` | back arrow on drill-through pages |

Name the icon in the layout spec (`"icon": "chart-bar"`); `scripts/pbir_layout.py` places it next to the
page's navigator item and registers it in `report.json`. Need another icon? Take the outline SVG from
Tabler, render it the same way (64 px, `#666666`) and keep the MIT notice.
