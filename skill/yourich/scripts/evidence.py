from _core import write_json
from _evidence import CONTRADICTED, INSUFFICIENT_EVIDENCE, PARTIALLY_SUPPORTED, SUPPORTED


def main() -> int:
    write_json(
        {
            "research_claim_statuses": [
                SUPPORTED,
                PARTIALLY_SUPPORTED,
                CONTRADICTED,
                INSUFFICIENT_EVIDENCE,
            ],
            "rule": "Claim -> Evidence -> Interpretation",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
