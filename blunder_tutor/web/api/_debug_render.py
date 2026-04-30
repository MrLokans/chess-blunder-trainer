from __future__ import annotations

from blunder_tutor.constants import (
    CLASSIFICATION_BLUNDER,
    CLASSIFICATION_INACCURACY,
    CLASSIFICATION_LABELS,
    MATE_SCORE_ANALYSIS,
    MATE_THRESHOLD,
    PHASE_LABELS,
)
from blunder_tutor.utils.pgn_utils import extract_game_url_from_string

CENTIPAWNS_PER_PAWN = 100


def _format_eval(cp: int) -> str:
    if abs(cp) >= MATE_THRESHOLD:
        sign = "+" if cp > 0 else "-"
        mate_in = (MATE_SCORE_ANALYSIS - abs(cp) + 1) // 2
        return f"{sign}M{mate_in}"
    return f"{cp / CENTIPAWNS_PER_PAWN:+.2f}"


def _player_label(player: int) -> str:
    return "white" if player == 0 else "black"


def _phase_label(move: dict) -> str:
    phase = move.get("game_phase")
    return PHASE_LABELS.get(phase, "?") if phase is not None else "?"


def _move_san_or_uci(move: dict) -> str:
    return move.get("san", move.get("uci", "?"))


def _render_header(game: dict, eco: dict) -> list[str]:
    lines = [
        "## Game Debug Info",
        "",
        f"- **Game ID**: `{game['id']}`",
        f"- **Source**: {game.get('source', 'unknown')}",
        f"- **White**: {game.get('white', '?')}",
        f"- **Black**: {game.get('black', '?')}",
        f"- **Result**: {game.get('result', '?')}",
        f"- **Date**: {game.get('date', '?')}",
        f"- **Time Control**: {game.get('time_control', '?')}",
        f"- **Player username**: {game.get('username', '?')}",
    ]
    if eco.get("eco_code"):
        lines.append(f"- **Opening**: {eco['eco_code']} {eco.get('eco_name', '')}")
    game_url = extract_game_url_from_string(game.get("pgn_content", ""))
    if game_url:
        lines.append(f"- **Original game**: {game_url}")
    return lines


def _render_pgn(game: dict) -> list[str]:
    return [
        "",
        "## PGN",
        "",
        "```",
        game.get("pgn_content", "").strip(),
        "```",
    ]


def _render_focus(focus_move: dict, focus_ply: int) -> list[str]:
    cls_label = CLASSIFICATION_LABELS.get(focus_move["classification"], "normal")
    eval_str = (
        f"{_format_eval(focus_move['eval_before'])}"
        f" → {_format_eval(focus_move['eval_after'])}"
    )
    return [
        "",
        f"## ⚠️ Currently Investigating (ply {focus_ply})",
        "",
        f"- **Move**: {_move_san_or_uci(focus_move)} "
        f"({_player_label(focus_move['player'])}, "
        f"move {focus_move['move_number']})",
        f"- **Classification**: {cls_label}",
        f"- **Eval**: {eval_str}",
        f"- **CP Loss**: {focus_move['cp_loss']}",
        f"- **Phase**: {_phase_label(focus_move)}",
    ]


def _format_analysis_row(move: dict, focus_ply: int | None) -> str:
    cls_label = CLASSIFICATION_LABELS.get(move["classification"], "normal")
    marker = (
        f" **{cls_label.upper()}**"
        if move["classification"] >= CLASSIFICATION_INACCURACY
        else ""
    )
    focus_marker = " ← 🔍" if focus_ply is not None and move["ply"] == focus_ply else ""
    eval_before = _format_eval(move["eval_before"])
    eval_after = _format_eval(move["eval_after"])
    return (
        f"| {move['ply']} | {move['move_number']} | {_player_label(move['player'])} "
        f"| {_move_san_or_uci(move)} | {eval_before} | {eval_after} "
        f"| {move['cp_loss']} | {cls_label}{marker} "
        f"| {_phase_label(move)}{focus_marker} |"
    )


def _render_analysis_table(
    analysis_moves: list[dict], focus_ply: int | None
) -> list[str]:
    lines = [
        "",
        "## Analysis (move-by-move)",
        "",
        "| Ply | Move# | Player | SAN | Eval Before | Eval After "
        "| CP Loss | Classification | Phase |",
        "|-----|-------|--------|-----|-------------|------------"
        "|---------|----------------|-------|",
    ]
    lines.extend(_format_analysis_row(m, focus_ply) for m in analysis_moves)
    return lines


def _format_blunder_summary(move: dict, focus_ply: int | None) -> str:
    prefix = "🔍 " if focus_ply is not None and move["ply"] == focus_ply else ""
    eval_str = (
        f"{_format_eval(move['eval_before'])} → {_format_eval(move['eval_after'])}"
    )
    phase = PHASE_LABELS.get(move.get("game_phase"), "?")
    return (
        f"- {prefix}**Ply {move['ply']}** ({_player_label(move['player'])}, "
        f"move {move['move_number']}): {_move_san_or_uci(move)} — "
        f"eval {eval_str} (cp_loss={move['cp_loss']}, phase={phase})"
    )


def _render_blunders_summary(
    analysis_moves: list[dict], focus_ply: int | None
) -> list[str]:
    blunders = [
        move
        for move in analysis_moves
        if move["classification"] == CLASSIFICATION_BLUNDER
    ]
    if not blunders:
        return []
    return ["", "## Blunders Summary", ""] + [
        _format_blunder_summary(move, focus_ply) for move in blunders
    ]


def _find_focus_move(analysis_moves: list[dict], focus_ply: int | None) -> dict | None:
    if focus_ply is None or not analysis_moves:
        return None
    return next((m for m in analysis_moves if m["ply"] == focus_ply), None)


def build_debug_text(
    game: dict,
    analysis_moves: list[dict],
    eco: dict,
    focus_ply: int | None = None,
) -> str:
    lines = _render_header(game, eco)
    lines.extend(_render_pgn(game))

    focus_move = _find_focus_move(analysis_moves, focus_ply)
    if focus_move is not None and focus_ply is not None:
        lines.extend(_render_focus(focus_move, focus_ply))

    if analysis_moves:
        lines.extend(_render_analysis_table(analysis_moves, focus_ply))
        lines.extend(_render_blunders_summary(analysis_moves, focus_ply))
    else:
        lines.extend(
            ["", "## Analysis", "", "_No analysis data available for this game._"]
        )

    return "\n".join(lines)
