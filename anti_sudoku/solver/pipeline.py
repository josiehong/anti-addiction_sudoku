"""
Unified Sudoku solver pipeline.

Board format throughout this module: list of 81 ints, 0 = blank, 1-9 = filled.

Technique order (weakest → strongest):
  1. Naked Singles       — cell with exactly 1 candidate
  2. Hidden Singles      — digit with only 1 position in a group
  3. Naked Pairs/Triples — N cells sharing N candidates; eliminate from rest of group
  4. Hidden Pairs/Triples— N digits confined to N cells; eliminate others from those cells
  5. Pointing Pairs      — digit in block confined to 1 row/col; eliminate outside block
  6. X-Wing             — digit in 2 rows sharing 2 cols; eliminate from those cols
  7. Swordfish           — X-Wing generalized to 3 rows/cols
  8. Backtracking        — brute-force with MRV heuristic (last resort)
"""

import sys
import copy
from itertools import combinations

sys.setrecursionlimit(15000)


# ─── Index helpers ────────────────────────────────────────────────────────────

def _row_indexes(r):
    return [r * 9 + c for c in range(9)]

def _col_indexes(c):
    return [r * 9 + c for r in range(9)]

def _block_indexes(b):
    r0, c0 = (b // 3) * 3, (b % 3) * 3
    return [r0 * 9 + dr * 9 + c0 + dc for dr in range(3) for dc in range(3)]

def _coords(idx):
    r = idx // 9
    c = idx % 9
    b = (r // 3) * 3 + (c // 3)
    return r, c, b

def _peers(idx):
    r, c, b = _coords(idx)
    return set(_row_indexes(r) + _col_indexes(c) + _block_indexes(b)) - {idx}

_GROUPS = (
    [("row", i, _row_indexes(i)) for i in range(9)]
    + [("col", i, _col_indexes(i)) for i in range(9)]
    + [("block", i, _block_indexes(i)) for i in range(9)]
)


# ─── Candidate management ─────────────────────────────────────────────────────

def init_candidates(board):
    """Return {cell_idx: set_of_candidates} for all blank cells."""
    candidates = {}
    for idx, val in enumerate(board):
        if val == 0:
            r, c, b = _coords(idx)
            used = set()
            for peer in _row_indexes(r) + _col_indexes(c) + _block_indexes(b):
                if board[peer] != 0:
                    used.add(board[peer])
            candidates[idx] = set(range(1, 10)) - used
    return candidates


def _propagate(candidates, idx, val):
    """Remove val from peers of idx. Return False if a peer's candidates become empty."""
    for peer in _peers(idx):
        if peer in candidates:
            candidates[peer].discard(val)
            if not candidates[peer]:
                return False
    return True


# ─── Fill singles loop ────────────────────────────────────────────────────────

def _fill_singles(board, candidates):
    """
    Repeatedly fill naked and hidden singles until none remain.
    Mutates board and candidates in place.
    Returns False on contradiction, True otherwise.
    """
    while candidates:
        made_progress = False

        # Naked singles: any cell with exactly 1 candidate
        for idx in list(candidates.keys()):
            cands = candidates.get(idx)
            if cands is None or len(cands) != 1:
                continue
            val = next(iter(cands))
            board[idx] = val
            del candidates[idx]
            if not _propagate(candidates, idx, val):
                return False
            made_progress = True

        if made_progress:
            continue  # restart; propagation may have created more naked singles

        # Hidden singles: digit with only 1 possible position in a group
        found = False
        for _, _, indexes in _GROUPS:
            blank = [i for i in indexes if i in candidates]
            for d in range(1, 10):
                positions = [i for i in blank if d in candidates[i]]
                if len(positions) == 1:
                    idx = positions[0]
                    if idx not in candidates:
                        continue  # already filled by another group in this pass
                    board[idx] = d
                    del candidates[idx]
                    if not _propagate(candidates, idx, d):
                        return False
                    found = True
                    break
            if found:
                break

        if not found:
            break  # no singles remain

    return True


# ─── Elimination techniques ───────────────────────────────────────────────────

def _apply_naked_sets(candidates):
    """Naked pairs/triples: N cells in a group with exactly N candidates total.
    Eliminate those candidates from the rest of the group. Returns True if changed."""
    changed = False
    for _, _, indexes in _GROUPS:
        blank = [i for i in indexes if i in candidates]
        for n in (2, 3):
            for combo in combinations(blank, n):
                union = set()
                for i in combo:
                    union |= candidates[i]
                if len(union) == n:
                    for i in blank:
                        if i not in combo:
                            before = len(candidates[i])
                            candidates[i] -= union
                            if len(candidates[i]) < before:
                                changed = True
    return changed


def _apply_hidden_sets(candidates):
    """Hidden pairs/triples: N digits that only appear in N cells in a group.
    Eliminate all other candidates from those cells. Returns True if changed."""
    changed = False
    for _, _, indexes in _GROUPS:
        blank = [i for i in indexes if i in candidates]
        digit_positions = {}
        for d in range(1, 10):
            pos = tuple(i for i in blank if d in candidates[i])
            if 2 <= len(pos) <= 3:
                digit_positions[d] = pos
        for n in (2, 3):
            for digits in combinations(digit_positions, n):
                cells = set()
                for d in digits:
                    cells |= set(digit_positions[d])
                if len(cells) == n:
                    keep = set(digits)
                    for i in cells:
                        before = len(candidates[i])
                        candidates[i] &= keep
                        if len(candidates[i]) < before:
                            changed = True
    return changed


def _apply_omission(candidates):
    """Pointing pairs / box-line reduction. Returns True if changed."""
    changed = False

    # Box → line: digit in block confined to one row or col
    for b in range(9):
        block = _block_indexes(b)
        blank_in_block = [i for i in block if i in candidates]
        for d in range(1, 10):
            positions = [i for i in blank_in_block if d in candidates[i]]
            if len(positions) < 2:
                continue
            rows = {_coords(i)[0] for i in positions}
            cols = {_coords(i)[1] for i in positions}
            if len(rows) == 1:
                for i in _row_indexes(rows.pop()):
                    if i not in block and i in candidates and d in candidates[i]:
                        candidates[i].discard(d)
                        changed = True
            if len(cols) == 1:
                for i in _col_indexes(cols.pop()):
                    if i not in block and i in candidates and d in candidates[i]:
                        candidates[i].discard(d)
                        changed = True

    # Line → box: digit in a row/col confined to one block
    for i in range(9):
        for group in (_row_indexes(i), _col_indexes(i)):
            blank = [j for j in group if j in candidates]
            for d in range(1, 10):
                positions = [j for j in blank if d in candidates[j]]
                if len(positions) < 2:
                    continue
                blocks = {_coords(j)[2] for j in positions}
                if len(blocks) == 1:
                    for j in _block_indexes(blocks.pop()):
                        if j not in group and j in candidates and d in candidates[j]:
                            candidates[j].discard(d)
                            changed = True

    return changed


def _apply_xwing(candidates):
    """X-Wing: digit in exactly 2 cells in each of 2 rows sharing the same 2 columns
    (or column analogue). Eliminate from the rest of those columns (rows). Returns True if changed."""
    changed = False
    for d in range(1, 10):
        # Rows → eliminate from columns
        row_cols = {}
        for r in range(9):
            cols = tuple(sorted(_coords(i)[1] for i in _row_indexes(r) if i in candidates and d in candidates[i]))
            if len(cols) == 2:
                row_cols[r] = cols
        for r1, r2 in combinations(row_cols, 2):
            if row_cols[r1] == row_cols[r2]:
                c1, c2 = row_cols[r1]
                for i in _col_indexes(c1) + _col_indexes(c2):
                    if _coords(i)[0] not in (r1, r2) and i in candidates and d in candidates[i]:
                        candidates[i].discard(d)
                        changed = True

        # Columns → eliminate from rows
        col_rows = {}
        for c in range(9):
            rows = tuple(sorted(_coords(i)[0] for i in _col_indexes(c) if i in candidates and d in candidates[i]))
            if len(rows) == 2:
                col_rows[c] = rows
        for c1, c2 in combinations(col_rows, 2):
            if col_rows[c1] == col_rows[c2]:
                r1, r2 = col_rows[c1]
                for i in _row_indexes(r1) + _row_indexes(r2):
                    if _coords(i)[1] not in (c1, c2) and i in candidates and d in candidates[i]:
                        candidates[i].discard(d)
                        changed = True

    return changed


def _apply_swordfish(candidates):
    """Swordfish: X-Wing generalized to 3 rows/columns. Returns True if changed."""
    changed = False
    for d in range(1, 10):
        # Rows → eliminate from columns
        row_cols = {}
        for r in range(9):
            cols = frozenset(_coords(i)[1] for i in _row_indexes(r) if i in candidates and d in candidates[i])
            if 2 <= len(cols) <= 3:
                row_cols[r] = cols
        for r1, r2, r3 in combinations(row_cols, 3):
            cols_union = row_cols[r1] | row_cols[r2] | row_cols[r3]
            if len(cols_union) == 3:
                for c in cols_union:
                    for i in _col_indexes(c):
                        if _coords(i)[0] not in (r1, r2, r3) and i in candidates and d in candidates[i]:
                            candidates[i].discard(d)
                            changed = True

        # Columns → eliminate from rows
        col_rows = {}
        for c in range(9):
            rows = frozenset(_coords(i)[0] for i in _col_indexes(c) if i in candidates and d in candidates[i])
            if 2 <= len(rows) <= 3:
                col_rows[c] = rows
        for c1, c2, c3 in combinations(col_rows, 3):
            rows_union = col_rows[c1] | col_rows[c2] | col_rows[c3]
            if len(rows_union) == 3:
                for r in rows_union:
                    for i in _row_indexes(r):
                        if _coords(i)[1] not in (c1, c2, c3) and i in candidates and d in candidates[i]:
                            candidates[i].discard(d)
                            changed = True

    return changed


# ─── Backtracking ─────────────────────────────────────────────────────────────

def _backtrack(board, candidates):
    """Recursive backtracking with MRV heuristic. Returns solved board or None."""
    if not candidates:
        return board

    # Pick cell with fewest candidates (MRV)
    idx = min(candidates, key=lambda k: len(candidates[k]))

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

        result = _backtrack(new_board, new_cands)
        if result is not None:
            return result

    return None


# ─── Public API ───────────────────────────────────────────────────────────────

_ELIM_TECHNIQUES = [
    (_apply_naked_sets,  "Naked Pairs/Triples"),
    (_apply_hidden_sets, "Hidden Pairs/Triples"),
    (_apply_omission,    "Pointing Pairs"),
    (_apply_xwing,       "X-Wing"),
    (_apply_swordfish,   "Swordfish"),
]


def solve(board):
    """
    Solve a Sudoku puzzle.

    Args:
        board: list of 81 ints, 0 = blank.

    Returns:
        {"board": list[int], "solved": bool}
    """
    board = list(board)
    candidates = init_candidates(board)

    if not _fill_singles(board, candidates):
        return {"board": board, "solved": False}

    # Repeatedly apply elimination techniques then fill singles
    progress = True
    while progress and candidates:
        progress = False
        for tech_fn, _ in _ELIM_TECHNIQUES:
            if tech_fn(candidates):
                progress = True
                if not _fill_singles(board, candidates):
                    return {"board": board, "solved": False}
                break  # restart from weakest technique

    if candidates:
        # Fall back to backtracking
        result = _backtrack(board[:], {k: set(v) for k, v in candidates.items()})
        if result is None:
            return {"board": board, "solved": False}
        return {"board": result, "solved": True}

    return {"board": board, "solved": True}


def hint(board):
    """
    Return the next deducible cell with the technique that found it.

    Args:
        board: list of 81 ints, 0 = blank.

    Returns:
        {"cell": int, "value": int, "technique": str} or None if board is complete/unsolvable.
        cell is a flat index 0-80 (row-major).
    """
    board = list(board)
    candidates = init_candidates(board)

    if not candidates:
        return None  # already complete

    def first_single():
        for idx, cands in candidates.items():
            if len(cands) == 1:
                return idx, next(iter(cands)), "Naked Single"
        for _, _, indexes in _GROUPS:
            blank = [i for i in indexes if i in candidates]
            for d in range(1, 10):
                positions = [i for i in blank if d in candidates[i]]
                if len(positions) == 1:
                    return positions[0], d, "Hidden Single"
        return None

    # Direct fill without any elimination
    result = first_single()
    if result:
        return {"cell": result[0], "value": result[1], "technique": result[2]}

    # Try elimination techniques; return the first fill they enable
    for tech_fn, tech_name in _ELIM_TECHNIQUES:
        if tech_fn(candidates):
            result = first_single()
            if result:
                return {"cell": result[0], "value": result[1], "technique": tech_name}

    # Need backtracking — pick most-constrained blank cell
    solved = _backtrack(board[:], {k: set(v) for k, v in candidates.items()})
    if solved is not None:
        idx = min(candidates, key=lambda k: len(candidates[k]))
        return {"cell": idx, "value": solved[idx], "technique": "Backtracking"}

    return None  # no solution exists


def validate(board, givens):
    """
    Check the current board state for conflicts.

    Args:
        board:  current board (81 ints, 0 = blank)
        givens: original puzzle  (81 ints, 0 = blank)

    Returns:
        {"errors": list[int], "complete": bool}
        errors: flat indices of conflicting user-entered cells.
        complete: True when all cells filled with no errors.
    """
    errors = []
    for idx in range(81):
        val = board[idx]
        if val == 0 or givens[idx] != 0:
            continue  # skip blank cells and givens
        r, c, b = _coords(idx)
        conflict = False
        for group in (_row_indexes(r), _col_indexes(c), _block_indexes(b)):
            for peer in group:
                if peer != idx and board[peer] == val:
                    conflict = True
                    break
            if conflict:
                break
        if conflict:
            errors.append(idx)

    complete = (0 not in board) and not errors
    return {"errors": errors, "complete": complete}
