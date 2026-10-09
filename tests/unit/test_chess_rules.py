import pytest

from backend.chess_logic import ChessGame, InvalidFenError
from backend.chess_logic.pgn import InvalidPgnError, export_pgn, import_pgn


def game_from_fen(fen):
    game = ChessGame()
    game.load_from_fen(fen)
    return game


def test_insufficient_material_cases():
    assert game_from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1").is_insufficient_material()
    assert game_from_fen("4k3/8/8/8/8/8/2B5/4K3 w - - 0 1").is_insufficient_material()
    assert game_from_fen("4k3/8/8/8/8/8/2N5/4K3 w - - 0 1").is_insufficient_material()
    assert game_from_fen("4kb2/8/8/8/8/8/8/2B1K3 w - - 0 1").is_insufficient_material()


def test_material_with_pawn_is_not_insufficient():
    assert not game_from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1").is_insufficient_material()


def test_fifty_move_draw_uses_halfmove_clock():
    assert game_from_fen("4k3/8/8/8/8/8/8/4K3 w - - 99 1").is_fifty_move_draw() is False
    assert game_from_fen("4k3/8/8/8/8/8/8/4K3 w - - 100 1").is_fifty_move_draw() is True


def test_threefold_repetition_counts_side_castling_and_en_passant():
    game = ChessGame()
    positions = [game.position_key()]
    for move in (("g1", "f3"), ("g8", "f6"), ("f3", "g1"), ("f6", "g8")) * 2:
        assert game.move(*move)
        positions.append(game.position_key())
    assert game.is_threefold_repetition(positions)


def test_strict_fen_semantics():
    invalid = [
        "4k3/8/8/8/8/8/4P3/4K3 w K - 0 1",
        "4k3/8/8/8/8/8/8/3Q4 w - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w - e3 0 1",
        "4k3/4R3/8/8/8/8/4r3/4K3 w - - 0 1",
    ]
    for fen in invalid:
        with pytest.raises(InvalidFenError):
            game_from_fen(fen)


def test_san_supports_disambiguation_castling_and_mate():
    ambiguous = game_from_fen("4k3/8/8/8/8/8/1N1N4/4K3 w - - 0 1")
    assert ambiguous.san_for_move("b2", "c4") == "Nbc4"
    assert ambiguous.san_for_move("d2", "c4") == "Ndc4"

    game = ChessGame()
    assert game.san_for_move("e2", "e4") == "e4"
    game.move("e2", "e4")
    assert game.san_for_move("e7", "e5") == "e5"

    castle = game_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert castle.san_for_move("e1", "g1") == "O-O"
    mate = game_from_fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
    assert mate.san_for_move("f7", "g7") == "Qg7#"


def test_pgn_round_trip_and_invalid_san():
    pgn = '[White "Alice"]\n[Black "Bob"]\n\n1. e4 e5 2. Nf3 Nc6 *'
    game, headers, result = import_pgn(pgn)
    assert headers["White"] == "Alice"
    assert result == "*"
    document = {
        "status": "imported",
        "winner": None,
        "white": {"name": "Alice"},
        "black": {"name": "Bob"},
        "move_history": game.move_history,
        "initial_fen": ChessGame().to_fen(),
    }
    exported = export_pgn(document)
    assert "1. e4 e5 2. Nf3 Nc6 *" in exported
    with pytest.raises(InvalidPgnError):
        import_pgn("1. e5 *")
