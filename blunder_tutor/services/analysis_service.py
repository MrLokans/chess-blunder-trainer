from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.constants import MATE_SCORE_WEB
from blunder_tutor.utils.chess_utils import board_from_fen, format_eval

if TYPE_CHECKING:
    from blunder_tutor.analysis.engine_pool import WorkCoordinator


@dataclass
class PositionAnalysis:
    eval_cp: int
    eval_display: str
    best_move_uci: str | None
    best_move_san: str | None
    best_line: list[str]


@dataclass
class MoveEvaluation:
    eval_cp: int
    eval_display: str


@dataclass
class PunishmentAnalysis:
    line: list[str]
    eval_cp: int
    eval_display: str
    material_swing: int
    lost_material: str | None
    summary: str | None


def _extract_best_line(
    board: chess.Board, pv: list[chess.Move]
) -> tuple[str | None, str | None, list[str]]:
    if not pv:
        return None, None, []
    best_uci = pv[0].uci()
    best_san = board.san(pv[0])
    line: list[str] = []
    temp_board = board.copy()
    for move in pv[:5]:
        line.append(temp_board.san(move))
        temp_board.push(move)
    return best_uci, best_san, line


def _eval_cp_from_info(info: chess.engine.InfoDict) -> int:
    score = info.get("score")
    return score.white().score(mate_score=MATE_SCORE_WEB) if score else 0


def _format_eval(eval_cp: int, player_color: str | None) -> str:
    if player_color:
        return format_eval(eval_cp, player_color)
    return str(eval_cp)


_PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def _color_from_name(player_color: str) -> chess.Color:
    return chess.BLACK if player_color == "black" else chess.WHITE


def _count_material(board: chess.Board, color: chess.Color) -> int:
    return sum(
        _PIECE_VALUES.get(piece.piece_type, 0)
        for square in chess.SQUARES
        if (piece := board.piece_at(square)) and piece.color == color
    )


def _material_balance(board: chess.Board, color: chess.Color) -> int:
    return _count_material(board, color) - _count_material(board, not color)


def _lost_material_label(material_loss: int) -> str | None:
    if material_loss >= 9:
        return "a queen or equivalent material"
    if material_loss >= 5:
        return "a rook or equivalent material"
    if material_loss >= 3:
        return "a minor piece or equivalent material"
    if material_loss >= 1:
        return "material"
    return None


def _format_line(line: list[str]) -> str:
    return " ".join(line[:6])


def _build_punishment_summary(
    *,
    blunder_san: str,
    line: list[str],
    best_move_san: str | None,
    material_swing: int,
    lost_material: str | None,
    cp_loss: int,
    gives_mate: bool,
) -> str:
    line_text = _format_line(line)
    if gives_mate:
        concrete = f"After {line_text}, the line ends in checkmate."
    elif lost_material:
        concrete = f"After {line_text}, you lose {lost_material}."
    elif cp_loss >= 100:
        pawn_loss = cp_loss / 100
        concrete = (
            f"A likely continuation is {line_text}. The evaluation drops by "
            f"about {pawn_loss:.1f} pawns."
        )
    else:
        concrete = f"A likely continuation is {line_text}."

    better = f" Better was {best_move_san}." if best_move_san else ""
    return (
        f"The move {blunder_san} is a blunder because the opponent gets a "
        f"concrete continuation. {concrete}{better}"
    )


class AnalysisService:
    def __init__(self, coordinator: WorkCoordinator, limit: chess.engine.Limit) -> None:
        self._coordinator = coordinator
        self.limit = limit

    async def analyze_position(
        self, fen: str, player_color: str | None = None
    ) -> PositionAnalysis:
        board = chess.Board(fen)
        info = await self._analyse(board)
        eval_cp = _eval_cp_from_info(info)
        best_uci, best_san, best_line = _extract_best_line(board, info.get("pv", []))

        return PositionAnalysis(
            eval_cp=eval_cp,
            eval_display=_format_eval(eval_cp, player_color),
            best_move_uci=best_uci,
            best_move_san=best_san,
            best_line=best_line,
        )

    async def evaluate_move(
        self, fen: str, move_uci: str, player_color: str | None = None
    ) -> MoveEvaluation:
        board = board_from_fen(fen)

        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc

        if move not in board.legal_moves:
            raise ValueError(f"Illegal move: {move_uci}")

        board.push(move)
        info = await self._analyse(board)
        eval_cp = _eval_cp_from_info(info)

        return MoveEvaluation(
            eval_cp=eval_cp,
            eval_display=_format_eval(eval_cp, player_color),
        )



    async def analyze_punishment_line(
        self,
        fen: str,
        blunder_uci: str,
        player_color: str,
        best_move_san: str | None = None,
        cp_loss: int = 0,
    ) -> PunishmentAnalysis:
        board = board_from_fen(fen)
        try:
            blunder_move = chess.Move.from_uci(blunder_uci)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {blunder_uci}") from exc

        if blunder_move not in board.legal_moves:
            raise ValueError(f"Illegal move: {blunder_uci}")

        player = _color_from_name(player_color)
        balance_before = _material_balance(board, player)
        blunder_san = board.san(blunder_move)
        board.push(blunder_move)

        info = await self._analyse(board)
        eval_cp = _eval_cp_from_info(info)
        line_board = board.copy()
        line = [blunder_san]

        for move in info.get("pv", [])[:5]:
            if move not in line_board.legal_moves:
                break
            line.append(line_board.san(move))
            line_board.push(move)

        material_swing = _material_balance(line_board, player) - balance_before
        lost_material = _lost_material_label(-material_swing)
        summary = _build_punishment_summary(
            blunder_san=blunder_san,
            line=line,
            best_move_san=best_move_san,
            material_swing=material_swing,
            lost_material=lost_material,
            cp_loss=cp_loss,
            gives_mate=line_board.is_checkmate(),
        )

        return PunishmentAnalysis(
            line=line,
            eval_cp=eval_cp,
            eval_display=_format_eval(eval_cp, player_color),
            material_swing=material_swing,
            lost_material=lost_material,
            summary=summary,
        )

    def get_move_san(self, fen: str, move_uci: str) -> str:
        board = board_from_fen(fen)
        try:
            move = chess.Move.from_uci(move_uci)
            return board.san(move)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc

    async def _analyse(self, board: chess.Board) -> chess.engine.InfoDict:
        limit = self.limit

        async def _work(engine: chess.engine.UciProtocol) -> chess.engine.InfoDict:  # noqa: WPS430 — `coordinator.submit` closure; captures `board`/`limit`.
            return await engine.analyse(board, limit)

        return await self._coordinator.submit(_work)
