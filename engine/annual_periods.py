"""Shared annual-observation validation without Case-specific scoring logic."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol


class AnnualPeriodLike(Protocol):
    fiscal_year: int
    fiscal_period_end: date


MIN_ANNUAL_GAP_DAYS = 330
MAX_ANNUAL_GAP_DAYS = 400


def validate_annual_periods(periods: Sequence[AnnualPeriodLike]) -> None:
    """Require consecutive fiscal labels and comparable annual observation gaps.

    The calendar-day tolerance permits ordinary 52/53-week years and leap years. It is
    intentionally a data-quality contract, not an investment threshold.
    """
    for previous, current in zip(periods, periods[1:], strict=False):
        if current.fiscal_year != previous.fiscal_year + 1:
            raise ValueError("annual fiscal_year labels must be consecutive")
        gap_days = (current.fiscal_period_end - previous.fiscal_period_end).days
        if not MIN_ANNUAL_GAP_DAYS <= gap_days <= MAX_ANNUAL_GAP_DAYS:
            raise ValueError(
                "annual fiscal_period_end observations are not comparable: "
                f"gap_days={gap_days}"
            )
