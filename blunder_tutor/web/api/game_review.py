from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from blunder_tutor.constants import CLASSIFICATION_LABELS, COLOR_LABELS, PHASE_LABELS
from blunder_tutor.utils.pgn_utils import extract_game_url_from_string
from blunder_tutor.web.dependencies import AnalysisRepoDep, GameRepoDep

game_review_router = APIRouter()


class ReviewGameInfo(BaseModel):
    id: str = Field(description="Game ID")
    white: str = Field(description="White player name")
    black: str = Field(description="Black player name")
    result: str = Field(description="Game result")
    date: str | None = Field(description="Game date")
    time_control: str | None = Field(description="Time control")
    source: str | None = Field(description="Game source platform")
    game_url: str | None = Field(description="URL to original game")
    eco_code: str | None = Field(description="ECO opening code")
    eco_name: str | None = Field(description="Opening name")
    username: str | None = Field(description="User's username")


class ReviewMove(BaseModel):
    ply: int = Field(description="Ply number")
    move_number: int = Field(description="Move number")
    player: str = Field(description="Player color (white/black)")
    san: str = Field(description="Move in SAN notation")
    uci: str = Field(description="Move in UCI notation")
    eval_before: int = Field(description="Eval before move (centipawns)")
    eval_after: int = Field(description="Eval after move (centipawns)")
    cp_loss: int = Field(description="Centipawn loss")
    classification: str = Field(description="Move classification")
    game_phase: str | None = Field(description="Game phase")


class GameReviewResponse(BaseModel):
    game: ReviewGameInfo = Field(description="Game metadata")
    moves: list[ReviewMove] = Field(description="Analyzed moves")
    analyzed: bool = Field(description="Whether the game has been analyzed")


@game_review_router.get(
    "/api/games/{game_id}/review",
    response_model=GameReviewResponse,
    summary="Get game review data",
    description="Returns game metadata and move-by-move analysis for the game review page.",
)
async def get_game_review(
    game_id: str,
    game_repo: GameRepoDep,
    analysis_repo: AnalysisRepoDep,
) -> dict:
    game = await game_repo.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    analysis_moves, eco = await asyncio.gather(
        analysis_repo.fetch_moves(game_id),
        analysis_repo.get_game_eco(game_id),
    )

    game_url = extract_game_url_from_string(game.get("pgn_content", ""))

    game_info = {
        "id": game["id"],
        "white": game.get("white", "?"),
        "black": game.get("black", "?"),
        "result": game.get("result", "?"),
        "date": game.get("date"),
        "time_control": game.get("time_control"),
        "source": game.get("source"),
        "game_url": game_url,
        "eco_code": eco.get("eco_code") if eco else None,
        "eco_name": eco.get("eco_name") if eco else None,
        "username": game.get("username"),
    }

    moves = [
        {
            "ply": m["ply"],
            "move_number": m["move_number"],
            "player": COLOR_LABELS.get(m["player"], "white"),
            "san": m.get("san", m.get("uci", "?")),
            "uci": m.get("uci", "?"),
            "eval_before": m["eval_before"],
            "eval_after": m["eval_after"],
            "cp_loss": m["cp_loss"],
            "classification": CLASSIFICATION_LABELS.get(m["classification"], "normal"),
            "game_phase": PHASE_LABELS.get(m.get("game_phase"))
            if m.get("game_phase") is not None
            else None,
        }
        for m in analysis_moves
    ]

    return {
        "game": game_info,
        "moves": moves,
        "analyzed": len(analysis_moves) > 0,
    }
