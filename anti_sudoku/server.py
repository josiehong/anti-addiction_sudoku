"""
FastAPI web server.

Run with:
    anti-sudoku serve
or directly:
    uvicorn anti_sudoku.server:app --reload
"""

import pathlib
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .solver.pipeline import solve as pipeline_solve, hint as pipeline_hint, validate as pipeline_validate
from .solver.sudoku_generator import generate as generator_generate

app = FastAPI(
    title="Anti-Addiction Sudoku",
    description="Solve All the Sudoku, Leave No Joy for Solving by Yourself",
)

_WEB_DIR = pathlib.Path(__file__).parent / "web"
_PUZZLES_DIR = pathlib.Path(__file__).parent / "puzzles"


# ─── Serve the frontend ───────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_WEB_DIR / "index.html")


# ─── Request/response models ──────────────────────────────────────────────────

class BoardRequest(BaseModel):
    board: List[int]  # 81 ints, 0 = blank

class ValidateRequest(BaseModel):
    board: List[int]   # current state (81 ints)
    givens: List[int]  # original puzzle (81 ints)


# ─── API endpoints ────────────────────────────────────────────────────────────

@app.post("/solve")
def solve(req: BoardRequest):
    """
    Fully solve the given board.

    Body:  {"board": [81 ints, 0=blank]}
    Reply: {"board": [81 ints], "solved": bool}
    """
    if len(req.board) != 81:
        raise HTTPException(status_code=422, detail="board must have exactly 81 cells")
    return pipeline_solve(req.board)


@app.post("/hint")
def hint(req: BoardRequest):
    """
    Return one hint: the next cell to fill and the technique used.

    Body:  {"board": [81 ints, 0=blank]}
    Reply: {"cell": int, "value": int, "technique": str}
            cell is a flat 0-80 index (row-major order).
    """
    if len(req.board) != 81:
        raise HTTPException(status_code=422, detail="board must have exactly 81 cells")
    result = pipeline_hint(req.board)
    if result is None:
        raise HTTPException(status_code=404, detail="No hint available — board may be complete or unsolvable")
    return result


@app.post("/validate")
def validate(req: ValidateRequest):
    """
    Check the current board for conflicts.

    Body:  {"board": [81 ints], "givens": [81 ints]}
    Reply: {"errors": [int], "complete": bool}
            errors: flat indices of conflicting user-filled cells.
    """
    if len(req.board) != 81 or len(req.givens) != 81:
        raise HTTPException(status_code=422, detail="board and givens must each have 81 cells")
    return pipeline_validate(req.board, req.givens)


@app.get("/puzzle")
def puzzle(difficulty: str = "hard"):
    """
    Generate a random puzzle.

    Query params: difficulty = easy | hard | master | grandmaster
    Reply: {"board": [81 ints], "difficulty": str}
    """
    valid = {"easy", "hard", "master", "grandmaster"}
    if difficulty not in valid:
        raise HTTPException(status_code=422, detail=f"difficulty must be one of {sorted(valid)}")
    board = generator_generate(difficulty=difficulty)
    return {"board": board, "difficulty": difficulty}


@app.get("/puzzles/{name}")
def get_puzzle(name: str):
    """
    Load a built-in puzzle by name (without .txt extension).

    Available: hard_001, master_001, master_002, grandmaster_001
    Reply: {"board": [81 ints], "name": str}
    """
    path = _PUZZLES_DIR / f"{name}.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Puzzle '{name}' not found")

    board = []
    with open(path) as f:
        for line in f:
            for cell in line.split():
                board.append(0 if cell == "-" else int(cell))

    if len(board) != 81:
        raise HTTPException(status_code=500, detail="Invalid puzzle file")

    return {"board": board, "name": name}
