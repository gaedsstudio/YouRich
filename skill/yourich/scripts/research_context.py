import argparse

from _core import ToolError, write_json
from _research import build_research_context, parse_research_request
from _research_types import RESEARCH_MODES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--mode", choices=RESEARCH_MODES, default="thesis")
    parser.add_argument("--limit", default=2, type=int)
    parser.add_argument("--evidence-limit", default=12, type=int)
    args = parser.parse_args()
    try:
        request = parse_research_request(args.ticker, args.mode, args.limit, args.evidence_limit)
        write_json(build_research_context(request))
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
