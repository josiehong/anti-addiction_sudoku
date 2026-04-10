"""
anti-sudoku: Solve All the Sudoku, Leave No Joy for Solving by Yourself.

Public API:
    solve(board)    → solved board string or list
    hint(board)     → {"row", "col", "value", "technique"} or None
    generate(...)   → puzzle string

Board input can be:
  - str of 81 chars: digits 1-9 for given cells, '.' or '0' for blanks
  - list of 81 ints: 0 for blank, 1-9 for given/filled cells
"""

from .solver.pipeline import (
    solve as _solve,
    hint as _hint,
    validate as _validate,
)
from .solver.sudoku_generator import generate as _generate

__version__ = "0.1.0"
__all__ = ["solve", "hint", "generate", "validate"]


def _parse(board_input):
    if isinstance(board_input, str):
        board = []
        for ch in board_input:
            if ch in ".-_":
                board.append(0)
            elif ch.isdigit():
                board.append(int(ch))
        return board
    return list(board_input)


def solve(board_input):
    """
    Solve a Sudoku puzzle.

    Args:
        board_input: 81-char string (dots = blank) **or** list of 81 ints (0 = blank).

    Returns:
        Same type as input, with all cells filled. Returns None if unsolvable.

    Example:
        >>> solve("53..7....")   # 81-char string
        "534678912..."
    """
    board = _parse(board_input)
    result = _solve(board)
    if not result["solved"]:
        return None
    if isinstance(board_input, str):
        return "".join(str(v) for v in result["board"])
    return result["board"]


def hint(board_input):
    """
    Get one hint: the next cell that can be determined and the technique used.

    Args:
        board_input: 81-char string or list of 81 ints.

    Returns:
        {"row": int, "col": int, "value": int, "technique": str}
        or None if the board is already complete / unsolvable.

    Example:
        >>> hint("53..7....")
        {"row": 0, "col": 3, "value": 6, "technique": "Hidden Single"}
    """
    board = _parse(board_input)
    result = _hint(board)
    if result is None:
        return None
    r, c = divmod(result["cell"], 9)
    return {"row": r, "col": c, "value": result["value"], "technique": result["technique"]}


def generate(difficulty="hard", seed=None):
    """
    Generate a Sudoku puzzle with a unique solution.

    Args:
        difficulty: "easy", "hard", "master", or "grandmaster"
        seed:       optional int for reproducible output

    Returns:
        81-char string where '.' marks blank cells.

    Example:
        >>> puzzle = generate(difficulty="hard")
        >>> len(puzzle)
        81
    """
    board = _generate(difficulty=difficulty, seed=seed)
    return "".join("." if v == 0 else str(v) for v in board)


def validate(board_input, givens_input):
    """
    Check a (partially) filled board for conflicts.

    Args:
        board_input:  current state (81-char string or list of 81 ints)
        givens_input: original puzzle (same format)

    Returns:
        {"errors": list[int], "complete": bool}
        errors: flat 0-80 indices of conflicting user-filled cells.
    """
    return _validate(_parse(board_input), _parse(givens_input))
