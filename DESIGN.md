---
name: Blunder Tutor
description: A chess trainer that drills one player's own blunders, set in ink on warm paper.
colors:
  ink: "#1A1A1A"
  paper: "#F5F2EB"
  paper-sunken: "#E8E4DB"
  graphite: "#3A3A3A"
  pencil: "#706E68"
  rule-light: "#B8B4AB"
  train-yellow: "#F2C12E"
  train-yellow-hover: "#E0B020"
  better-green: "#247A33"
  worse-red: "#D42828"
  link-blue: "#1A3A8F"
  dashboard-positive: "#176B2B"
  dashboard-negative: "#B42318"
  dashboard-info: "#164E9A"
  dashboard-caution: "#7A5200"
  ink-ramp-1: "#BFB9AC"
  ink-ramp-2: "#8F8A7E"
  ink-ramp-3: "#57534A"
  night-ground: "#16150F"
  night-raised: "#26241B"
  night-ink: "#F5F2EB"
typography:
  display:
    fontFamily: "Jost, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "normal"
  numeral:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum"
  headline:
    fontFamily: "Jost, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.25
  title:
    fontFamily: "Jost, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  body-small:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Jost, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "2px"
  label-micro:
    fontFamily: "Jost, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "1px"
rounded:
  none: "0"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.train-yellow}"
    textColor: "{colors.ink}"
    typography: "{typography.label-micro}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.train-yellow-hover}"
    textColor: "{colors.ink}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label-micro}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-danger:
    backgroundColor: "{colors.worse-red}"
    textColor: "{colors.paper}"
    typography: "{typography.label-micro}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.pencil}"
    typography: "{typography.body-small}"
    rounded: "{rounded.none}"
  tab:
    backgroundColor: "transparent"
    textColor: "{colors.pencil}"
    typography: "{typography.label-micro}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  tab-active:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.graphite}"
    typography: "{typography.label}"
    padding: "8px 16px"
  nav-link-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  text-input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "8px"
  badge:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label-micro}"
    rounded: "{rounded.none}"
    padding: "2px 8px"
  chart-container:
    backgroundColor: "transparent"
    rounded: "{rounded.none}"
    padding: "16px 0 0"
---

# Design System: Blunder Tutor

## Overview

**Creative North Star: "The Annotated Scoresheet"**

Blunder Tutor reads like a chess player's own scoresheet after a bad game: warm paper, black ink, heavy rules between sections, and a few marks in colour where something went right or wrong. The ground is a warm off-white in light mode and a warm near-black in dark mode; everything structural is drawn in ink (or its dark-mode inversion) with flat fills and square corners. There are no drop shadows, no gradients, no rounded cards. Depth comes from rules and inversion, never from lift.

Density is that of a working document, not a marketing page. One element owns each view: on the dashboard a single trend chart with a sentence-case verdict above it; in the trainer the board, kept whole, with the result laid beside it as two mini boards. Everything else is ranked under that owner with ink weight and opacity rather than with extra colour. Colour is reserved for meaning: green says better or best, red says worse or your miss, yellow marks the one action you should take next.

The system descends from a Bauhaus token set (the source still names it that), and the primary triad survives in the tokens. The newest surfaces have narrowed it: blue has retreated to links, focus and informational states, and charts are ink.

**Key Characteristics:**
- Warm paper ground, ink text and ink charts; dark mode is the same world inverted, not a new palette.
- 3px ink rules divide sections and frame boards; 2px ink strokes outline controls.
- Square corners everywhere (radius 0).
- Jost uppercase for small labels, tabs, buttons and nav; Jost sentence case for display headings and verdicts; DM Sans for body and numbers.
- Colour carries meaning only: green better, red worse, yellow the single primary action.
- Charts are hand-drawn in HTML/SVG with ink bars, reference lines and a screen-reader table; no chart library.

## Colors

A warm two-tone paper-and-ink palette with three semantic marks; volume is shown in ink tints, never in hue.

### Primary
- **Train Yellow** (train-yellow): the fill of the one primary action on a view: "Train" on the dashboard, "Next" in the trainer. Text on it is ink. Hover deepens to train-yellow-hover.

### Secondary
- **Better Green** (better-green): improvement and the best move. Best-move mini board ring, best-move text, "Improving" words. On the dashboard the darker, contrast-checked dashboard-positive is used for text.
- **Worse Red** (worse-red): regression and the player's miss. "Worsening" words, the latest-block reference line when worse, the "your move" text, destructive buttons. Dashboard text uses dashboard-negative. The brand mark square is also this red.

### Tertiary
- **Link Blue** (link-blue): the default accent token. Focus rings, input focus border, info states, links, the "analysis running" status (dashboard-info), and board move highlights. It is not used for chart data or emphasis.

### Neutral
- **Ink** (ink): text, rules, borders, chart bars, active nav fill, the top of the volume ramp.
- **Paper** (paper): page ground and raised surfaces (the same value; surfaces are not tonally stacked in light mode).
- **Sunken Paper** (paper-sunken): table row hover, code chips, sunken wells.
- **Graphite** (graphite): secondary text, nav links at rest, section titles.
- **Pencil** (pencil): muted text, captions, axis labels, inactive tabs.
- **Light Rule** (rule-light): the default 1px border and disabled text.
- **Ink Ramp** (ink-ramp-1 to ink-ramp-3, then ink): volume steps for the activity heatmap.
- **Night Ground / Night Raised / Night Ink** (night-ground, night-raised, night-ink): dark-mode surface, raised surface and text. Dark-mode semantic hues are lightened (see the sidecar) so they hold contrast on the night ground.

### Named Rules
**The One Meaning Rule.** Green only ever means better or best; red only ever means worse or your miss; yellow only ever means the action to take. A colour that means something on one chart may not mean something else on the next. Deliberate exception, kept by the owner: chess convention keeps yellow for inaccuracies and mistakes in game review (move-list dots, eval-graph markers), for the middlegame phase colour (a user-themable palette) and for the game-review result badge.

**The Ink For Volume Rule.** Counts, shares and frequencies are drawn in ink at stepped opacity or along the ink ramp (heatmap levels, ranked bars, games-played strips). Hue is never used to encode volume.

**The Single Highlight Rule.** Within one breakdown, exactly one row may be drawn at full ink (the leader); the rest sit at about 35% ink, and rows resting on too little data (fewer than 10 games) drop to about 15% and muted text and are never the highlight.

**The One Yellow Rule.** A view carries one yellow button. Secondary actions are ink-outlined.

## Typography

**Display Font:** Jost (with sans-serif)
**Body Font:** DM Sans (with sans-serif)

**Character:** Jost is the geometric, poster-like voice of structure: labels, tabs, buttons and headings. DM Sans is the reading voice for sentences and the figures that carry the data. Both are self-hosted woff2.

### Hierarchy
- **Display** (Jost 600, 1.75rem, line-height 1.15, sentence case, balanced wrap): dashboard section headings ("Where your blunders come from") and the trend verdict. Drops to 1.375rem on narrow screens.
- **Numeral** (DM Sans 700, 2.75rem, line-height 1, tabular figures): the before and after values beside the verdict, big conversion rates. 2rem on phones.
- **Headline** (Jost 700, 1.25rem, line-height 1.2 to 1.25): the trainer result headline ("You missed Rd3+"), the coaching headline.
- **Title** (Jost 700, 1.0625rem): card and modal titles, side-column metric values.
- **Body** (DM Sans 400, 0.875rem, line-height 1.5): all running text. Body-small (0.8125rem) for explanations, captions, scope notes and chart notes.
- **Label** (Jost 700, 0.8125rem, letter-spacing 2px, uppercase): section and container titles ("Blunders by game phase", side-column titles, trainer panel section titles).
- **Label Micro** (Jost 700 or 400, 0.6875rem, letter-spacing 1 to 2px, uppercase): buttons, tabs, badges, form labels, table headers, mini-board captions.

### Named Rules
**The Two Voices Rule.** Uppercase Jost is for naming things (labels, controls, containers). Statements meant to be read as sentences (verdicts, section headings, result headlines) are sentence case. Never set a sentence in caps.

**The Tabular Figures Rule.** Every number that can be compared with another number uses tabular figures: chart axes, trend values, side-column values, ranked-bar values, library status.

## Layout

A 4px-based power-of-two spacing scale (4, 8, 16, 24, 32, 48) carries all rhythm; container widths cap at 1400px with 24px side padding.

The dashboard opens on a two-column trend spine: the chart column takes the remaining width and the side column is clamped to 280 to 360px, with a 48px gap, closed by a 3px ink rule. Breakdowns below sit in a two-column grid with 48px gaps, each container topped by its own 3px rule; wide breakdowns span both columns but cap their bars at 760px so lengths stay comparable. The trainer is a board column with 48px padding beside a side panel clamped to 380 to 480px, separated by a 3px vertical rule; panel sections are stacked and divided by 3px rules.

Responsive behaviour collapses rather than rearranges: at 1080px both the trend spine and the trainer go single-column (the trainer panel's left rule becomes a top rule and the board padding drops to 24px); at 760px the breakdown grid goes single-column; at 480px ranked-bar rows stack label over bar and chart gutters narrow. Tab bars scroll horizontally on phones rather than wrapping. The board's size is capped by viewport height so the action row stays above the fold.

**The Owner Rule.** Each view has one element that owns the first viewport (the trend, the board). Everything else is visibly subordinate to it.

## Elevation & Depth

The system is flat. Shadow tokens (shadow-sm through shadow-lg) are deliberately set to none. Depth is expressed by rules (3px ink section dividers, 2px control outlines, 1px light rules between rows), by inversion (the active nav item and hovered outline buttons flip to ink-on-paper reversed), and by the modal backdrop scrim. Box-shadow appears only as a stroke technique: 3px outer frames on mini boards (ink, or green for the best move), inset square highlight rings on the chessboard, and the two-ring focus indicator.

### Named Rules
**The Flat Paper Rule.** Nothing floats. Surfaces do not cast shadows; if something needs separating, draw a rule.

## Shapes

Every corner is square (radius tokens are all 0). Forms are rectangles bounded by ink strokes of three weights: 3px for structure (section dividers, board frame, modal and drawer edges, reference lines), 2px for controls (buttons, inputs, tabs, filter bar, badges), 1px for quiet subdivision (table rows, chart ticks). The only circles are functional: spinners and colour swatches. The brand mark is a solid red square.

## Components

### Buttons
Blunt, uppercase and outlined; they read as stamped labels.
- **Shape:** square corners, 2px border.
- **Primary:** train-yellow fill with ink text, Jost micro label caps. One per view. Full-width in the dashboard's coaching block.
- **Secondary:** transparent with a 2px ink outline; on hover the button inverts to an ink fill with paper text.
- **Danger:** worse-red fill, used only for destructive confirmation.
- **Ghost:** no border, DM Sans small sentence case in muted text; for low-stakes inline actions.
- **Sizes:** small (4px 8px), medium (8px 16px), large (16px 24px, 0.8125rem). Disabled at 50% opacity.
- **Focus:** a 2px blue outline offset 2px (two-ring paper-then-blue shadow on tabs).

### Tabs
Folder tabs on a 2px ink baseline. Inactive tabs are muted caps with a transparent border; the active tab gains a 2px ink outline (no bottom edge) that sits over the baseline, and ink text. Arrow keys move focus between tabs. On phones the bar scrolls horizontally.

### Containers
There are no cards in the shadowed sense. Breakdown containers are open: a 3px ink top rule, 16px top padding, a caps label title, a muted one-line scope note, then content. A bordered card-surface variant (2px ink outline, square) exists for settings-style lists.

### Inputs / Fields
2px ink outline on paper, square, DM Sans body text; the border turns link-blue on focus and worse-red when invalid. Labels above are Jost micro caps in muted text. Checkboxes and toggles use ink as the accent.

### Navigation
Top bar with the red-square brand mark and the wordmark in Jost caps on the left; Jost caps links on the right in graphite. Hover draws a 2px ink underline; the active page is a solid ink block with paper text and a 2px inset bottom stroke.

### Drawer (Modal, side placement)
A full-height right drawer, 440px wide, edged by a single 3px ink rule on its open side, over the scrim. On phones it becomes a bottom sheet up to 85% of the viewport with a 3px top rule. Centred modals are 3px-framed, unshadowed.

### Ink Charts (signature)
The dashboard's charts are drawn in HTML and SVG in the page's own grammar.
- **Block trend:** ink bars per 20-game block on a 2px ink baseline with 1px light tick lines and muted tabular axis labels in a fixed gutter. Middle blocks sit at about 22% ink; the first compared block at 45%; the latest blocks at full ink. Two 3px reference lines mark the "then" (dashed, ink) and "now" (solid, green if better, red if worse, ink if flat) values, each with a bold tabular tag on a paper chip.
- **Accuracy line:** a 2px ink polyline with square 8px paper-filled ink-outlined markers, over a quiet ink strip of games played at 25%.
- **Ranked bars:** a table whose bars are 14px ink rules, value right-aligned in bold tabular figures with a muted detail line; the Single Highlight Rule applies.
- **Sparklines:** small ink lines in the side column, paired with a coloured better or worse word.
- **Heatmap:** square cells on the five-step ink ramp, with an inverted ink tooltip.
- Every chart carries an sr-only table with the same data. Bar growth animates (0.4s, expo-out) and stops under reduced motion.

### Result Twins (signature)
In the trainer result, two mini boards sit side by side under the headline: the position after your move (ink frame, move text in red) and after the best move (green frame, move text in green), each captioned with a micro caps label, the move and its eval. When only one future exists it shows alone at up to 220px. The main board stays unobstructed beside them.

### Library Status
A right-aligned, muted, tabular line of counts separated by ink middle dots; the analysis state goes blue while running and red on failure.

## Do's and Don'ts

### Do:
- **Do** separate sections with a 3px ink rule and outline controls with 2px ink.
- **Do** keep every corner square.
- **Do** draw new charts in ink with reference lines, a baseline, tabular axis labels and an sr-only data table, using no third-party chart library.
- **Do** give each breakdown exactly one full-ink highlight and mute rows with fewer than 10 games behind it.
- **Do** use one yellow primary button per view and ink outlines for everything else.
- **Do** set statements in sentence-case Jost and names of things in uppercase Jost labels.
- **Do** route every colour through the light-dark() tokens so dark mode and user themes follow.
- **Do** meet WCAG 2.2 AA: contrast-checked dashboard text colours, visible 2px focus outlines, 44px touch targets on coarse pointers, reduced-motion fallbacks.

### Don't:
- **Don't** add drop shadows, glows or gradients; the shadow tokens are none on purpose.
- **Don't** round corners on cards, buttons, inputs, tabs or charts.
- **Don't** encode volume or rank with hue; use the ink ramp or ink opacity.
- **Don't** use green, red or yellow for anything other than better, worse and the primary action, outside the chess-convention exception under the One Meaning Rule.
- **Don't** cover the board with the trainer result; it belongs beside the board.
