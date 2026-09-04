# Youngrich Engine

Youngrich Engine is a versioned, point-in-time-safe stock analysis and tracking engine.
It separates Case-specific company quality, current business direction, Narrative,
Valuation, Investment Grade, immutable tracking, and realized performance.

Case 1 Profitable Growth and Case 2 Emerging / Asymmetric Growth are implemented and
frozen at v1. Cases 3–6, systematic backtesting, production market-data ingestion, API,
and dashboard/PWA work are not implemented.

For project status and LLM operating context, start with [PROJECT.md](PROJECT.md). Frozen
rules live under [docs/specs](docs/specs/), and milestone status lives in
[docs/roadmap.md](docs/roadmap.md).

## Setup

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -e ".[dev]"
```

On systems without the Windows launcher, use the equivalent `python -m ...` commands.

## Test

```bash
py -m pytest
git diff --check
```

Tests are offline and deterministic. Research-time fixture curation is separate and is
never invoked by pytest.

## Minimal usage

```bash
py -m app.demo
```

Raw financial inputs and source metadata are authoritative inputs. Analysis snapshots
are reproducible derived records; new information creates new immutable snapshots.

## Documentation

- [Project index and current state](PROJECT.md)
- [Milestone roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md)
- [Frozen specifications](docs/specs/)
- [Decision records](docs/decisions/README.md)
- [Validation results](docs/validation/)
- [Research plans](docs/research/)

Historical Stress Calibration v0.1 is intentionally curated and outcome-aware. It is a
diagnostic validation, not an unbiased strategy backtest or proof of alpha.
