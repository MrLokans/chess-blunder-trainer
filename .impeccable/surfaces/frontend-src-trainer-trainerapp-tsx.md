---
version: 1
slug: "frontend-src-trainer-trainerapp-tsx"
primary_target: "frontend/src/trainer/TrainerApp.tsx"
related_targets: ["templates/trainer.html"]
---

# Trainer — result state

Mode: Operate. Club player (1000–2000) just made a move on a puzzle from their own game; the job is to understand what they missed and move on.

## Direction contract

THESIS: After a move the board stays whole and the answer lives beside it as two futures: the position after your move and after the best move. Refuses the category default of a modal/toast card covering the board.

OWN-WORLD: The incumbent DNA: warm paper ground, ink-black 3px rules, square corners, Jost caps labels, green = best, red = your miss, yellow primary (Next). No new palette or type.

STORY: The player reads one headline ("You missed Rd3+ — skewer"), compares two mini boards with evals, optionally plays the best line or the refutation on the main board, then presses Next.

FIRST VIEWPORT: Desktop: main board left, unobstructed, with best/your-move arrows; right panel (filters hidden while the result shows) holds headline, two mini boards side by side (yours left, best right with green outline), eval under each, explanation, actions (Play best line, Show refutation, Next). Phone: the same panel stacks directly under the board and scrolls into view.

FORM: Two boards, dealt structure 5 of 7 on the ordered list. seed:63195c5afcab268e

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open
- Retry with hint and session progress belong to TREK-288.
