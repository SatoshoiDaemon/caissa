import re

from .chess_game import ChessGame, ChessStateError

RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}
ELLIPSIS = "." * 3
TAG_PATTERN = re.compile(r'^\[([A-Za-z0-9_]+)\s+"((?:[^"\\]|\\.)*)"\]\s*$')
MOVE_NUMBER_PATTERN = re.compile(r"^\d+\.(\.\.)?$")


class InvalidPgnError(ChessStateError):
    """Raised when a PGN cannot be parsed or replayed legally."""


def _unescape_tag(value):
    return value.replace('\\"', '"').replace("\\\\", "\\")


def parse_pgn(pgn: str):
    if not isinstance(pgn, str) or not pgn.strip():
        raise InvalidPgnError("PGN must be a non-empty string")
    tags = {}
    movetext = []
    in_tags = True
    for line in pgn.splitlines():
        match = TAG_PATTERN.match(line.strip())
        if match and in_tags:
            tags[match.group(1)] = _unescape_tag(match.group(2))
            continue
        if line.strip() and not line.lstrip().startswith(";"):
            in_tags = False
            movetext.append(line)

    text = "\n".join(movetext)
    text = re.sub(r"\{[^}]*\}", " ", text, flags=re.DOTALL)
    text = re.sub(r";[^\n]*", " ", text)
    text = re.sub(r"\([^()]*\)", " ", text)
    text = re.sub(r"\$\d+", " ", text)
    tokens = []
    for token in text.split():
        if MOVE_NUMBER_PATTERN.fullmatch(token) or token == ELLIPSIS:
            continue
        tokens.append(token)
    result = tags.get("Result", "*")
    if tokens and tokens[-1] in RESULTS:
        result = tokens.pop()
    if result not in RESULTS:
        raise InvalidPgnError("invalid PGN result")
    return tags, tokens, result


def _find_san_move(game, san):
    normalized = san.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    matches = []
    for row in range(8):
        for col in range(8):
            source = game._coords_to_pos(row, col)
            piece = game.board[row][col]
            if piece.color != game.current_player:
                continue
            for target_row in range(8):
                for target_col in range(8):
                    target = game._coords_to_pos(target_row, target_col)
                    promotions = (
                        ("q", "r", "b", "n")
                        if piece.piece_type.value == "p" and target_row in (0, 7)
                        else (None,)
                    )
                    for promotion in promotions:
                        try:
                            if game.san_for_move(source, target, promotion) == normalized:
                                matches.append((source, target, promotion))
                        except ChessStateError:
                            continue
    if len(matches) != 1:
        raise InvalidPgnError(f"invalid or ambiguous SAN move: {san}")
    return matches[0]


def import_pgn(pgn: str):
    tags, tokens, result = parse_pgn(pgn)
    game = ChessGame()
    if tags.get("SetUp") == "1":
        if not tags.get("FEN"):
            raise InvalidPgnError("PGN SetUp tag requires a FEN tag")
        try:
            game.load_from_fen(tags["FEN"])
        except ChessStateError as error:
            raise InvalidPgnError(str(error)) from error
    for token in tokens:
        try:
            move = _find_san_move(game, token)
            if not game.move(*move):
                raise InvalidPgnError(f"invalid SAN move: {token}")
        except ChessStateError as error:
            raise InvalidPgnError(str(error)) from error
    return game, tags, result


def _result_marker(document):
    if document.get("pgn_result") in RESULTS:
        return document["pgn_result"]
    status = document.get("status", "active")
    winner = document.get("winner")
    if status == "checkmate" and winner == "white":
        return "1-0"
    if status == "checkmate" and winner == "black":
        return "0-1"
    if status in {"draw", "stalemate", "resignation", "timeout", "abandonment"}:
        if status == "resignation" and winner == "white":
            return "1-0"
        if status == "resignation" and winner == "black":
            return "0-1"
        if status == "timeout" and winner == "white":
            return "1-0"
        if status == "timeout" and winner == "black":
            return "0-1"
        return "1/2-1/2"
    return "*"


def export_pgn(document):
    initial_fen = document.get("initial_fen")
    game = ChessGame()
    if initial_fen:
        game.load_from_fen(initial_fen)
    for move in document.get("move_history", []):
        if not game.move(move["from"], move["to"], move.get("promotion")):
            raise InvalidPgnError("stored move history is invalid")
    headers = dict(document.get("pgn_headers") or {})
    headers.setdefault("Event", "Caissa game")
    headers.setdefault("Site", "Caissa")
    headers.setdefault("White", document.get("white", {}).get("name", "White"))
    headers.setdefault("Black", (document.get("black") or {}).get("name", "Black"))
    headers["Result"] = _result_marker(document)
    if initial_fen and initial_fen != ChessGame().to_fen():
        headers.update({"SetUp": "1", "FEN": initial_fen})
    lines = [f'[{key} "{value}"]' for key, value in headers.items()]
    lines.append("")
    san_moves = [move.get("san") for move in document.get("move_history", [])]
    if not all(san_moves):
        san_moves = []
        replay = ChessGame()
        if initial_fen:
            replay.load_from_fen(initial_fen)
        for move in document.get("move_history", []):
            san = replay.san_for_move(move["from"], move["to"], move.get("promotion"))
            replay.move(move["from"], move["to"], move.get("promotion"))
            san_moves.append(san)
    numbered = []
    move_number = 1 if initial_fen is None else int(initial_fen.split()[5])
    active_white = initial_fen is None or " w " in initial_fen
    for index, san in enumerate(san_moves):
        if active_white:
            numbered.extend((f"{move_number}.", san))
            active_white = False
        else:
            if index == 0:
                numbered.append(f"{move_number}...")
            numbered.append(san)
            move_number += 1
            active_white = True
    numbered.append(headers["Result"])
    lines.append(" ".join(numbered))
    return "\n".join(lines) + "\n"
