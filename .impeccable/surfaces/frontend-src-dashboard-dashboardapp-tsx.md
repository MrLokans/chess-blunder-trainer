---
version: 1
slug: "frontend-src-dashboard-dashboardapp-tsx"
primary_target: "frontend/src/dashboard/DashboardApp.tsx"
related_targets: ["templates/dashboard.html"]
---

# Dashboard — progress review

Mode: Operate. Club player (1000–2000) opens the dashboard between training sessions; the job is to answer "am I improving?" and leave with one thing to train.

## Direction contract

THESIS: One trend owns the page: a single bar chart of the chosen metric across 20-game blocks, with the first and the latest blocks drawn as reference lines and a one-line verdict above it. Refuses the category default of a KPI strip plus a wall of equal-weight cards.

OWN-WORLD: The incumbent DNA: warm paper ground, ink-black 3px rules, square corners, Jost caps labels, yellow primary only for the train action, green = better, red = worse. Charts are drawn in ink, not Chart.js defaults; one colour meaning across the page.

STORY: The player reads the verdict ("Worse than when you started: 1.9 → 2.9 blunders per game"), switches metric tabs to check the others, sees which metrics moved in the side column, and presses the one train action. Breakdowns below explain where blunders come from.

FIRST VIEWPORT: Desktop: filter row with a library status line on the right; left column (≈70%) metric tabs, verdict headline with before → now numbers, the block chart; right column the other metrics as before → now with sparklines and better/worse words, then the next-step block with the yellow train button. Below the fold: "Where it comes from" breakdowns with in-page links. Phone: tabs scroll, chart full width, side column stacks under it.

FORM: Trend spine, structure 3 of 7 on the ordered list. seed:1cebd4cfbb9a9857

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open
- The library table moves to Management; hour-of-day accuracy goes to the bottom.
