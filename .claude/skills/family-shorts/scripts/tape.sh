# Sourced by the other scripts: reads <tape-dir>/plan/tape.json into shell variables.
#   TAPE_DIR SRC OUT_DIR CHANNEL
TAPE_DIR="$(cd "$1" && pwd)"
_tj() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$TAPE_DIR/plan/tape.json" "$1"; }
SRC="$(_tj source)"; OUT_DIR="$(_tj out_dir)"; CHANNEL="$(_tj channel)"
[ -f "$SRC" ] || { echo "source not found: $SRC" >&2; exit 1; }
