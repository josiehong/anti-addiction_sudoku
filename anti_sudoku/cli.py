"""
CLI entry point for anti-sudoku.

Usage:
    anti-sudoku solve puzzle.txt
    anti-sudoku solve --input "53..7...."
    anti-sudoku generate --difficulty hard
    anti-sudoku serve [--host 127.0.0.1] [--port 8000]
"""

import argparse
import sys
import threading
import pathlib


def main():
    parser = argparse.ArgumentParser(
        prog="anti-sudoku",
        description="Solve All the Sudoku, Leave No Joy for Solving by Yourself",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── solve ──────────────────────────────────────────────────────────────────
    sp = sub.add_parser("solve", help="Solve a Sudoku puzzle")
    sp.add_argument("file", nargs="?", help="Path to puzzle .txt file")
    sp.add_argument("--input", metavar="STRING",
                    help="Puzzle as 81-char string (dots or dashes = blank)")

    # ── generate ───────────────────────────────────────────────────────────────
    gp = sub.add_parser("generate", help="Generate a new Sudoku puzzle")
    gp.add_argument("--difficulty", choices=["easy", "hard", "master", "grandmaster"],
                    default="hard")
    gp.add_argument("--seed", type=int, help="Random seed for reproducible output")

    # ── serve ──────────────────────────────────────────────────────────────────
    wp = sub.add_parser("serve", help="Start the web UI")
    wp.add_argument("--host", default="127.0.0.1")
    wp.add_argument("--port", type=int, default=8000)
    wp.add_argument("--no-browser", action="store_true",
                    help="Don't open the browser automatically")

    args = parser.parse_args()

    if args.command == "solve":
        _cmd_solve(args)
    elif args.command == "generate":
        _cmd_generate(args)
    elif args.command == "serve":
        _cmd_serve(args)
    else:
        parser.print_help()


# ─── solve ────────────────────────────────────────────────────────────────────

def _load_board_from_file(path):
    with open(path) as f:
        data = f.read()
    board = []
    for ch in data.replace("\n", " ").split():
        if ch == "-":
            board.append(0)
        elif ch.isdigit():
            board.append(int(ch))
    return board


def _load_board_from_string(s):
    board = []
    for ch in s:
        if ch in ".-_":
            board.append(0)
        elif ch.isdigit():
            board.append(int(ch))
    return board


def _cmd_solve(args):
    from .solver.pipeline import solve

    if args.file:
        board = _load_board_from_file(args.file)
    elif args.input:
        board = _load_board_from_string(args.input)
    else:
        print("Error: provide a file path or --input STRING", file=sys.stderr)
        sys.exit(1)

    if len(board) != 81:
        print(f"Error: expected 81 cells, got {len(board)}", file=sys.stderr)
        sys.exit(1)

    print("Puzzle:")
    _print_board(board)

    result = solve(board)
    if result["solved"]:
        print("\nSolution:")
        _print_board(result["board"])
    else:
        print("\nNo solution found — check your input.", file=sys.stderr)
        sys.exit(1)


# ─── generate ─────────────────────────────────────────────────────────────────

def _cmd_generate(args):
    from .solver.sudoku_generator import generate

    print(f"Generating {args.difficulty} puzzle…")
    board = generate(difficulty=args.difficulty, seed=args.seed)
    _print_board(board)

    given_count = sum(1 for v in board if v != 0)
    print(f"\n{given_count} given cells  |  difficulty: {args.difficulty}")
    if args.seed is not None:
        print(f"Seed: {args.seed}")


# ─── serve ────────────────────────────────────────────────────────────────────

def _cmd_serve(args):
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required for 'serve'. Install it with:\n"
              "    pip install uvicorn[standard]", file=sys.stderr)
        sys.exit(1)

    from .server import app

    url = f"http://{args.host}:{args.port}"

    if not args.no_browser:
        def _open():
            import time, webbrowser
            time.sleep(1)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    print(f"Anti-Addiction Sudoku → {url}")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host=args.host, port=args.port)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _print_board(board):
    for r in range(9):
        row = board[r * 9 : (r + 1) * 9]
        cells = [str(v) if v != 0 else "." for v in row]
        line = " ".join(cells[:3]) + " | " + " ".join(cells[3:6]) + " | " + " ".join(cells[6:])
        print(line)
        if r in (2, 5):
            print("------+-------+------")
