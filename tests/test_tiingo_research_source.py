from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request

import pytest

from engine.performance_engine import build_performance_snapshot
from engine.research_data import (
    HistoricalSecurityCandidate,
    ResearchDataFailureReason,
    TiingoAdjustmentEvidence,
    TiingoAuthenticationError,
    TiingoClient,
    TiingoClientSettings,
    TiingoEODObservation,
    TiingoEODSeries,
    TiingoMalformedResponseError,
    TiingoMetadata,
    TiingoMissingTokenError,
    TiingoHistoricalPriceSource,
    TiingoProviderError,
    TiingoRateLimitError,
    TiingoTransportResponse,
    tiingo_cache_key,
    tiingo_to_price_snapshots,
    validate_tiingo_dividend_adjustment,
    validate_tiingo_split_adjustment,
)
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    MetricResult,
    PerformanceHorizon,
    PerformanceReturnType,
    PriceBasis,
    QuantSnapshot,
    ResolutionState,
)


UTC = timezone.utc


def metadata_payload() -> dict:
    return {
        "ticker": "AAPL",
        "name": "Apple Inc",
        "exchangeCode": "NASDAQ",
        "startDate": "1980-12-12",
        "endDate": "2026-09-03",
        "description": "Synthetic test metadata",
    }


def eod_row(
    value_date: date,
    *,
    close: float = 100.0,
    adj_close: float | None = None,
    div_cash: float = 0.0,
    split_factor: float = 1.0,
) -> dict:
    adjusted = close if adj_close is None else adj_close
    return {
        "date": f"{value_date.isoformat()}T00:00:00.000Z",
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": 1000,
        "adjOpen": adjusted,
        "adjHigh": adjusted * 1.01,
        "adjLow": adjusted * 0.99,
        "adjClose": adjusted,
        "adjVolume": 1000,
        "divCash": div_cash,
        "splitFactor": split_factor,
    }


class StubTransport:
    def __init__(self, *responses: TiingoTransportResponse):
        self.responses = list(responses)
        self.requests: list[Request] = []

    def __call__(self, request: Request, _timeout: float) -> TiingoTransportResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected network call")
        return self.responses.pop(0)


def response(payload: object, status: int = 200, **headers: str):
    return TiingoTransportResponse(
        status_code=status,
        body=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )


def settings(tmp_path: Path, **updates) -> TiingoClientSettings:
    return TiingoClientSettings(cache_dir=tmp_path, **updates)


def test_missing_token_fails_before_network(monkeypatch, tmp_path):
    monkeypatch.delenv("TIINGO_API_TOKEN", raising=False)
    transport = StubTransport()
    with pytest.raises(TiingoMissingTokenError, match="not set"):
        TiingoClient.from_environment(
            settings=settings(tmp_path),
            transport=transport,
        )
    assert transport.requests == []


def test_metadata_parsing_and_header_auth_without_query_token(tmp_path):
    transport = StubTransport(response(metadata_payload()))
    client = TiingoClient("synthetic-secret", settings=settings(tmp_path), transport=transport)

    metadata, payload = client.metadata("AAPL")

    assert metadata.ticker == "AAPL"
    assert metadata.exchange_code == "NASDAQ"
    assert metadata.start_date == date(1980, 12, 12)
    assert metadata.end_date == date(2026, 9, 3)
    assert payload.cache_hit is False
    assert transport.requests[0].get_header("Authorization") == "Token synthetic-secret"
    assert "synthetic-secret" not in transport.requests[0].full_url


def test_eod_parser_preserves_raw_adjusted_and_action_fields(tmp_path):
    row = eod_row(
        date(2020, 8, 31),
        close=129.04,
        adj_close=125.40,
        div_cash=0.82,
        split_factor=4.0,
    )
    transport = StubTransport(response([row]))
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)

    observations, _payload = client.eod(
        "AAPL",
        start=date(2020, 8, 31),
        end=date(2020, 8, 31),
    )

    item = observations[0]
    assert item.open == row["open"]
    assert item.high == row["high"]
    assert item.low == row["low"]
    assert item.close == row["close"]
    assert item.volume == row["volume"]
    assert item.adj_open == row["adjOpen"]
    assert item.adj_high == row["adjHigh"]
    assert item.adj_low == row["adjLow"]
    assert item.adj_close == row["adjClose"]
    assert item.adj_volume == row["adjVolume"]
    assert item.div_cash == 0.82
    assert item.split_factor == 4.0


def test_search_parser_preserves_research_identity_fields(tmp_path):
    transport = StubTransport(
        response(
            [
                {
                    "ticker": "VLDR",
                    "name": "Velodyne Lidar",
                    "assetType": "Stock",
                    "isActive": False,
                    "permaTicker": "US000000VLDR",
                    "openFIGIComposite": "BBG00TESTVLDR",
                }
            ]
        )
    )
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)

    results = client.search("VLDR")

    assert len(results) == 1
    assert results[0].is_active is False
    assert results[0].perma_ticker == "US000000VLDR"
    assert results[0].open_figi == "BBG00TESTVLDR"
    assert transport.requests[0].full_url.endswith("?query=VLDR")


def test_nullable_delisted_metadata_and_empty_prices_remain_unresolved(tmp_path):
    transport = StubTransport(
        response(
            metadata_payload()
            | {"ticker": "BBBY", "name": None, "startDate": None, "endDate": None}
        ),
        response([]),
    )
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)
    candidate = HistoricalSecurityCandidate(
        permanent_id="test-bbby",
        company_id="test-company",
        instrument_id="test-instrument",
        ticker="BBBY",
        exchange="NASDAQ",
        anchor_date=date(2022, 1, 1),
    )

    result = TiingoHistoricalPriceSource(client).adjusted_prices(
        candidate,
        start=date(2022, 1, 1),
        end=date(2022, 12, 31),
    )

    assert result.value is None
    assert result.failures[0].reason == ResearchDataFailureReason.PRICE_UNAVAILABLE
    assert result.failures[0].detail == "no_price_observations"


def test_date_range_ordering_fails_before_network(tmp_path):
    transport = StubTransport()
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)
    with pytest.raises(ValueError, match="end date"):
        client.eod("AAPL", start=date(2022, 2, 1), end=date(2022, 1, 1))
    assert transport.requests == []


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, TiingoAuthenticationError), (500, TiingoProviderError)],
)
def test_provider_errors_are_structured_and_do_not_expose_token(
    tmp_path,
    status,
    error_type,
):
    transport = StubTransport(response({"detail": "provider error"}, status=status))
    client = TiingoClient("never-log-me", settings=settings(tmp_path), transport=transport)
    with pytest.raises(error_type) as captured:
        client.metadata("AAPL")
    assert "never-log-me" not in str(captured.value)


def test_429_is_structured_and_retains_retry_after(tmp_path):
    transport = StubTransport(response({}, status=429, **{"Retry-After": "17"}))
    client = TiingoClient(
        "test",
        settings=settings(tmp_path, max_rate_limit_retries=0),
        transport=transport,
    )
    with pytest.raises(TiingoRateLimitError) as captured:
        client.metadata("AAPL")
    assert captured.value.status_code == 429
    assert captured.value.retry_after_seconds == 17


def test_429_backoff_retries_without_parallel_request(tmp_path):
    transport = StubTransport(
        response({}, status=429, **{"Retry-After": "3"}),
        response(metadata_payload()),
    )
    waits: list[float] = []
    client = TiingoClient(
        "test",
        settings=settings(tmp_path, max_rate_limit_retries=1),
        transport=transport,
        sleeper=waits.append,
    )
    metadata, _payload = client.metadata("AAPL")
    assert metadata.ticker == "AAPL"
    assert waits == [3]
    assert len(transport.requests) == 2


def test_malformed_response_is_rejected(tmp_path):
    transport = StubTransport(
        TiingoTransportResponse(status_code=200, body=b"not-json", headers={})
    )
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)
    with pytest.raises(TiingoMalformedResponseError, match="malformed JSON"):
        client.metadata("AAPL")


def test_cache_key_is_stable_and_cache_prevents_duplicate_call(tmp_path):
    assert tiingo_cache_key(
        "/prices",
        {"endDate": "2022-01-02", "startDate": "2022-01-01"},
    ) == tiingo_cache_key(
        "/prices",
        {"startDate": "2022-01-01", "endDate": "2022-01-02"},
    )
    transport = StubTransport(response(metadata_payload()))
    client = TiingoClient("test", settings=settings(tmp_path), transport=transport)
    _first, first_payload = client.metadata("AAPL")
    _second, second_payload = client.metadata("AAPL")
    assert first_payload.cache_hit is False
    assert second_payload.cache_hit is True
    assert len(transport.requests) == 1
    assert list(tmp_path.glob("*.json"))


def observations(*rows: dict) -> tuple[TiingoEODObservation, ...]:
    return tuple(TiingoEODObservation.model_validate(row) for row in rows)


def test_split_validation_confirms_raw_discontinuity_and_adjusted_continuity():
    items = observations(
        eod_row(date(2020, 8, 28), close=500, adj_close=125),
        eod_row(
            date(2020, 8, 31),
            close=126,
            adj_close=126,
            split_factor=4,
        ),
    )
    result = validate_tiingo_split_adjustment(items)
    assert result.event_count == 1
    assert result.passed is True
    assert "factor=4" in result.details[0]


def test_split_validation_compares_basis_without_treating_market_move_as_failure():
    valid_market_move = observations(
        eod_row(date(2022, 8, 24), close=900, adj_close=300),
        eod_row(date(2022, 8, 25), close=337.5, adj_close=337.5, split_factor=3),
    )
    mismatched_adjustment = observations(
        eod_row(date(2022, 8, 24), close=900, adj_close=300),
        eod_row(date(2022, 8, 25), close=337.5, adj_close=300, split_factor=3),
    )

    assert validate_tiingo_split_adjustment(valid_market_move).passed is True
    assert validate_tiingo_split_adjustment(mismatched_adjustment).passed is False


def test_dividend_validation_matches_total_return_convention():
    items = observations(
        eod_row(date(2022, 1, 3), close=100, adj_close=99),
        eod_row(
            date(2022, 1, 4),
            close=99,
            adj_close=99,
            div_cash=1,
        ),
    )
    result = validate_tiingo_dividend_adjustment(items)
    assert result.event_count == 1
    assert result.passed is True


def series(items: tuple[TiingoEODObservation, ...]) -> TiingoEODSeries:
    return TiingoEODSeries(
        request_version="tiingo-eod-v0.1",
        requested_ticker="TEST",
        requested_start=items[0].date,
        requested_end=items[-1].date,
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        metadata=TiingoMetadata.model_validate(metadata_payload() | {"ticker": "TEST"}),
        observations=items,
        response_checksum="checksum",
        cache_key="cache-key",
        cache_hit=False,
    )


def test_price_basis_mapping_requires_validation_and_separates_bases():
    items = observations(
        eod_row(date(2020, 8, 28), close=500, adj_close=125),
        eod_row(date(2020, 8, 31), close=126, adj_close=126, split_factor=4),
    )
    unvalidated = TiingoAdjustmentEvidence(
        split_validation_passed=False,
        dividend_validation_passed=False,
    )
    with pytest.raises(ValueError, match="split adjustment"):
        tiingo_to_price_snapshots(
            series(items), basis=PriceBasis.SPLIT_ADJUSTED, evidence=unvalidated
        )

    validated = TiingoAdjustmentEvidence(
        split_validation_passed=True,
        dividend_validation_passed=True,
        split_symbols=("TEST",),
        dividend_symbols=("DIV",),
    )
    split_prices = tiingo_to_price_snapshots(
        series(items), basis=PriceBasis.SPLIT_ADJUSTED, evidence=validated
    )
    total_return_prices = tiingo_to_price_snapshots(
        series(items), basis=PriceBasis.TOTAL_RETURN_ADJUSTED, evidence=validated
    )
    assert [item.price for item in split_prices] == [125, 126]
    assert [item.price for item in total_return_prices] == [125, 126]
    assert split_prices[0].adjustment_version.endswith("raw_close_splitFactor_derived")
    assert total_return_prices[0].adjustment_version.endswith("provider_adjClose")
    assert split_prices[0].timestamp.hour == 20
    assert split_prices[1].timestamp.hour == 20


def test_mapped_split_series_runs_through_existing_performance_engine():
    start = date(2020, 1, 3)
    end = date(2021, 1, 5)
    rows = []
    current = start
    index = 0
    while current <= end:
        rows.append(eod_row(current, close=100 + index * 0.1))
        current += timedelta(days=1)
        index += 1
    items = observations(*rows)
    input_series = series(items).model_copy(
        update={"requested_start": start, "requested_end": end}
    )
    reference_id = "tiingo-performance-reference"
    evidence = TiingoAdjustmentEvidence(
        split_validation_passed=True,
        dividend_validation_passed=False,
        split_symbols=("SYNTHETIC",),
    )
    prices = tiingo_to_price_snapshots(
        input_series,
        basis=PriceBasis.SPLIT_ADJUSTED,
        evidence=evidence,
        reference_date=start,
        reference_price_snapshot_id=reference_id,
    )
    as_of = datetime(2020, 1, 2, 20, tzinfo=UTC)
    metric = MetricResult(
        name="synthetic",
        state=ResolutionState.UNRESOLVED,
        weight=1.0,
    )
    quant = QuantSnapshot(
        snapshot_id="synthetic-quant",
        ticker="TEST",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="synthetic",
        metrics=(metric,),
        state=ResolutionState.UNRESOLVED,
        coverage=0,
        provisional=True,
        period_end=date(2019, 12, 31),
        available_at=as_of,
        as_of=as_of,
    )
    analysis = AnalysisSnapshot(
        snapshot_id="synthetic-analysis",
        ticker="TEST",
        company_name="Synthetic",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="synthetic",
        quant=quant,
        reference_price_snapshot_id=reference_id,
        period_end=date(2019, 12, 31),
        available_at=as_of,
        as_of=as_of,
    )
    result = build_performance_snapshot(
        performance_snapshot_id="synthetic-performance",
        analysis=analysis,
        instrument_id="TEST",
        evaluation_as_of=prices[-1].timestamp,
        return_type=PerformanceReturnType.PRICE_RETURN,
        price_basis=PriceBasis.SPLIT_ADJUSTED,
        stock_prices=prices,
        created_at=datetime(2026, 9, 4, tzinfo=UTC),
    )
    horizons = {item.horizon: item for item in result.horizons}
    assert horizons[PerformanceHorizon.SIX_MONTHS].state == ResolutionState.RESOLVED
    assert horizons[PerformanceHorizon.ONE_YEAR].state == ResolutionState.RESOLVED
    assert result.max_drawdown == pytest.approx(0)
