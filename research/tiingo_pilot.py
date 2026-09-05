"""Manual Tiingo smoke and small price pilot; never imported by normal tests.

Examples:
    py -m research.tiingo_pilot smoke
    py -m research.tiingo_pilot pilot
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from engine.performance_engine import add_calendar_months, build_performance_snapshot
from engine.research_data.tiingo import (
    TiingoAdjustmentEvidence,
    TiingoClient,
    TiingoClientSettings,
    TiingoEODSeries,
    TiingoError,
    tiingo_to_price_snapshots,
    validate_tiingo_dividend_adjustment,
    validate_tiingo_split_adjustment,
)
from engine.tracking_models import (
    PerformanceHorizon,
    PerformanceReturnType,
    PriceBasis,
)
from research.historical_performance_calibration import (
    load_historical_stress_records,
)


DEFAULT_SYMBOLS = (
    "AAPL",
    "ADBE",
    "CRWD",
    "NVDA",
    "TSLA",
    "SKLZ",
    "VLDR",
    "FSLY",
    "TWTR",
    "BBBY",
    "SPY",
    "VTI",
)
SUMMARY_PATH = Path("data/local/tiingo/pilot-summary.json")


def _client(args: argparse.Namespace) -> TiingoClient:
    return TiingoClient.from_environment(
        settings=TiingoClientSettings(
            cache_dir=Path(args.cache_dir),
            max_rate_limit_retries=args.rate_limit_retries,
            backoff_seconds=args.backoff_seconds,
        )
    )


def _series_summary(series: TiingoEODSeries) -> dict:
    split_count = sum(item.split_factor != 1.0 for item in series.observations)
    dividend_count = sum(item.div_cash != 0 for item in series.observations)
    return {
        "ticker": series.requested_ticker,
        "name": series.metadata.name,
        "exchangeCode": series.metadata.exchange_code,
        "metadataStartDate": (
            series.metadata.start_date.isoformat() if series.metadata.start_date else None
        ),
        "metadataEndDate": (
            series.metadata.end_date.isoformat() if series.metadata.end_date else None
        ),
        "requestedStart": series.requested_start.isoformat(),
        "requestedEnd": series.requested_end.isoformat(),
        "observationCount": len(series.observations),
        "firstDate": (
            series.observations[0].date.isoformat() if series.observations else None
        ),
        "lastDate": (
            series.observations[-1].date.isoformat() if series.observations else None
        ),
        "splitEventCount": split_count,
        "dividendEventCount": dividend_count,
        "cacheHit": series.cache_hit,
        "cacheKey": series.cache_key,
        "responseChecksum": series.response_checksum,
    }


def _performance_checks(
    series_by_ticker: dict[str, TiingoEODSeries],
    evidence: TiingoAdjustmentEvidence,
) -> list[dict]:
    results: list[dict] = []
    if not evidence.split_validation_passed:
        return results
    for record in load_historical_stress_records():
        series = series_by_ticker.get(record.metadata.ticker)
        reference = record.raw_fixture.get("reference_price")
        if series is None or reference is None:
            continue
        reference_date = datetime.fromisoformat(
            reference["timestamp"].replace("Z", "+00:00")
        ).date()
        intended_end = add_calendar_months(reference_date, 12) + timedelta(days=7)
        observations = tuple(
            item
            for item in series.observations
            if reference_date <= item.date <= intended_end
        )
        if not observations:
            results.append(
                {"sample": record.metadata.sample_id, "state": "unresolved_no_prices"}
            )
            continue
        subset = series.model_copy(
            update={
                "requested_start": reference_date,
                "requested_end": intended_end,
                "observations": observations,
            }
        )
        prices = tiingo_to_price_snapshots(
            subset,
            basis=PriceBasis.SPLIT_ADJUSTED,
            evidence=evidence,
            reference_date=reference_date,
            reference_price_snapshot_id=record.analysis.reference_price_snapshot_id,
        )
        performance = build_performance_snapshot(
            performance_snapshot_id=f"{record.metadata.sample_id}-tiingo-pilot",
            analysis=record.analysis,
            instrument_id=f"{record.metadata.ticker}-tiingo-pilot",
            evaluation_as_of=prices[-1].timestamp,
            return_type=PerformanceReturnType.PRICE_RETURN,
            price_basis=PriceBasis.SPLIT_ADJUSTED,
            stock_prices=prices,
            created_at=series.retrieved_at,
        )
        horizons = {item.horizon: item for item in performance.horizons}
        results.append(
            {
                "sample": record.metadata.sample_id,
                "sixMonthState": horizons[PerformanceHorizon.SIX_MONTHS].state.value,
                "oneYearState": horizons[PerformanceHorizon.ONE_YEAR].state.value,
                "mddState": performance.mdd_coverage.status.value,
                "observationCount": performance.mdd_coverage.observation_count,
            }
        )
    return results


def run_smoke(args: argparse.Namespace) -> int:
    token_detected = bool(os.environ.get("TIINGO_API_TOKEN", "").strip())
    if not token_detected:
        print(json.dumps({"tokenDetected": False, "status": "not_run"}))
        return 2
    try:
        client = _client(args)
        authenticated = client.authenticate()
        metadata, _metadata_payload = client.metadata("AAPL")
        observations, payload = client.eod(
            "AAPL",
            start=date.fromisoformat(args.start),
            end=date.fromisoformat(args.end),
        )
        print(
            json.dumps(
                {
                    "tokenDetected": True,
                    "authenticated": authenticated,
                    "ticker": metadata.ticker,
                    "name": metadata.name,
                    "exchangeCode": metadata.exchange_code,
                    "metadataStartDate": (
                        metadata.start_date.isoformat() if metadata.start_date else None
                    ),
                    "metadataEndDate": (
                        metadata.end_date.isoformat() if metadata.end_date else None
                    ),
                    "observationCount": len(observations),
                    "firstDate": observations[0].date.isoformat() if observations else None,
                    "lastDate": observations[-1].date.isoformat() if observations else None,
                    "corporateActionCount": sum(
                        item.split_factor != 1.0 or item.div_cash != 0
                        for item in observations
                    ),
                    "cacheHit": payload.cache_hit,
                },
                indent=2,
            )
        )
        return 0
    except TiingoError as error:
        print(
            json.dumps(
                {
                    "tokenDetected": True,
                    "status": "unresolved",
                    "errorType": type(error).__name__,
                }
            )
        )
        return 1


def run_pilot(args: argparse.Namespace) -> int:
    token_detected = bool(os.environ.get("TIINGO_API_TOKEN", "").strip())
    if not token_detected:
        print(json.dumps({"tokenDetected": False, "status": "not_run"}))
        return 2
    client = _client(args)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    summaries: list[dict] = []
    searches: dict[str, list[dict]] = {}
    series_by_ticker: dict[str, TiingoEODSeries] = {}
    split_passed_symbols: list[str] = []
    dividend_passed_symbols: list[str] = []
    for ticker in args.symbols:
        stage = "metadata"
        try:
            metadata, metadata_payload = client.metadata(ticker)
            stage = "eod"
            observations, prices_payload = client.eod(ticker, start=start, end=end)
            if not observations:
                summaries.append(
                    {
                        "ticker": ticker,
                        "name": metadata.name,
                        "exchangeCode": metadata.exchange_code,
                        "metadataStartDate": (
                            metadata.start_date.isoformat()
                            if metadata.start_date
                            else None
                        ),
                        "metadataEndDate": (
                            metadata.end_date.isoformat() if metadata.end_date else None
                        ),
                        "state": "unresolved_no_prices",
                        "observationCount": 0,
                    }
                )
            else:
                series = TiingoEODSeries(
                    request_version=client.settings.request_version,
                    requested_ticker=ticker,
                    requested_start=start,
                    requested_end=end,
                    retrieved_at=prices_payload.retrieved_at,
                    metadata=metadata,
                    observations=observations,
                    response_checksum=prices_payload.checksum,
                    cache_key=prices_payload.cache_key,
                    cache_hit=metadata_payload.cache_hit and prices_payload.cache_hit,
                )
                series_by_ticker[ticker] = series
                summaries.append(_series_summary(series))
                split = validate_tiingo_split_adjustment(observations)
                dividend = validate_tiingo_dividend_adjustment(observations)
                if split.passed:
                    split_passed_symbols.append(ticker)
                if dividend.passed:
                    dividend_passed_symbols.append(ticker)
        except (TiingoError, ValueError) as error:
            summaries.append(
                {
                    "ticker": ticker,
                    "state": "unresolved",
                    "stage": stage,
                    "errorType": type(error).__name__,
                }
            )

        try:
            searches[ticker] = [
                {
                    "ticker": item.ticker,
                    "name": item.name,
                    "assetType": item.asset_type,
                    "isActive": item.is_active,
                    "permaTicker": item.perma_ticker,
                    "openFIGI": item.open_figi,
                }
                for item in client.search(ticker)
            ]
        except (TiingoError, ValueError) as error:
            searches[ticker] = [
                {"state": "unresolved", "errorType": type(error).__name__}
            ]
        if args.pause_seconds:
            time.sleep(args.pause_seconds)

    evidence = TiingoAdjustmentEvidence(
        split_validation_passed=bool(split_passed_symbols),
        dividend_validation_passed=bool(dividend_passed_symbols),
        split_symbols=tuple(split_passed_symbols),
        dividend_symbols=tuple(dividend_passed_symbols),
        note="Pilot evidence only; review before production price-basis mapping.",
    )
    output = {
        "schemaVersion": "m12-b0.1-tiingo-pilot-v0.1",
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "tokenDetected": True,
        "symbols": summaries,
        "search": searches,
        "adjustmentEvidence": evidence.model_dump(mode="json"),
        "performanceEngineChecks": _performance_checks(series_by_ticker, evidence),
    }
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "tokenDetected": True,
                "tested": len(args.symbols),
                "resolved": len(series_by_ticker),
                "splitValidationPassed": evidence.split_validation_passed,
                "dividendValidationPassed": evidence.dividend_validation_passed,
                "summaryPath": str(summary_path),
            },
            indent=2,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--cache-dir", default="data/local/tiingo")
    root.add_argument("--rate-limit-retries", type=int, default=1)
    root.add_argument("--backoff-seconds", type=float, default=2.0)
    commands = root.add_subparsers(dest="command", required=True)

    smoke = commands.add_parser("smoke")
    smoke.add_argument("--start", default="2022-01-03")
    smoke.add_argument("--end", default="2022-01-10")
    smoke.set_defaults(handler=run_smoke)

    pilot = commands.add_parser("pilot")
    pilot.add_argument("--start", default="2018-01-01")
    pilot.add_argument("--end", default="2023-12-31")
    pilot.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    pilot.add_argument("--pause-seconds", type=float, default=1.0)
    pilot.add_argument("--summary-path", default=str(SUMMARY_PATH))
    pilot.set_defaults(handler=run_pilot)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
