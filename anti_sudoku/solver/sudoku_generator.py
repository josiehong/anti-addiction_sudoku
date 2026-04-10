"""
Sudoku puzzle generator.

Strategy: generate-and-remove with uniqueness guarantee.
  1. Fill the three diagonal 3×3 blocks randomly (they are mutually independent).
  2. Solve the rest with backtracking → complete valid board.
  3. Remove clues one at a time in random order; restore any clue whose removal
     would create more than one solution.
  4. Stop when the target number of givens is reached.
"""

import random
import sys
from .pipeline import init_candidates, _backtrack, _coords, _peers

sys.setrecursionlimit(15000)


# Difficulty → target number of given (filled) cells
_DIFFICULTY_GIVENS = {
    "easy":        40,
    "hard":        30,
    "master":      26,
    "grandmaster": 23,
}


def _fill_block(board, b):
    """Fill block b with a random permutation of 1-9."""
    r0, c0 = (b // 3) * 3, (b % 3) * 3
    cells = [r0 * 9 + dr * 9 + c0 + dc for dr in range(3) for dc in range(3)]
    digits = list(range(1, 10))
    random.shuffle(digits)
    for cell, digit in zip(cells, digits):
        board[cell] = digit


def _random_full_board():
    """Return a randomly generated complete valid Sudoku board, or None on failure."""
    board = [0] * 81
    # Fill diagonal blocks first — they share no peers with each other
    for b in (0, 4, 8):
        _fill_block(board, b)
    # Solve the remaining cells with backtracking
    candidates = init_candidates(board)
    return _backtrack(board, candidates)


def _count_solutions(board, candidates, limit=2):
    """
    Count solutions up to `limit` (stops early for efficiency).
    Used to verify uniqueness: if count >= 2, the puzzle is ambiguous.
    """
    if not candidates:
        return 1

    idx = min(candidates, key=lambda k: len(candidates[k]))

    count = 0
    for val in sorted(candidates[idx]):
        new_board = board[:]
        new_board[idx] = val
        new_cands = {k: set(v) for k, v in candidates.items()}
        del new_cands[idx]

        valid = True
        for peer in _peers(idx):
            if peer in new_cands:
                new_cands[peer].discard(val)
                if not new_cands[peer]:
                    valid = False
                    break
        if not valid:
            continue

        count += _count_solutions(new_board, new_cands, limit)
        if count >= limit:
            return count

    return count


def generate(difficulty="hard", seed=None):
    """
    Generate a Sudoku puzzle with a unique solution.

    Args:
        difficulty: "easy", "hard", "master", or "grandmaster"
        seed:       optional int for reproducible output

    Returns:
        list of 81 ints, 0 = blank.
    """
    if seed is not None:
        random.seed(seed)

    target_givens = _DIFFICULTY_GIVENS.get(difficulty, 30)

    while True:
        full = _random_full_board()
        if full is None:
            continue  # rare backtracking failure; retry

        board = full[:]
        positions = list(range(81))
        random.shuffle(positions)

        for pos in positions:
            if board.count(0) >= 81 - target_givens:
                break  # reached target blank count
            saved = board[pos]
            board[pos] = 0
            cands = init_candidates(board)
            if _count_solutions(board, cands, limit=2) != 1:
                board[pos] = saved  # removal broke uniqueness; restore

        return board
