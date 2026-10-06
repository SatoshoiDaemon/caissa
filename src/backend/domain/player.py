from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    name: str
    color: str
    token_hash: str
