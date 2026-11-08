# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Club-level online players, roughly 1000–2000 rating, who play regularly on Lichess or Chess.com and keep losing games to the same kinds of mistakes. Their job: turn their own blunders into practice so they stop repeating them.

## Product Purpose

Blunder Tutor imports a player's games, finds the positions where they went wrong with Stockfish, and turns those positions into puzzles they drill until the pattern sticks. Success is fewer repeated mistakes in real games, visible as improving accuracy and a shrinking set of weak patterns on the dashboard.

## Positioning

It trains *your* mistakes, not random tactics. Lichess shows a blunder but does not drill it; Chess.com review is paywalled; generic puzzle sites train other people's positions. Blunder Tutor combines finding, drilling, and tracking one player's own errors, for free, on their own machine.

## Operating Context

- **Focused desktop sessions:** the primary scene. Sitting at a computer with a keyboard, working through puzzles for 15–30 minutes.
- **Short phone bursts:** a few positions on the go, touch input.
- **Periodic stats review:** opening the dashboard to see weak openings, phases, difficulty, and tactical patterns.
- Games arrive from Lichess and Chess.com sync, or pasted PGN. First analysis runs in the background and can take a while; progress lives on Management.

## Capabilities and Constraints

- Trainer (puzzles from own blunders, SRS "Blunder Inbox"), game review with engine, dashboard, opening traps, starred puzzles, profiles, management, import, settings.
- Self-hosted single process (FastAPI + SQLite + Stockfish). Single-user by default; optional multi-user credentials mode.
- Public read-only demo instance exists; demo mode disables writes.
- **Must preserve:** free and self-hosted (no paywall, data stays with the user); all UI available in 7 languages.
- Keyboard/vim move input and user theming (custom colours, boards, piece sets) exist today but were not named as binding; they may be reshaped.

## Brand Commitments

- Name: Blunder Tutor.
- Free and local is a core promise in copy and product decisions.

## Evidence on Hand

- README screenshots in `images/`.
- Demo database `demo/demo.sqlite3` with real analysed games.
- Live demo: https://blunders-demo.mrlokans.work/
- Design write-up: https://mrlokans.work/posts/building-self-hosted-chess-blunder-trainer/
- No testimonials, user counts, or benchmarks exist; do not invent them.

## Product Principles

1. Your own mistakes first: every surface should lead back to the player's real positions.
2. The training loop is the product: attempt → feedback → understanding → retry should be fast and clear.
3. Show patterns, not just numbers: stats exist to tell the player what to practise next.
4. Free, local, private: never design toward accounts, upsells, or data leaving the machine.

## Accessibility & Inclusion

Target WCAG 2.2 AA: keyboard operability, visible focus, contrast in light and dark themes, reduced motion, 44px touch targets, screen-reader status for move results. Seven locales with varying string lengths.
