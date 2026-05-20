"""Phase 6: produce a sample engine-vs-RandomPlayer result line for the report."""

from __future__ import annotations

from dialectical_checkers.match import EnginePlayer, RandomPlayer, play_game


def main() -> None:
    result = play_game(EnginePlayer(), RandomPlayer(seed=42))
    print(
        f"DialecticalEngine (Red) vs RandomPlayer (White): "
        f"outcome={result.outcome} reason={result.reason} "
        f"plies={result.ply_count}"
    )
    print(f"first 6 moves: {[m.pdn() for m in result.moves[:6]]}")
    print(f"final FEN: {result.positions[-1].to_fen()}")


if __name__ == "__main__":
    main()
