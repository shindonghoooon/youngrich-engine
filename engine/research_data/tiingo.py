"""Thin Tiingo research client for the M12-B0.1 price-data pilot.

The client preserves provider fields and provenance. It does not calculate Case metrics,
call the calibration kernel, or declare a Tiingo adjustment basis equivalent to a
youngrich-engine basis without explicit validation evidence.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Self
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

from engine.calibration_models import CalibrationDataQuality
from engine.research_data.contracts import (
    HistoricalPriceSource,
    HistoricalSecurityCandidate,
    ResearchDataFailure,
    ResearchDataFailureReason,
    ResearchDataResult,
    SourceReference,
)
from engine.tracking_models import (
    FrozenDomainModel,
    PriceBasis,
    PriceSnapshot,
    PriceType,
)


TIINGO_PROVIDER = "TIINGO"
TIINGO_REQUEST_VERSION = "tiingo-eod-v0.1"
DEFAULT_BASE_URL = "https://api.tiingo.com"
DEFAULT_CACHE_DIR = Path("data/local/tiingo")


class TiingoError(RuntimeError):
    """Base error that never includes the authentication token."""


class TiingoMissingTokenError(TiingoError):
    pass


class TiingoAuthenticationError(TiingoError):
    pass


class TiingoProviderError(TiingoError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TiingoRateLimitError(TiingoProviderError):
    def __init__(self, *, retry_after_seconds: float | None = None):
        super().__init__("Tiingo request rate-limited", status_code=429)
        self.retry_after_seconds = retry_after_seconds


class TiingoMalformedResponseError(TiingoError):
    pass


class TiingoMetadata(FrozenDomainModel):
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    ticker: str
    name: str | None = None
    exchange_code: str = Field(alias="exchangeCode")
    start_date: date | None = Field(alias="startDate")
    end_date: date | None = Field(alias="endDate")
    description: str | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_provider_date(cls, value: object) -> object:
        if isinstance(value, str) and "T" in value:
            return value.split("T", 1)[0]
        return value


class TiingoEODObservation(FrozenDomainModel):
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adj_open: float = Field(alias="adjOpen")
    adj_high: float = Field(alias="adjHigh")
    adj_low: float = Field(alias="adjLow")
    adj_close: float = Field(alias="adjClose")
    adj_volume: float = Field(alias="adjVolume")
    div_cash: float = Field(alias="divCash")
    split_factor: float = Field(alias="splitFactor")

    @field_validator("date", mode="before")
    @classmethod
    def parse_provider_date(cls, value: object) -> object:
        if isinstance(value, str) and "T" in value:
            return value.split("T", 1)[0]
        return value

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        prices = (
            self.open,
            self.high,
            self.low,
            self.close,
            self.adj_open,
            self.adj_high,
            self.adj_low,
            self.adj_close,
        )
        if any(value <= 0 for value in prices):
            raise ValueError("Tiingo EOD prices must be positive")
        if self.volume < 0 or self.adj_volume < 0:
            raise ValueError("Tiingo volume cannot be negative")
        if self.div_cash < 0:
            raise ValueError("Tiingo divCash cannot be negative")
        if self.split_factor <= 0:
            raise ValueError("Tiingo splitFactor must be positive")
        return self


class TiingoSearchResult(FrozenDomainModel):
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    ticker: str
    name: str | None = None
    asset_type: str | None = Field(default=None, alias="assetType")
    is_active: bool | None = Field(default=None, alias="isActive")
    perma_ticker: str | None = Field(default=None, alias="permaTicker")
    open_figi: str | None = Field(
        default=None,
        validation_alias=AliasChoices("openFIGI", "openFIGIComposite"),
    )


class TiingoEODSeries(FrozenDomainModel):
    provider: str = TIINGO_PROVIDER
    request_version: str
    requested_ticker: str
    requested_start: date
    requested_end: date
    retrieved_at: datetime
    metadata: TiingoMetadata
    observations: tuple[TiingoEODObservation, ...]
    response_checksum: str
    cache_key: str
    cache_hit: bool

    @model_validator(mode="after")
    def validate_series(self) -> Self:
        if self.provider != TIINGO_PROVIDER:
            raise ValueError("provider must be TIINGO")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.requested_end < self.requested_start:
            raise ValueError("requested end cannot precede start")
        ordered = tuple(sorted(self.observations, key=lambda item: item.date))
        if ordered != self.observations:
            raise ValueError("Tiingo observations must be date-ordered")
        dates = [item.date for item in self.observations]
        if len(dates) != len(set(dates)):
            raise ValueError("Tiingo observations cannot contain duplicate dates")
        if any(
            item.date < self.requested_start or item.date > self.requested_end
            for item in self.observations
        ):
            raise ValueError("Tiingo observation is outside the requested range")
        return self


class TiingoAdjustmentEvidence(FrozenDomainModel):
    split_validation_passed: bool
    dividend_validation_passed: bool
    split_symbols: tuple[str, ...] = ()
    dividend_symbols: tuple[str, ...] = ()
    note: str | None = None


class TiingoActionValidation(FrozenDomainModel):
    event_count: int = Field(ge=0)
    passed: bool
    details: tuple[str, ...] = ()


class TiingoClientSettings(FrozenDomainModel):
    base_url: str = DEFAULT_BASE_URL
    cache_dir: Path = DEFAULT_CACHE_DIR
    request_version: str = TIINGO_REQUEST_VERSION
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_rate_limit_retries: int = Field(default=1, ge=0, le=5)
    backoff_seconds: float = Field(default=2.0, ge=0)


@dataclass(frozen=True)
class TiingoTransportResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str]


@dataclass(frozen=True)
class _Payload:
    value: Any
    retrieved_at: datetime
    checksum: str
    cache_key: str
    cache_hit: bool


Transport = Callable[[Request, float], TiingoTransportResponse]
Sleeper = Callable[[float], None]


def _default_transport(request: Request, timeout_seconds: float) -> TiingoTransportResponse:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            return TiingoTransportResponse(
                status_code=response.status,
                body=response.read(),
                headers=dict(response.headers.items()),
            )
    except HTTPError as error:
        return TiingoTransportResponse(
            status_code=error.code,
            body=error.read(),
            headers=dict(error.headers.items()) if error.headers else {},
        )
    except URLError as error:
        raise TiingoProviderError("Tiingo network request failed") from error


def tiingo_cache_key(
    endpoint: str,
    params: Mapping[str, str],
    *,
    request_version: str = TIINGO_REQUEST_VERSION,
) -> str:
    canonical = json.dumps(
        {
            "endpoint": endpoint,
            "params": sorted(params.items()),
            "request_version": request_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class TiingoCache:
    def __init__(self, root: Path, request_version: str):
        self.root = root
        self.request_version = request_version

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def read(self, key: str) -> _Payload | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope["payload"]
            checksum = sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if checksum != envelope["checksum"]:
                raise TiingoMalformedResponseError("Tiingo cache checksum mismatch")
            return _Payload(
                value=payload,
                retrieved_at=datetime.fromisoformat(envelope["retrieved_at"]),
                checksum=checksum,
                cache_key=key,
                cache_hit=True,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise TiingoMalformedResponseError("Tiingo cache is malformed") from error

    def write(self, key: str, payload: Any, retrieved_at: datetime) -> _Payload:
        self.root.mkdir(parents=True, exist_ok=True)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        checksum = sha256(canonical.encode("utf-8")).hexdigest()
        envelope = {
            "request_version": self.request_version,
            "retrieved_at": retrieved_at.isoformat(),
            "checksum": checksum,
            "payload": payload,
        }
        self._path(key).write_text(
            json.dumps(envelope, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        return _Payload(
            value=payload,
            retrieved_at=retrieved_at,
            checksum=checksum,
            cache_key=key,
            cache_hit=False,
        )


class TiingoClient:
    def __init__(
        self,
        token: str,
        *,
        settings: TiingoClientSettings | None = None,
        transport: Transport = _default_transport,
        sleeper: Sleeper = time.sleep,
    ):
        if not token.strip():
            raise TiingoMissingTokenError("TIINGO_API_TOKEN is not set")
        self._token = token.strip()
        self.settings = settings or TiingoClientSettings()
        self._transport = transport
        self._sleeper = sleeper
        self._cache = TiingoCache(
            self.settings.cache_dir,
            self.settings.request_version,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        settings: TiingoClientSettings | None = None,
        transport: Transport = _default_transport,
        sleeper: Sleeper = time.sleep,
    ) -> "TiingoClient":
        token = os.environ.get("TIINGO_API_TOKEN", "")
        return cls(token, settings=settings, transport=transport, sleeper=sleeper)

    def _request_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, str] | None = None,
        use_cache: bool = True,
    ) -> _Payload:
        request_params = dict(params or {})
        key = tiingo_cache_key(
            endpoint,
            request_params,
            request_version=self.settings.request_version,
        )
        if use_cache:
            cached = self._cache.read(key)
            if cached is not None:
                return cached

        query = f"?{urlencode(request_params)}" if request_params else ""
        request = Request(
            f"{self.settings.base_url.rstrip('/')}{endpoint}{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Token {self._token}",
                "User-Agent": "youngrich-engine/tiingo-research-v0.1",
            },
        )
        response: TiingoTransportResponse | None = None
        for attempt in range(self.settings.max_rate_limit_retries + 1):
            response = self._transport(request, self.settings.timeout_seconds)
            if response.status_code != 429:
                break
            retry_after = _retry_after(response.headers)
            if attempt == self.settings.max_rate_limit_retries:
                raise TiingoRateLimitError(retry_after_seconds=retry_after)
            self._sleeper(
                retry_after
                if retry_after is not None
                else self.settings.backoff_seconds * (2**attempt)
            )

        assert response is not None
        if response.status_code in (401, 403):
            raise TiingoAuthenticationError("Tiingo authentication failed")
        if not 200 <= response.status_code < 300:
            raise TiingoProviderError(
                f"Tiingo request failed with HTTP {response.status_code}",
                status_code=response.status_code,
            )
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TiingoMalformedResponseError("Tiingo returned malformed JSON") from error
        retrieved_at = datetime.now(timezone.utc)
        if use_cache:
            return self._cache.write(key, payload, retrieved_at)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return _Payload(
            value=payload,
            retrieved_at=retrieved_at,
            checksum=sha256(canonical.encode("utf-8")).hexdigest(),
            cache_key=key,
            cache_hit=False,
        )

    def authenticate(self) -> bool:
        payload = self._request_json("/api/test/", use_cache=False).value
        return isinstance(payload, dict) and bool(payload.get("message"))

    def metadata(self, ticker: str) -> tuple[TiingoMetadata, _Payload]:
        payload = self._request_json(f"/tiingo/daily/{quote(ticker, safe='-')}")
        if not isinstance(payload.value, dict):
            raise TiingoMalformedResponseError("Tiingo metadata response must be an object")
        try:
            return TiingoMetadata.model_validate(payload.value), payload
        except ValueError as error:
            raise TiingoMalformedResponseError("Tiingo metadata fields are malformed") from error

    def eod(
        self,
        ticker: str,
        *,
        start: date,
        end: date,
    ) -> tuple[tuple[TiingoEODObservation, ...], _Payload]:
        if end < start:
            raise ValueError("end date cannot precede start date")
        payload = self._request_json(
            f"/tiingo/daily/{quote(ticker, safe='-')}/prices",
            params={"startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        if not isinstance(payload.value, list):
            raise TiingoMalformedResponseError("Tiingo EOD response must be an array")
        try:
            observations = tuple(
                TiingoEODObservation.model_validate(item) for item in payload.value
            )
        except (TypeError, ValueError) as error:
            raise TiingoMalformedResponseError("Tiingo EOD fields are malformed") from error
        if tuple(sorted(observations, key=lambda item: item.date)) != observations:
            raise TiingoMalformedResponseError("Tiingo EOD response is not date-ordered")
        return observations, payload

    def search(self, query: str) -> tuple[TiingoSearchResult, ...]:
        payload = self._request_json(
            "/tiingo/utilities/search",
            params={"query": query},
        )
        if not isinstance(payload.value, list):
            raise TiingoMalformedResponseError("Tiingo search response must be an array")
        try:
            return tuple(TiingoSearchResult.model_validate(item) for item in payload.value)
        except (TypeError, ValueError) as error:
            raise TiingoMalformedResponseError("Tiingo search fields are malformed") from error


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = next(
        (value for key, value in headers.items() if key.lower() == "retry-after"),
        None,
    )
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class TiingoHistoricalPriceSource(HistoricalPriceSource[TiingoEODSeries]):
    provider_name = TIINGO_PROVIDER
    source_version = TIINGO_REQUEST_VERSION

    def __init__(self, client: TiingoClient):
        self.client = client

    def adjusted_prices(
        self,
        candidate: HistoricalSecurityCandidate,
        *,
        start: date,
        end: date,
    ) -> ResearchDataResult[TiingoEODSeries]:
        try:
            metadata, metadata_payload = self.client.metadata(candidate.ticker)
            observations, prices_payload = self.client.eod(
                candidate.ticker,
                start=start,
                end=end,
            )
            if not observations:
                return ResearchDataResult(
                    quality=CalibrationDataQuality.UNRESOLVED,
                    failures=(
                        ResearchDataFailure(
                            reason=ResearchDataFailureReason.PRICE_UNAVAILABLE,
                            stage="tiingo_historical_price",
                            detail="no_price_observations",
                        ),
                    ),
                )
            series = TiingoEODSeries(
                request_version=self.client.settings.request_version,
                requested_ticker=candidate.ticker,
                requested_start=start,
                requested_end=end,
                retrieved_at=prices_payload.retrieved_at,
                metadata=metadata,
                observations=observations,
                response_checksum=prices_payload.checksum,
                cache_key=prices_payload.cache_key,
                cache_hit=metadata_payload.cache_hit and prices_payload.cache_hit,
            )
            return ResearchDataResult(
                quality=CalibrationDataQuality.COMPLETE,
                value=series,
                sources=(
                    SourceReference(
                        provider=TIINGO_PROVIDER,
                        role="metadata_and_eod_prices",
                        source_version=self.source_version,
                        url=(
                            f"{self.client.settings.base_url.rstrip('/')}"
                            f"/tiingo/daily/{candidate.ticker}"
                        ),
                        retrieved_at=prices_payload.retrieved_at,
                        note="Raw licensed payload retained only in ignored local cache.",
                    ),
                ),
            )
        except TiingoError as error:
            return ResearchDataResult(
                quality=CalibrationDataQuality.UNRESOLVED,
                failures=(
                    ResearchDataFailure(
                        reason=ResearchDataFailureReason.SOURCE_ACCESS,
                        stage="tiingo_historical_price",
                        detail=type(error).__name__,
                    ),
                ),
            )


def validate_tiingo_split_adjustment(
    observations: Sequence[TiingoEODObservation],
    *,
    tolerance: float = 1e-6,
) -> TiingoActionValidation:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")
    ordered = tuple(sorted(observations, key=lambda item: item.date))
    results: list[bool] = []
    details: list[str] = []
    for previous, current in zip(ordered, ordered[1:]):
        if current.split_factor == 1.0:
            continue
        raw_normalized_return = (
            current.close / previous.close * current.split_factor - 1.0
        )
        adjusted_return = current.adj_close / previous.adj_close - 1.0
        basis_error = abs(raw_normalized_return - adjusted_return)
        passed = basis_error <= tolerance
        results.append(passed)
        details.append(
            f"{current.date.isoformat()}: factor={current.split_factor:g}; "
            f"raw_normalized_return={raw_normalized_return:.6f}; "
            f"adjusted_return={adjusted_return:.6f}; basis_error={basis_error:.6f}"
        )
    return TiingoActionValidation(
        event_count=len(results),
        passed=bool(results) and all(results),
        details=tuple(details),
    )


def validate_tiingo_dividend_adjustment(
    observations: Sequence[TiingoEODObservation],
    *,
    tolerance: float = 0.01,
) -> TiingoActionValidation:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")
    ordered = tuple(sorted(observations, key=lambda item: item.date))
    results: list[bool] = []
    details: list[str] = []
    for previous, current in zip(ordered, ordered[1:]):
        if current.div_cash == 0:
            continue
        economic_return = (current.close + current.div_cash) / previous.close - 1.0
        adjusted_return = current.adj_close / previous.adj_close - 1.0
        error = abs(economic_return - adjusted_return)
        results.append(error <= tolerance)
        details.append(
            f"{current.date.isoformat()}: divCash={current.div_cash:g}; "
            f"economic_return={economic_return:.6f}; "
            f"adjusted_return={adjusted_return:.6f}; error={error:.6f}"
        )
    return TiingoActionValidation(
        event_count=len(results),
        passed=bool(results) and all(results),
        details=tuple(details),
    )


def _split_adjusted_closes(
    observations: Sequence[TiingoEODObservation],
) -> tuple[tuple[TiingoEODObservation, float], ...]:
    cumulative_future_split = 1.0
    output: list[tuple[TiingoEODObservation, float]] = []
    for observation in reversed(tuple(observations)):
        output.append((observation, observation.close / cumulative_future_split))
        cumulative_future_split *= observation.split_factor
    return tuple(reversed(output))


def tiingo_to_price_snapshots(
    series: TiingoEODSeries,
    *,
    basis: PriceBasis,
    evidence: TiingoAdjustmentEvidence,
    currency: str = "USD",
    reference_date: date | None = None,
    reference_price_snapshot_id: str | None = None,
    market_timezone: str = "America/New_York",
) -> tuple[PriceSnapshot, ...]:
    """Map validated US EOD session labels to scheduled regular-close timestamps.

    Tiingo's EOD ``date`` is a trading-session label, not a provider publication or
    executable timestamp. The v0.1 pilot uses 16:00 in the explicit market timezone and
    leaves early-close/exchange-calendar refinement unresolved.
    """
    if basis == PriceBasis.RAW:
        values = tuple((item, item.close) for item in series.observations)
        adjustment_version = None
    elif basis == PriceBasis.SPLIT_ADJUSTED:
        if not evidence.split_validation_passed:
            raise ValueError("Tiingo split adjustment has not been validated")
        values = _split_adjusted_closes(series.observations)
        adjustment_version = f"{series.request_version}:raw_close_splitFactor_derived"
    else:
        if not evidence.split_validation_passed or not evidence.dividend_validation_passed:
            raise ValueError("Tiingo total-return adjustment has not been validated")
        values = tuple((item, item.adj_close) for item in series.observations)
        adjustment_version = f"{series.request_version}:provider_adjClose"

    created_at = series.retrieved_at.astimezone(timezone.utc)
    session_timezone = ZoneInfo(market_timezone)
    snapshots: list[PriceSnapshot] = []
    for observation, value in values:
        identifier = (
            reference_price_snapshot_id
            if reference_date == observation.date and reference_price_snapshot_id
            else f"tiingo-{series.requested_ticker}-{basis.value}-{observation.date.isoformat()}"
        )
        snapshots.append(
            PriceSnapshot(
                price_snapshot_id=identifier,
                ticker=series.requested_ticker,
                timestamp=datetime.combine(
                    observation.date,
                    datetime_time(16, 0),
                    tzinfo=session_timezone,
                ).astimezone(timezone.utc),
                price=value,
                currency=currency,
                source=TIINGO_PROVIDER,
                price_type=PriceType.CLOSE,
                price_basis=basis,
                adjustment_version=adjustment_version,
                provider_reference=(
                    f"{DEFAULT_BASE_URL}/tiingo/daily/"
                    f"{series.requested_ticker}/prices"
                ),
                created_at=created_at,
            )
        )
    return tuple(snapshots)
