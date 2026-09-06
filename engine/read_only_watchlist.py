"""Read-only projection for the bounded STRL/TEM/LPTH operating watchlist.

This module deliberately has no calculation, provider, seeding, migration, or write
entry point.  It opens an existing SQLite database in read-only mode and joins each
stored ``OperatingEvaluation`` to its immutable reference ``AnalysisSnapshot``.
"""

from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import model_validator
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from engine.limited_operating import (
    EvaluationArtifactStore,
    LimitedOperatingService,
    OperatingEvaluation,
    OperatingEvaluationDiff,
    SUPPORTED_TICKERS,
)
from engine.persistence.repositories import AnalysisRepository, PriceRepository
from engine.persistence.session import create_session_factory
from engine.tracking_models import AnalysisSnapshot, FrozenDomainModel


class WatchlistErrorCode(str, Enum):
    MISSING_DATABASE = "missing_database"
    MISSING_EVALUATIONS = "missing_evaluations"
    INVALID_DATABASE_PATH = "invalid_database_path"
    INVALID_EVALUATION_PATH = "invalid_evaluation_path"
    CORRUPT_DATABASE = "corrupt_database"
    CORRUPT_EVALUATIONS = "corrupt_evaluations"


class WatchlistDataError(RuntimeError):
    """Safe, structured data-source failure suitable for a local UI."""

    def __init__(self, code: WatchlistErrorCode, public_message: str):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


class WatchlistItemState(str, Enum):
    READY = "ready"
    MISSING_EVALUATION = "missing_evaluation"
    MISSING_ANALYSIS = "missing_analysis"
    INCONSISTENT_DATA = "inconsistent_data"


class WatchlistItem(FrozenDomainModel):
    ticker: str
    state: WatchlistItemState
    message: str | None = None
    evaluation: OperatingEvaluation | None = None
    reference_analysis: AnalysisSnapshot | None = None
    previous_evaluation: OperatingEvaluation | None = None
    latest_diff: OperatingEvaluationDiff | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state == WatchlistItemState.READY:
            if self.evaluation is None or self.reference_analysis is None:
                raise ValueError("ready watchlist item requires evaluation and analysis")
            if self.evaluation.ticker != self.ticker:
                raise ValueError("watchlist ticker must match evaluation")
            if self.reference_analysis.snapshot_id != self.evaluation.reference_analysis_snapshot_id:
                raise ValueError("watchlist analysis must match evaluation reference")
        elif self.evaluation is not None or self.reference_analysis is not None:
            raise ValueError("non-ready watchlist item cannot carry partial display data")
        return self


class WatchlistSnapshot(FrozenDomainModel):
    usage_mode: str = "DEMO/VALIDATION"
    items: tuple[WatchlistItem, ...]

    def item_for(self, ticker: str) -> WatchlistItem:
        return next(item for item in self.items if item.ticker == ticker)


def _require_existing_file(path: Path, *, database: bool) -> Path:
    missing_code = (
        WatchlistErrorCode.MISSING_DATABASE
        if database
        else WatchlistErrorCode.MISSING_EVALUATIONS
    )
    invalid_code = (
        WatchlistErrorCode.INVALID_DATABASE_PATH
        if database
        else WatchlistErrorCode.INVALID_EVALUATION_PATH
    )
    label = "데이터베이스" if database else "평가 기록"
    if not path.exists():
        raise WatchlistDataError(missing_code, f"저장된 {label} 파일이 없습니다.")
    if not path.is_file():
        raise WatchlistDataError(invalid_code, f"{label} 경로가 파일이 아닙니다.")
    return path.resolve()


def _readonly_engine(db_path: Path):
    uri = f"file:{db_path.as_posix()}?mode=ro"

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
        connection.execute("PRAGMA query_only=ON")
        return connection

    return create_engine("sqlite+pysqlite://", creator=connect, future=True)


def _evaluation_price_is_consistent(session, evaluation: OperatingEvaluation) -> bool:
    price = PriceRepository(session).get_price_snapshot(evaluation.price_snapshot_id)
    if price is None:
        return False
    return (
        price.ticker == evaluation.ticker
        and price.price == evaluation.price
        and price.currency == evaluation.currency
        and price.price_basis == evaluation.price_basis
        and price.timestamp == evaluation.price_timestamp
    )


def load_watchlist(
    db_path: str | Path,
    artifact_path: str | Path,
    *,
    tickers: tuple[str, ...] = SUPPORTED_TICKERS,
) -> WatchlistSnapshot:
    """Load a coherent read-only view without creating or modifying either source."""

    database = _require_existing_file(Path(db_path), database=True)
    artifacts = _require_existing_file(Path(artifact_path), database=False)

    store = EvaluationArtifactStore(artifacts)
    try:
        histories = {ticker: store.list_for_ticker(ticker) for ticker in tickers}
    except (OSError, UnicodeError, ValueError) as exc:
        raise WatchlistDataError(
            WatchlistErrorCode.CORRUPT_EVALUATIONS,
            "저장된 평가 기록을 검증할 수 없습니다. 최신 기록을 대신해 과거 기록을 표시하지 않았습니다.",
        ) from exc

    engine = _readonly_engine(database)
    session = create_session_factory(engine)()
    service = LimitedOperatingService(
        session,
        repo_root=database.parent,
        artifact_path=artifacts,
    )
    items: list[WatchlistItem] = []
    try:
        analyses = AnalysisRepository(session)
        for ticker in tickers:
            history = histories[ticker]
            if not history:
                items.append(
                    WatchlistItem(
                        ticker=ticker,
                        state=WatchlistItemState.MISSING_EVALUATION,
                        message="저장된 평가가 없습니다.",
                    )
                )
                continue

            latest = history[-1]
            analysis = analyses.get_analysis_snapshot(
                latest.reference_analysis_snapshot_id
            )
            if analysis is None:
                items.append(
                    WatchlistItem(
                        ticker=ticker,
                        state=WatchlistItemState.MISSING_ANALYSIS,
                        message="평가가 참조하는 기준 분석을 찾을 수 없습니다.",
                    )
                )
                continue
            if not _evaluation_price_is_consistent(session, latest):
                items.append(
                    WatchlistItem(
                        ticker=ticker,
                        state=WatchlistItemState.INCONSISTENT_DATA,
                        message="평가와 가격 원본의 연결이 일치하지 않습니다.",
                    )
                )
                continue

            previous = history[-2] if len(history) >= 2 else None
            latest_diff = None
            if previous is not None:
                if not _evaluation_price_is_consistent(session, previous):
                    items.append(
                        WatchlistItem(
                            ticker=ticker,
                            state=WatchlistItemState.INCONSISTENT_DATA,
                            message="이전 평가와 가격 원본의 연결이 일치하지 않습니다.",
                        )
                    )
                    continue
                latest_diff = service.compare_evaluations(
                    previous.evaluation_id, latest.evaluation_id
                )

            items.append(
                WatchlistItem(
                    ticker=ticker,
                    state=WatchlistItemState.READY,
                    evaluation=latest,
                    reference_analysis=analysis,
                    previous_evaluation=previous,
                    latest_diff=latest_diff,
                )
            )
    except WatchlistDataError:
        raise
    except (SQLAlchemyError, sqlite3.DatabaseError, ValueError) as exc:
        raise WatchlistDataError(
            WatchlistErrorCode.CORRUPT_DATABASE,
            "저장된 데이터베이스를 안전하게 읽을 수 없습니다.",
        ) from exc
    finally:
        session.close()
        engine.dispose()

    return WatchlistSnapshot(items=tuple(items))
