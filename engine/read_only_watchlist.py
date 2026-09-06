"""Read-only projection of persistent ACTIVE instrument memberships.

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
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import SQLAlchemyError

from engine.limited_operating import (
    EvaluationArtifactStore,
    LimitedOperatingService,
    OperatingEvaluation,
    OperatingEvaluationDiff,
)
from engine.persistence.models import AnalysisSnapshotRow, OnboardingRecordRow, PriceSnapshotRow
from engine.persistence.repositories import AnalysisRepository, PriceRepository
from engine.persistence.session import create_session_factory
from engine.tracking_models import AnalysisSnapshot, FrozenDomainModel, PriceSnapshot
from engine.stored_analysis_view import StoredAnalysisView, stored_analysis_view
from engine.watchlist_registry import WatchlistRepository


class WatchlistErrorCode(str, Enum):
    MISSING_DATABASE = "missing_database"
    MISSING_EVALUATIONS = "missing_evaluations"
    INVALID_DATABASE_PATH = "invalid_database_path"
    INVALID_EVALUATION_PATH = "invalid_evaluation_path"
    CORRUPT_DATABASE = "corrupt_database"
    CORRUPT_EVALUATIONS = "corrupt_evaluations"
    REGISTRY_MIGRATION_REQUIRED = "registry_migration_required"


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
    instrument_id: str | None = None
    exchange: str | None = None
    state: WatchlistItemState
    message: str | None = None
    evaluation: OperatingEvaluation | StoredAnalysisView | None = None
    reference_analysis: AnalysisSnapshot | None = None
    price_snapshot: PriceSnapshot | None = None
    previous_evaluation: OperatingEvaluation | None = None
    latest_diff: OperatingEvaluationDiff | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.state == WatchlistItemState.READY:
            if (
                self.evaluation is None
                or self.reference_analysis is None
                or (self.price_snapshot is None and not isinstance(self.evaluation, StoredAnalysisView))
            ):
                raise ValueError(
                    "ready watchlist item requires evaluation, analysis, and price"
                )
            if self.instrument_id is not None:
                if self.evaluation.instrument_id != self.instrument_id:
                    raise ValueError("watchlist instrument must match evaluation")
            elif self.evaluation.ticker != self.ticker:
                raise ValueError("watchlist ticker must match evaluation")
            if self.reference_analysis.snapshot_id != self.evaluation.reference_analysis_snapshot_id:
                raise ValueError("watchlist analysis must match evaluation reference")
            if self.price_snapshot is not None and self.price_snapshot.price_snapshot_id != self.evaluation.price_snapshot_id:
                raise ValueError("watchlist price must match evaluation reference")
        elif (
            self.evaluation is not None
            or self.reference_analysis is not None
            or self.price_snapshot is not None
        ):
            raise ValueError("non-ready watchlist item cannot carry partial display data")
        return self


class WatchlistSnapshot(FrozenDomainModel):
    usage_mode: str = "DEMO/VALIDATION"
    items: tuple[WatchlistItem, ...]

    def item_for(self, ticker: str) -> WatchlistItem:
        matches = [item for item in self.items if item.ticker == ticker]
        if len(matches) != 1:
            raise ValueError("ticker is missing or ambiguous; use instrument identity")
        return matches[0]


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


def _evaluation_price(session, evaluation: OperatingEvaluation) -> PriceSnapshot | None:
    row = session.get(PriceSnapshotRow, evaluation.price_snapshot_id)
    if row is None or row.instrument_id != evaluation.instrument_id:
        return None
    price = PriceRepository(session).get_price_snapshot(evaluation.price_snapshot_id)
    if price is None:
        return None
    consistent = (
        price.ticker == evaluation.ticker
        and price.price == evaluation.price
        and price.currency == evaluation.currency
        and price.price_basis == evaluation.price_basis
        and price.timestamp == evaluation.price_timestamp
    )
    return price if consistent else None


def load_watchlist(
    db_path: str | Path,
    artifact_path: str | Path | None = None,
) -> WatchlistSnapshot:
    """Load a coherent read-only view without creating or modifying either source."""

    database = _require_existing_file(Path(db_path), database=True)
    artifacts = _require_existing_file(Path(artifact_path), database=False) if artifact_path is not None else None

    store = EvaluationArtifactStore(artifacts) if artifacts else None
    try:
        evaluations = store._items() if store else ()
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
    ) if artifacts else None
    items: list[WatchlistItem] = []
    try:
        analyses = AnalysisRepository(session)
        if "watchlist_memberships" not in inspect(engine).get_table_names():
            raise WatchlistDataError(WatchlistErrorCode.REGISTRY_MIGRATION_REQUIRED,
                "관심종목 등록 저장소 준비가 필요합니다. 명시적인 migrate / register-existing-watchlist 명령을 사용하세요.")
        for entry in WatchlistRepository(session).list_active_watchlist():
            instrument = entry.instrument
            ticker = instrument.ticker
            identity = dict(ticker=ticker, instrument_id=instrument.instrument_id, exchange=instrument.exchange)
            history = sorted((e for e in evaluations if e.instrument_id == instrument.instrument_id),
                key=lambda e: (e.assessment_as_of, e.created_at, e.evaluation_id))
            current_analysis = entry.latest_analysis
            receipt = session.scalar(select(OnboardingRecordRow).where(
                OnboardingRecordRow.analysis_snapshot_id == current_analysis.snapshot_id
            )) if current_analysis else None
            # Never let an older price-only evaluation hide a newer fundamental analysis.
            if receipt and (not history or current_analysis.as_of >= history[-1].assessment_as_of):
                price = PriceRepository(session).get_price_snapshot(current_analysis.reference_price_snapshot_id) if current_analysis.reference_price_snapshot_id else None
                price_row = session.get(PriceSnapshotRow, current_analysis.reference_price_snapshot_id) if price else None
                expected_price = PriceSnapshot.model_validate(receipt.payload["input"]["price"]) if receipt.payload["input"]["price"] else None
                if (price != expected_price or (current_analysis.reference_price_snapshot_id
                        and (price_row is None or price_row.instrument_id != instrument.instrument_id))):
                    items.append(WatchlistItem(**identity, state=WatchlistItemState.INCONSISTENT_DATA,
                        message="분석과 가격 원본의 연결이 일치하지 않습니다."))
                else:
                    items.append(WatchlistItem(**identity, state=WatchlistItemState.READY,
                        evaluation=stored_analysis_view(current_analysis, price, receipt),
                        reference_analysis=current_analysis, price_snapshot=price))
                continue
            if not history:
                items.append(
                    WatchlistItem(
                        **identity,
                        state=WatchlistItemState.MISSING_EVALUATION if current_analysis else WatchlistItemState.MISSING_ANALYSIS,
                        message="저장된 가격 평가 없음" if current_analysis else "저장된 분석 없음",
                    )
                )
                continue

            latest = history[-1]
            analysis = analyses.get_analysis_snapshot(
                latest.reference_analysis_snapshot_id
            )
            analysis_row = session.get(AnalysisSnapshotRow, latest.reference_analysis_snapshot_id)
            if analysis_row is not None and analysis_row.instrument_id != instrument.instrument_id:
                raise ValueError("evaluation references a different instrument analysis")
            if analysis is None:
                items.append(
                    WatchlistItem(
                        **identity,
                        state=WatchlistItemState.MISSING_ANALYSIS,
                        message="평가가 참조하는 기준 분석을 찾을 수 없습니다.",
                    )
                )
                continue
            latest_price = _evaluation_price(session, latest)
            if latest_price is None:
                items.append(
                    WatchlistItem(
                        **identity,
                        state=WatchlistItemState.INCONSISTENT_DATA,
                        message="평가와 가격 원본의 연결이 일치하지 않습니다.",
                    )
                )
                continue

            previous = history[-2] if len(history) >= 2 else None
            latest_diff = None
            if previous is not None:
                if _evaluation_price(session, previous) is None:
                    items.append(
                        WatchlistItem(
                            **identity,
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
                    **identity,
                    state=WatchlistItemState.READY,
                    evaluation=latest,
                    reference_analysis=analysis,
                    price_snapshot=latest_price,
                    previous_evaluation=previous,
                    latest_diff=latest_diff,
                )
            )
    except WatchlistDataError:
        raise
    except (SQLAlchemyError, sqlite3.DatabaseError, ValueError, KeyError, TypeError) as exc:
        raise WatchlistDataError(
            WatchlistErrorCode.CORRUPT_DATABASE,
            "저장된 데이터베이스를 안전하게 읽을 수 없습니다.",
        ) from exc
    finally:
        session.close()
        engine.dispose()

    return WatchlistSnapshot(items=tuple(items))
