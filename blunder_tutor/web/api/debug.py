from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from blunder_tutor.constants import (
    CLASSIFICATION_BLUNDER,
    CLASSIFICATION_INACCURACY,
    CLASSIFICATION_LABELS,
    MATE_SCORE_ANALYSIS,
    MATE_THRESHOLD,
    PHASE_LABELS,
)
from blunder_tutor.utils.pgn_utils import extract_game_url_from_string
from blunder_tutor.web.dependencies import AnalysisRepoDep, GameRepoDep

debug_router = APIRouter()

CENTIPAWNS_PER_PAWN = 100


def _format_eval(cp: int) -> str:
    if abs(cp) >= MATE_THRESHOLD:
        sign = "+" if cp > 0 else "-"
        mate_in = (MATE_SCORE_ANALYSIS - abs(cp) + 1) // 2
        return f"{sign}M{mate_in}"
    return f"{cp / CENTIPAWNS_PER_PAWN:+.2f}"


def _build_debug_text(
    game: dict,
    analysis_moves: list[dict],
    eco: dict,
    focus_ply: int | None = None,
) -> str:
    lines: list[str] = []

    lines.append("## Game Debug Info")
    lines.append("")  # noqa: WPS204 — markdown blank-line separators in a single linear builder; helper would obscure the layout.
    lines.append(f"- **Game ID**: `{game['id']}`")
    lines.append(f"- **Source**: {game.get('source', 'unknown')}")
    lines.append(f"- **White**: {game.get('white', '?')}")
    lines.append(f"- **Black**: {game.get('black', '?')}")
    lines.append(f"- **Result**: {game.get('result', '?')}")
    lines.append(f"- **Date**: {game.get('date', '?')}")
    lines.append(f"- **Time Control**: {game.get('time_control', '?')}")
    lines.append(f"- **Player username**: {game.get('username', '?')}")

    if eco.get("eco_code"):
        lines.append(f"- **Opening**: {eco['eco_code']} {eco.get('eco_name', '')}")

    game_url = extract_game_url_from_string(game.get("pgn_content", ""))
    if game_url:
        lines.append(f"- **Original game**: {game_url}")

    lines.append("")
    lines.append("## PGN")
    lines.append("")
    lines.append("```")
    lines.append(game.get("pgn_content", "").strip())
    lines.append("```")

    focus_move = None
    if focus_ply is not None and analysis_moves:
        focus_move = next(
            (m for m in analysis_moves if m["ply"] == focus_ply),  # noqa: WPS204 — iterating analysis_moves to find target ply.
            None,
        )

    if focus_move is not None:
        player = "white" if focus_move["player"] == 0 else "black"
        cls_label = CLASSIFICATION_LABELS.get(focus_move["classification"], "normal")
        phase_label = (
            PHASE_LABELS.get(focus_move.get("game_phase"), "?")
            if focus_move.get("game_phase") is not None
            else "?"
        )
        lines.append("")
        lines.append(f"## ⚠️ Currently Investigating (ply {focus_ply})")
        lines.append("")
        lines.append(
            f"- **Move**: {focus_move.get('san', focus_move.get('uci', '?'))} ({player}, move {focus_move['move_number']})"
        )
        lines.append(f"- **Classification**: {cls_label}")
        lines.append(
            f"- **Eval**: {_format_eval(focus_move['eval_before'])} → {_format_eval(focus_move['eval_after'])}"
        )
        lines.append(f"- **CP Loss**: {focus_move['cp_loss']}")
        lines.append(f"- **Phase**: {phase_label}")

    if analysis_moves:
        lines.append("")
        lines.append("## Analysis (move-by-move)")
        lines.append("")
        lines.append(
            "| Ply | Move# | Player | SAN | Eval Before | Eval After | CP Loss | Classification | Phase |"
        )
        lines.append(
            "|-----|-------|--------|-----|-------------|------------|---------|----------------|-------|"
        )
        for m in analysis_moves:
            player = "white" if m["player"] == 0 else "black"
            cls_label = CLASSIFICATION_LABELS.get(m["classification"], "normal")
            phase_label = (
                PHASE_LABELS.get(m["game_phase"], "?")
                if m.get("game_phase") is not None
                else "?"
            )
            marker = (
                f" **{cls_label.upper()}**"
                if m["classification"] >= CLASSIFICATION_INACCURACY
                else ""
            )
            focus_marker = (
                " ← 🔍" if focus_ply is not None and m["ply"] == focus_ply else ""
            )
            lines.append(
                f"| {m['ply']} | {m['move_number']} | {player} | {m.get('san', m.get('uci', '?'))} "
                f"| {_format_eval(m['eval_before'])} | {_format_eval(m['eval_after'])} "
                f"| {m['cp_loss']} | {cls_label}{marker} | {phase_label}{focus_marker} |"
            )

        blunders = [
            move
            for move in analysis_moves
            if move["classification"] == CLASSIFICATION_BLUNDER
        ]
        if blunders:
            lines.append("")
            lines.append("## Blunders Summary")
            lines.append("")
            for m in blunders:
                player = "white" if m["player"] == 0 else "black"
                is_focus = focus_ply is not None and m["ply"] == focus_ply
                prefix = "🔍 " if is_focus else ""
                lines.append(
                    f"- {prefix}**Ply {m['ply']}** ({player}, move {m['move_number']}): "
                    f"{m.get('san', m.get('uci', '?'))} — "
                    f"eval {_format_eval(m['eval_before'])} → {_format_eval(m['eval_after'])} "
                    f"(cp_loss={m['cp_loss']}, phase={PHASE_LABELS.get(m.get('game_phase'), '?')})"
                )
    else:
        lines.append("")
        lines.append("## Analysis")
        lines.append("")
        lines.append("_No analysis data available for this game._")

    return "\n".join(lines)


@debug_router.get(
    "/api/games/{game_id}/debug",
    response_class=PlainTextResponse,
    summary="Get game debug info",
    description="Returns a self-contained debug snapshot of a game with PGN and analysis data.",
)
async def game_debug_info(
    game_id: str,
    game_repo: GameRepoDep,
    analysis_repo: AnalysisRepoDep,
    ply: Annotated[
        int | None,
        Query(description="Ply of the specific blunder being investigated"),
    ] = None,
) -> PlainTextResponse:
    game = await game_repo.get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Game not found: {game_id}"
        )

    analysis_moves = await analysis_repo.fetch_moves(game_id)
    eco = await analysis_repo.get_game_eco(game_id)

    text = _build_debug_text(game, analysis_moves, eco, focus_ply=ply)
    return PlainTextResponse(text)
