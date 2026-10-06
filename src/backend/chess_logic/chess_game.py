import re
from enum import Enum


class ChessStateError(ValueError):
    """Base exception for invalid chess state or input."""


class InvalidFenError(ChessStateError):
    """Raised when a FEN string does not describe a valid position."""


class PieceType(Enum):
    PAWN = "p"
    ROOK = "r"
    KNIGHT = "n"
    BISHOP = "b"
    QUEEN = "q"
    KING = "k"


class Color(Enum):
    WHITE = "white"
    BLACK = "black"


PROMOTION_TYPES = {
    "q": PieceType.QUEEN,
    "r": PieceType.ROOK,
    "b": PieceType.BISHOP,
    "n": PieceType.KNIGHT,
}
CASTLING_RIGHTS = "KQkq"
POSITION_PATTERN = re.compile(r"^[a-h][1-8]$")


class Square:
    def __init__(self, piece_type=None, color=None):
        self.piece_type = piece_type
        self.color = color

    def is_empty(self):
        return self.piece_type is None

    def copy(self):
        return Square(self.piece_type, self.color)


class ChessGame:
    def __init__(self):
        self.board = [[Square() for _ in range(8)] for _ in range(8)]
        self.current_player = Color.WHITE
        self.move_history = []
        self.captured_pieces = {Color.WHITE: [], Color.BLACK: []}
        self.castling_rights = set(CASTLING_RIGHTS)
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self._initialize_board()

    def _initialize_board(self):
        piece_order = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]
        for col, piece_type in enumerate(piece_order):
            self.board[0][col] = Square(piece_type, Color.BLACK)
            self.board[7][col] = Square(piece_type, Color.WHITE)
        for col in range(8):
            self.board[1][col] = Square(PieceType.PAWN, Color.BLACK)
            self.board[6][col] = Square(PieceType.PAWN, Color.WHITE)

    def _pos_to_coords(self, pos: str) -> tuple[int, int]:
        if not isinstance(pos, str) or not POSITION_PATTERN.fullmatch(pos):
            raise ChessStateError("invalid board position")
        return 8 - int(pos[1]), ord(pos[0]) - ord("a")

    def _coords_to_pos(self, row: int, col: int) -> str:
        return chr(col + ord("a")) + str(8 - row)

    def _get_piece_at(self, pos: str) -> Square:
        row, col = self._pos_to_coords(pos)
        return self.board[row][col]

    def _is_path_clear(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        row_step = 0 if from_row == to_row else (1 if to_row > from_row else -1)
        col_step = 0 if from_col == to_col else (1 if to_col > from_col else -1)
        row, col = from_row + row_step, from_col + col_step
        while (row, col) != (to_row, to_col):
            if not self.board[row][col].is_empty():
                return False
            row += row_step
            col += col_step
        return True

    def _piece_attacks(self, from_pos: str, to_pos: str) -> bool:
        """Return attack geometry, independent of destination occupancy."""
        piece = self._get_piece_at(from_pos)
        from_row, from_col = self._pos_to_coords(from_pos)
        to_row, to_col = self._pos_to_coords(to_pos)
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        if piece.is_empty():
            return False
        if piece.piece_type == PieceType.PAWN:
            direction = -1 if piece.color == Color.WHITE else 1
            return to_row - from_row == direction and col_diff == 1
        if piece.piece_type == PieceType.ROOK:
            return (from_row == to_row or from_col == to_col) and self._is_path_clear(
                from_row, from_col, to_row, to_col
            )
        if piece.piece_type == PieceType.KNIGHT:
            return (row_diff, col_diff) in {(1, 2), (2, 1)}
        if piece.piece_type == PieceType.BISHOP:
            return row_diff == col_diff and self._is_path_clear(from_row, from_col, to_row, to_col)
        if piece.piece_type == PieceType.QUEEN:
            return (
                (from_row == to_row or from_col == to_col) or row_diff == col_diff
            ) and self._is_path_clear(from_row, from_col, to_row, to_col)
        return row_diff <= 1 and col_diff <= 1 and row_diff + col_diff > 0

    def _is_under_attack(self, row: int, col: int, color: Color) -> bool:
        opponent = Color.BLACK if color == Color.WHITE else Color.WHITE
        target = self._coords_to_pos(row, col)
        for source_row in range(8):
            for source_col in range(8):
                piece = self.board[source_row][source_col]
                if piece.color == opponent and self._piece_attacks(
                    self._coords_to_pos(source_row, source_col), target
                ):
                    return True
        return False

    def _find_king(self, color: Color) -> tuple[int, int] | None:
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece.piece_type == PieceType.KING and piece.color == color:
                    return row, col
        return None

    def _is_in_check(self, color: Color) -> bool:
        king = self._find_king(color)
        return king is not None and self._is_under_attack(king[0], king[1], color)

    def _pawn_move_valid(self, from_pos: str, to_pos: str) -> bool:
        piece = self._get_piece_at(from_pos)
        target = self._get_piece_at(to_pos)
        from_row, from_col = self._pos_to_coords(from_pos)
        to_row, to_col = self._pos_to_coords(to_pos)
        direction = -1 if piece.color == Color.WHITE else 1
        row_diff, col_diff = to_row - from_row, to_col - from_col
        if col_diff == 0:
            if row_diff == direction:
                return target.is_empty()
            if row_diff == 2 * direction:
                start_row = 6 if piece.color == Color.WHITE else 1
                middle = self.board[from_row + direction][from_col]
                return from_row == start_row and target.is_empty() and middle.is_empty()
            return False
        if abs(col_diff) == 1 and row_diff == direction:
            if not target.is_empty() and target.color != piece.color:
                return True
            return to_pos == self.en_passant_target
        return False

    def _can_castle(self, color: Color, from_pos: str, to_pos: str) -> bool:
        row = 7 if color == Color.WHITE else 0
        if from_pos != ("e1" if color == Color.WHITE else "e8"):
            return False
        if to_pos == ("g1" if color == Color.WHITE else "g8"):
            right, rook_pos, rook_col, transit = (
                ("K" if color == Color.WHITE else "k"),
                ("h1" if color == Color.WHITE else "h8"),
                7,
                (5, 6),
            )
        elif to_pos == ("c1" if color == Color.WHITE else "c8"):
            right, rook_pos, rook_col, transit = (
                ("Q" if color == Color.WHITE else "q"),
                ("a1" if color == Color.WHITE else "a8"),
                0,
                (3, 2),
            )
        else:
            return False
        rook = self._get_piece_at(rook_pos)
        if (
            right not in self.castling_rights
            or rook.piece_type != PieceType.ROOK
            or rook.color != color
        ):
            return False
        if any(
            not self.board[row][col].is_empty()
            for col in range(min(4, rook_col) + 1, max(4, rook_col))
        ):
            return False
        if self._is_in_check(color):
            return False
        return all(not self._is_under_attack(row, col, color) for col in transit)

    def _is_move_valid(
        self,
        from_pos: str,
        to_pos: str,
        color: Color | None = None,
        enforce_turn: bool = True,
        promotion: str | None = None,
    ) -> bool:
        from_piece = self._get_piece_at(from_pos)
        target = self._get_piece_at(to_pos)
        moving_color = color or self.current_player
        if from_piece.is_empty() or from_piece.color != moving_color or from_pos == to_pos:
            return False
        if not target.is_empty() and target.color == from_piece.color:
            return False
        if enforce_turn and from_piece.color != self.current_player:
            return False
        _, from_col = self._pos_to_coords(from_pos)
        to_row, to_col = self._pos_to_coords(to_pos)
        if from_piece.piece_type == PieceType.KING and abs(to_col - from_col) == 2:
            if not self._can_castle(from_piece.color, from_pos, to_pos):
                return False
        elif from_piece.piece_type == PieceType.KING:
            if not self._piece_attacks(from_pos, to_pos):
                return False
        elif from_piece.piece_type == PieceType.PAWN:
            if not self._pawn_move_valid(from_pos, to_pos):
                return False
        elif not self._piece_attacks(from_pos, to_pos):
            return False
        reaches_back_rank = from_piece.piece_type == PieceType.PAWN and to_row in (0, 7)
        if reaches_back_rank and promotion not in PROMOTION_TYPES:
            return False
        if not reaches_back_rank and promotion is not None:
            return False
        simulation = self.clone()
        simulation._apply_move(from_pos, to_pos, promotion)
        return not simulation._is_in_check(moving_color)

    def _legal_moves(self, color: Color) -> set[tuple[str, str]]:
        legal = set()
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece.color != color:
                    continue
                source = self._coords_to_pos(row, col)
                for target_row in range(8):
                    for target_col in range(8):
                        target = self._coords_to_pos(target_row, target_col)
                        promotions = (
                            PROMOTION_TYPES
                            if piece.piece_type == PieceType.PAWN and target_row in (0, 7)
                            else {None: None}
                        )
                        if any(
                            self._is_move_valid(source, target, color, False, promotion)
                            for promotion in promotions
                        ):
                            legal.add((source, target))
        return legal

    def is_checkmate(self, color: Color) -> bool:
        return self._is_in_check(color) and not self._legal_moves(color)

    def is_stalemate(self, color: Color) -> bool:
        return not self._is_in_check(color) and not self._legal_moves(color)

    def _revoke_rook_right(self, position: str):
        self.castling_rights.discard({"a1": "Q", "h1": "K", "a8": "q", "h8": "k"}.get(position, ""))

    def _apply_move(self, from_pos: str, to_pos: str, promotion: str | None = None):
        piece = self._get_piece_at(from_pos)
        target = self._get_piece_at(to_pos)
        from_row, from_col = self._pos_to_coords(from_pos)
        to_row, to_col = self._pos_to_coords(to_pos)
        original_type = piece.piece_type
        captured_type = target.piece_type.value if not target.is_empty() else None
        was_en_passant = (
            original_type == PieceType.PAWN
            and to_pos == self.en_passant_target
            and target.is_empty()
        )
        if not target.is_empty() and target.piece_type == PieceType.ROOK:
            self._revoke_rook_right(to_pos)
        if original_type == PieceType.KING:
            self.castling_rights.difference_update(
                {"K", "Q"} if piece.color == Color.WHITE else {"k", "q"}
            )
            if abs(to_col - from_col) == 2:
                rook_from = (
                    ("h1" if to_col == 6 else "a1")
                    if piece.color == Color.WHITE
                    else ("h8" if to_col == 6 else "a8")
                )
                rook_to = (
                    ("f1" if to_col == 6 else "d1")
                    if piece.color == Color.WHITE
                    else ("f8" if to_col == 6 else "d8")
                )
                rook_from_row, rook_from_col = self._pos_to_coords(rook_from)
                rook_to_row, rook_to_col = self._pos_to_coords(rook_to)
                self.board[rook_to_row][rook_to_col] = self.board[rook_from_row][rook_from_col]
                self.board[rook_from_row][rook_from_col] = Square()
        elif original_type == PieceType.ROOK:
            self._revoke_rook_right(from_pos)
        if was_en_passant:
            self.board[from_row][to_col] = Square()
            captured_type = "p"
        self.en_passant_target = None
        if original_type == PieceType.PAWN and abs(to_row - from_row) == 2:
            self.en_passant_target = self._coords_to_pos((from_row + to_row) // 2, to_col)
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = Square()
        if original_type == PieceType.PAWN and to_row in (0, 7):
            piece.piece_type = PROMOTION_TYPES[promotion]
        self.halfmove_clock = (
            0 if original_type == PieceType.PAWN or captured_type else self.halfmove_clock + 1
        )
        if piece.color == Color.BLACK:
            self.fullmove_number += 1
        self.move_history.append(
            {
                "from": from_pos,
                "to": to_pos,
                "piece": original_type.value,
                "captured": captured_type,
                "promotion": promotion,
            }
        )
        self.current_player = Color.BLACK if self.current_player == Color.WHITE else Color.WHITE

    def clone(self):
        clone = ChessGame()
        clone.load_from_fen(self.to_fen())
        clone.move_history = list(self.move_history)
        return clone

    def move(self, from_pos: str, to_pos: str, promotion: str | None = None) -> bool:
        if not self._is_move_valid(from_pos, to_pos, promotion=promotion):
            return False
        self._apply_move(from_pos, to_pos, promotion)
        return True

    def get_board_state(self) -> list[list[dict | None]]:
        return [
            [
                (
                    None
                    if piece.is_empty()
                    else {"type": piece.piece_type.value, "color": piece.color.value}
                )
                for piece in row
            ]
            for row in self.board
        ]

    def get_possible_moves(self, pos: str) -> list[str]:
        self._pos_to_coords(pos)
        piece = self._get_piece_at(pos)
        if piece.is_empty() or piece.color != self.current_player:
            return []
        result = []
        for row in range(8):
            for col in range(8):
                target = self._coords_to_pos(row, col)
                promotions = (
                    PROMOTION_TYPES
                    if piece.piece_type == PieceType.PAWN and row in (0, 7)
                    else {None: None}
                )
                if any(
                    self._is_move_valid(pos, target, promotion=promotion)
                    for promotion in promotions
                ):
                    result.append(target)
        return result

    def get_game_status(self) -> dict:
        in_check = self._is_in_check(self.current_player)
        return {
            "board": self.get_board_state(),
            "current_player": self.current_player.value,
            "in_check": in_check,
            "is_checkmate": self.is_checkmate(self.current_player),
            "is_stalemate": self.is_stalemate(self.current_player),
            "move_history": self.move_history,
            "halfmove_clock": self.halfmove_clock,
            "fullmove_number": self.fullmove_number,
            "fen": self.to_fen(),
            "castling_rights": self._castling_rights_string(),
            "en_passant_target": self.en_passant_target,
        }

    def _castling_rights_string(self):
        return "".join(right for right in CASTLING_RIGHTS if right in self.castling_rights) or "-"

    def load_from_fen(self, fen: str):
        if not isinstance(fen, str):
            raise InvalidFenError("FEN must be a string")
        fields = fen.split()
        if len(fields) != 6:
            raise InvalidFenError("FEN must contain six fields")
        board_fen, active, rights, en_passant, halfmove, fullmove = fields
        invalid_rights = rights != "-" and (
            not rights
            or any(char not in CASTLING_RIGHTS for char in rights)
            or len(set(rights)) != len(rights)
        )
        if active not in {"w", "b"} or invalid_rights:
            raise InvalidFenError("invalid FEN metadata")
        if en_passant != "-" and not re.fullmatch(r"[a-h][36]", en_passant):
            raise InvalidFenError("invalid en passant target")
        if (
            not halfmove.isdigit()
            or not fullmove.isdigit()
            or int(halfmove) < 0
            or int(fullmove) < 1
        ):
            raise InvalidFenError("invalid FEN counters")
        rows = board_fen.split("/")
        if len(rows) != 8:
            raise InvalidFenError("FEN board must contain eight ranks")
        board = [[Square() for _ in range(8)] for _ in range(8)]
        piece_map = {piece.value: piece for piece in PieceType}
        king_count = {Color.WHITE: 0, Color.BLACK: 0}
        for row_index, row_fen in enumerate(rows):
            col = 0
            for char in row_fen:
                if char.isdigit() and char in "12345678":
                    col += int(char)
                elif char.lower() in piece_map and char.isalpha():
                    if col >= 8:
                        raise InvalidFenError("rank contains too many squares")
                    color = Color.WHITE if char.isupper() else Color.BLACK
                    piece = piece_map[char.lower()]
                    board[row_index][col] = Square(piece, color)
                    if piece == PieceType.KING:
                        king_count[color] += 1
                    col += 1
                else:
                    raise InvalidFenError("invalid FEN piece")
            if col != 8:
                raise InvalidFenError("rank does not contain eight squares")
        if king_count[Color.WHITE] != 1 or king_count[Color.BLACK] != 1:
            raise InvalidFenError("FEN must contain one king per color")
        self.board = board
        self.current_player = Color.WHITE if active == "w" else Color.BLACK
        self.castling_rights = set() if rights == "-" else set(rights)
        self.en_passant_target = None if en_passant == "-" else en_passant
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)
        self.move_history = []
        self.captured_pieces = {Color.WHITE: [], Color.BLACK: []}

    def to_fen(self) -> str:
        ranks = []
        for row in self.board:
            rank, empty = "", 0
            for piece in row:
                if piece.is_empty():
                    empty += 1
                    continue
                if empty:
                    rank += str(empty)
                    empty = 0
                value = piece.piece_type.value
                rank += value.upper() if piece.color == Color.WHITE else value
            if empty:
                rank += str(empty)
            ranks.append(rank)
        return f"{'/'.join(ranks)} {'w' if self.current_player == Color.WHITE else 'b'} {self._castling_rights_string()} {self.en_passant_target or '-'} {self.halfmove_clock} {self.fullmove_number}"
