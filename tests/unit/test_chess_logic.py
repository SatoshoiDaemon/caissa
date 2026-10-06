import pytest

from backend.chess_logic import ChessGame, Color, InvalidFenError

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
BARE_ROOKS_FEN = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
PROMOTION_FEN = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"


def game_from_fen(fen):
    game = ChessGame()
    game.load_from_fen(fen)
    return game


def test_initial_fen_contains_all_six_fields():
    game = ChessGame()
    assert game.to_fen() == INITIAL_FEN
    assert len(game.to_fen().split()) == 6


def test_king_cannot_move_onto_ally_piece():
    assert ChessGame().move("e1", "f1") is False


def test_pawn_attacks_empty_square():
    game = game_from_fen("4k3/8/8/8/3p4/8/8/4K3 w - - 0 1")
    assert game._is_under_attack(5, 2, Color.WHITE) is True
    assert game._is_under_attack(5, 4, Color.WHITE) is True


def test_pawn_capture_requires_an_enemy_or_en_passant():
    game = game_from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    assert game.move("e2", "d3") is False


def test_castling_requires_the_correct_rook():
    game = game_from_fen(BARE_ROOKS_FEN)
    assert game.move("e1", "g1") is True
    assert game.get_board_state()[7][5]["type"] == "r"
    game = game_from_fen("4k3/8/8/8/8/8/8/4K3 w KQkq - 0 1")
    assert game.move("e1", "g1") is False


def test_castling_rights_are_revoked_after_king_or_rook_moves():
    game = game_from_fen(BARE_ROOKS_FEN)
    assert game.move("h1", "h2") is True
    assert "K" not in game.to_fen().split()[2]
    game = game_from_fen(BARE_ROOKS_FEN)
    assert game.move("e1", "f1") is True
    assert "K" not in game.to_fen().split()[2]
    assert "Q" not in game.to_fen().split()[2]


def test_rook_right_is_revoked_when_the_rook_is_captured():
    game = game_from_fen("r3k3/8/8/8/8/8/8/R3K3 b q - 0 1")
    assert game.move("a8", "a1") is True
    assert "q" not in game.to_fen().split()[2]


def test_en_passant_is_created_and_consumed():
    game = game_from_fen("4k3/3p4/8/4P3/8/8/8/4K3 b - - 0 1")
    assert game.move("d7", "d5") is True
    assert game.en_passant_target == "d6"
    assert game.move("e5", "d6") is True
    assert game.en_passant_target is None
    assert game.get_board_state()[2][3]["type"] == "p"
    assert game.get_board_state()[3][3] is None


@pytest.mark.parametrize("promotion", ["q", "r", "b", "n"])
def test_all_promotion_choices_are_supported(promotion):
    game = game_from_fen(PROMOTION_FEN)
    assert game.move("a7", "a8", promotion) is True
    assert game.get_board_state()[0][0]["type"] == promotion
    assert game.move_history[-1]["piece"] == "p"
    assert game.move_history[-1]["promotion"] == promotion


def test_promotion_must_be_explicit_and_valid():
    game = game_from_fen(PROMOTION_FEN)
    assert game.move("a7", "a8") is False
    assert game.move("a7", "a8", "k") is False


def test_fen_round_trip_preserves_castling_en_passant_and_counters():
    fen = "r3k2r/8/8/3pP3/8/8/8/R3K2R b KQkq d3 17 42"
    game = game_from_fen(fen)
    assert game.to_fen() == fen
    assert game.castling_rights == {"K", "Q", "k", "q"}
    assert game.en_passant_target == "d3"
    assert game.halfmove_clock == 17
    assert game.fullmove_number == 42


@pytest.mark.parametrize(
    "fen",
    [
        "invalid",
        "8/8/8/8/8/8/8/8 w - - 0 1",
        "8/8/8/8/8/8/8/4K2K w - - 0 1",
        "8/8/8/8/8/8/8/4K1k1 w BAD - 0 1",
        "8/8/8/8/8/8/8/4K1k1 w - e4 0 1",
        "8/8/8/8/8/8/8/4K1k1 w - - -1 1",
    ],
)
def test_malformed_fen_is_rejected(fen):
    with pytest.raises(InvalidFenError):
        ChessGame().load_from_fen(fen)


def test_checkmate_and_stalemate_are_distinguished():
    checkmate = game_from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    assert checkmate.is_checkmate(Color.BLACK) is True
    assert checkmate.is_stalemate(Color.BLACK) is False
    stalemate = game_from_fen("7k/5Q2/7K/8/8/8/8/8 b - - 0 1")
    assert stalemate.is_checkmate(Color.BLACK) is False
    assert stalemate.is_stalemate(Color.BLACK) is True
