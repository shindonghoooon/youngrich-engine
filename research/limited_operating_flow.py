"""CLI for the bounded STRL/TEM/LPTH DEMO/VALIDATION operating flow."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from engine.limited_operating import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DB_PATH,
    SUPPORTED_TICKERS,
    RefreshStatus,
    diff_summary,
    evaluation_summary,
    open_limited_operating_service,
)
from engine.tracking_models import InvestmentGradePolicyVersion


ROOT = Path(__file__).parents[1]


def _json(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, BaseModel):
            return item.model_dump(mode="json")
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, (date, datetime, Path)):
            return str(item)
        if isinstance(item, tuple):
            return list(item)
        raise TypeError(f"cannot serialize {type(item).__name__}")

    return json.dumps(value, indent=2, sort_keys=True, default=encode)


def _paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACT_PATH)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded STRL/TEM/LPTH DEMO/VALIDATION analysis-price flow. "
            "No output is a current investment recommendation."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed", help="persist immutable reference analyses")
    _paths(seed)
    seed.add_argument("--tickers", nargs="+", choices=SUPPORTED_TICKERS, default=list(SUPPORTED_TICKERS))

    refresh = subparsers.add_parser("refresh", help="import one exact Tiingo RAW close")
    _paths(refresh)
    refresh.add_argument("--ticker", choices=SUPPORTED_TICKERS, required=True)
    refresh.add_argument("--session-date", type=date.fromisoformat, required=True)

    revalue = subparsers.add_parser("revalue", help="derive an immutable v1.1 evaluation")
    _paths(revalue)
    revalue.add_argument("--ticker", choices=SUPPORTED_TICKERS, required=True)
    revalue.add_argument("--price-snapshot-id", required=True)
    revalue.add_argument("--assessment-as-of", type=datetime.fromisoformat)

    show = subparsers.add_parser("show", help="show stored evaluations and latest change")
    _paths(show)
    show.add_argument("--ticker", choices=SUPPORTED_TICKERS, required=True)
    show.add_argument("--json-only", action="store_true")

    run = subparsers.add_parser(
        "run", help="seed, refresh exact live closes, revalue, and compare in one command"
    )
    _paths(run)
    run.add_argument("--tickers", nargs="+", choices=SUPPORTED_TICKERS, default=list(SUPPORTED_TICKERS))
    run.add_argument("--session-date", type=date.fromisoformat, required=True)
    run.add_argument("--json-only", action="store_true")
    return parser


def _service(args: argparse.Namespace):
    return open_limited_operating_service(
        repo_root=ROOT,
        db_path=args.db,
        artifact_path=args.artifacts,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session, service = _service(args)
    try:
        if args.command == "seed":
            results = service.seed_demo(args.tickers)
            print(_json({"usage_mode": "DEMO/VALIDATION", "results": results}))
            return 0

        if args.command == "refresh":
            service.seed_demo((args.ticker,))
            result = service.refresh_eod(args.ticker, args.session_date)
            print(_json({"token_detected": bool(os.environ.get("TIINGO_API_TOKEN", "").strip()), "result": result}))
            return 0

        if args.command == "revalue":
            service.seed_demo((args.ticker,))
            evaluation, status = service.revalue(
                args.ticker,
                args.price_snapshot_id,
                policy_version=InvestmentGradePolicyVersion.V1_1,
                assessment_as_of=args.assessment_as_of,
            )
            print(evaluation_summary(evaluation))
            print(_json({"write_status": status.value, "evaluation": evaluation}))
            return 0

        if args.command == "show":
            items = service.artifacts.list_for_ticker(args.ticker)
            output: dict[str, Any] = {"usage_mode": "DEMO/VALIDATION", "evaluations": items}
            if len(items) >= 2:
                output["latest_diff"] = service.compare_evaluations(
                    items[-2].evaluation_id, items[-1].evaluation_id
                )
            if not args.json_only:
                if items:
                    print(evaluation_summary(items[-1]))
                    if "latest_diff" in output:
                        print()
                        print(diff_summary(output["latest_diff"]))
                else:
                    print(f"{args.ticker} - DEMO/VALIDATION - no evaluations stored")
            print(_json(output))
            return 0

        if args.command == "run":
            seeds = service.seed_demo(args.tickers)
            rows: list[dict[str, Any]] = []
            for ticker in args.tickers:
                refresh = service.refresh_eod(ticker, args.session_date)
                row: dict[str, Any] = {"ticker": ticker, "refresh": refresh}
                if refresh.status in {RefreshStatus.STORED, RefreshStatus.ALREADY_EXISTS}:
                    assert refresh.price_snapshot_id is not None
                    evaluation, status = service.revalue(
                        ticker,
                        refresh.price_snapshot_id,
                        policy_version=InvestmentGradePolicyVersion.V1_1,
                        assessment_as_of=datetime.combine(
                            args.session_date,
                            datetime.max.time(),
                            tzinfo=timezone.utc,
                        ),
                    )
                    row["evaluation"] = evaluation
                    row["write_status"] = status.value
                    history = service.artifacts.list_for_ticker(ticker)
                    if len(history) >= 2:
                        row["diff"] = service.compare_evaluations(
                            history[-2].evaluation_id, history[-1].evaluation_id
                        )
                    if not args.json_only:
                        print(evaluation_summary(evaluation))
                        if "diff" in row:
                            print(diff_summary(row["diff"]))
                        print()
                elif not args.json_only:
                    print(
                        f"{ticker} - DEMO/VALIDATION - {refresh.status.value}: "
                        f"{refresh.reason or 'no exact-session price'}"
                    )
                rows.append(row)
            print(
                _json(
                    {
                        "usage_mode": "DEMO/VALIDATION",
                        "token_detected": bool(
                            os.environ.get("TIINGO_API_TOKEN", "").strip()
                        ),
                        "seed": seeds,
                        "results": rows,
                    }
                )
            )
            return 0
        raise AssertionError("unreachable command")
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
