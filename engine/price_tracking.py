"""Pure price-series comparisons; no provider, persistence, or technical signals."""

from __future__ import annotations

from engine.tracking_models import PriceChange, PriceSnapshot


def compare_prices(previous: PriceSnapshot, current: PriceSnapshot) -> PriceChange:
    if previous.ticker != current.ticker:
        raise ValueError("price snapshots must use the same ticker")
    if current.timestamp <= previous.timestamp:
        raise ValueError("current price timestamp must be later than previous timestamp")
    if previous.currency != current.currency:
        raise ValueError("price snapshots must use the same currency")
    return PriceChange(
        ticker=previous.ticker,
        previous_timestamp=previous.timestamp,
        current_timestamp=current.timestamp,
        previous_price=previous.price,
        current_price=current.price,
        absolute_change=current.price - previous.price,
        return_ratio=current.price / previous.price - 1,
        market_cap_change=(
            current.market_cap - previous.market_cap
            if current.market_cap is not None and previous.market_cap is not None
            else None
        ),
        enterprise_value_change=(
            current.enterprise_value - previous.enterprise_value
            if current.enterprise_value is not None
            and previous.enterprise_value is not None
            else None
        ),
    )
