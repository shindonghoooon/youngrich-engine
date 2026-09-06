"""Manual deterministic onboarding from an explicitly supplied normalized artifact."""
import argparse
import json
from pathlib import Path

from engine.persistence.session import create_session_factory
from engine.stock_onboarding import OnboardingInput, StockOnboardingService
from research.watchlist import existing_engine


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("analyze",))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--track", action="store_true")
    args = parser.parse_args(argv)
    try:
        inputs = OnboardingInput.model_validate_json(args.input.read_text(encoding="utf-8"))
        engine = existing_engine(args.db)
        try:
            with create_session_factory(engine)() as session:
                result = StockOnboardingService(session).analyze(inputs, track=args.track)
                print(result.model_dump_json(indent=2))
        finally:
            engine.dispose()
    except (ValueError, OSError) as error:
        # No full input dump (which may contain private analyst research) on errors.
        parser.exit(2, json.dumps({"status": "INVALID_INPUT", "error_type": type(error).__name__}) + "\n")


if __name__ == "__main__":
    main()
