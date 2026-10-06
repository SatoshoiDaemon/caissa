from dataclasses import dataclass

from ..chess_logic.chess_game import ChessGame


@dataclass
class GameState:
    chess_game: ChessGame
    status: str = "active"
    version: int = 0
    winner: str | None = None

    def as_dict(self):
        result = self.chess_game.get_game_status()
        result.update({"status": self.status, "version": self.version, "winner": self.winner})
        return result
