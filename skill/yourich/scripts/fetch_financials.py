import sys

from _core import ToolError, write_json
from _sec import fetch_financials


def main() -> int:
    args = [arg for arg in sys.argv[1:] if arg != "--debug"]
    ticker = args[0] if args else ""
    try:
        write_json(fetch_financials(ticker, debug="--debug" in sys.argv[1:]))
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
