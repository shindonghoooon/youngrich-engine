# Read-only Watchlist — STRL / TEM / LPTH

Status: ACTIVE — DEMO/VALIDATION

Last Updated: 2026-09-06

This is a local, read-only Streamlit view over the bounded limited-operating result. It
does not fetch prices, run Case/Quant/Valuation/Investment Grade calculations, edit an
assumption, or create a database. Nothing shown is realtime data or an investment
recommendation.

## Environment

The repository-local environment was created from Python 3.12.14. The interpreter used
for installation, tests, and the app is:

```text
D:\youngrich-engine\youngrich-engine\.venv\Scripts\python.exe
```

Create the environment only when `.venv` does not already exist, then install the project:

```text
C:\Users\sdh94\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`.venv/` is ignored by Git. Do not replace or modify another Python installation.

## Stored inputs

The default sources are both ignored by Git:

- SQLite: `data/local/limited-operating/demo.sqlite3`
- append-only evaluations: `data/local/limited-operating/evaluations.jsonl`

SQLite is opened with SQLite `mode=ro` and `PRAGMA query_only=ON`. The JSONL file is read
and validated in full before any ticker result is displayed. A corrupt latest record is
never hidden by silently falling back to an older evaluation.

Alternate local paths may be selected only when the app process starts. They are not
accepted from a browser field:

```text
.\.venv\Scripts\python.exe -m streamlit run app/read_only_watchlist.py --server.address 127.0.0.1 -- --db <existing.sqlite3> --artifacts <existing.jsonl>
```

The equivalent startup environment variables are
`YOUNGRICH_WATCHLIST_DB_PATH` and `YOUNGRICH_WATCHLIST_ARTIFACT_PATH`. The view never reads
`TIINGO_API_TOKEN` and does not need a network connection.

### Existing live-validation pair

The ignored files from the bounded 2026-09-04 Tiingo validation are a separate,
corresponding pair:

- SQLite: `data/local/limited-operating-live-2026-09-04.sqlite`
- evaluations: `data/local/limited-operating-live-2026-09-04.jsonl`

From the repository root, inspect that existing pair without seeding, refreshing, or
revaluing:

```text
.\.venv\Scripts\python.exe -m streamlit run app/read_only_watchlist.py --server.address 127.0.0.1 -- --db "data/local/limited-operating-live-2026-09-04.sqlite" --artifacts "data/local/limited-operating-live-2026-09-04.jsonl"
```

Local screen verification on 2026-09-06 matched the stored evaluations: STRL 486.49 USD
and `U`, TEM 64.62 USD and `B`, and LPTH 9.67 USD and `U`, all on 2026-09-04 with RAW
Tiingo prices and IG policy v1.1. The screen displayed `U` as `판단 보류`, retained the
stored reasons and assumption states, and showed that no ticker had an earlier evaluation
in this artifact. SHA-256 checks of both ignored source files were identical before and
after the reload control. Desktop and 390 px browser QA passed; this was a local browser
viewport check, not remote-phone access. No provider call was made.

## Run locally

```text
.\.venv\Scripts\python.exe -m streamlit run app/read_only_watchlist.py --server.address 127.0.0.1
```

Open the loopback URL printed by Streamlit. The page is responsive at a narrow browser
viewport, but this does not provide remote phone access. No public deployment, tunnel,
port forwarding, firewall change, CDN, or remote font is part of this pilot.
Repository Streamlit configuration disables usage telemetry, so the local view has no
application or framework reason to contact an external host.

If either default input is absent, the page shows `저장된 데이터 없음` and points to
[the existing limited operating CLI](limited-operating-flow.md). It does not create or
download substitute data.

## Display contract

The summary and detail views keep the price, derived Investment Grade, policy version,
assumption identity, and Expectation Gap from one `OperatingEvaluation`. A separately
newer price is never mixed into the card. The immutable reference `AnalysisSnapshot`
provides company name, Quant, Current, Narrative, and Thesis/KPI evidence.

- a stored Investment Grade `U` is displayed as `판단 보류`; technical code `U` and every
  structured reason remain available in detail.
- missing/corrupt files, missing reference analysis, and inconsistent price linkage are
  data errors, not `판단 보류`.
- original v1 analysis and derived v1.1 evaluation are labeled separately.
- user-facing `기업등급` is Quant business quality, while `투자등급` is attractiveness at
  the evaluation price; internal field names and policy contracts remain unchanged.
- the compact state label is derived from stored provenance: synthetic inputs are
  `예시 데이터`, and persisted DEMO/VALIDATION assumptions are `검증용 가정`.
- absent Current/Narrative/Thesis data remains `미제공 / 미해결`; UNKNOWN flags never
  become confirmed NO.
- comparison appears only when two valid stored evaluations have the existing structured
  comparison result.

The only action is `저장 결과 다시 읽기`, which rereads the same local files. It does not
refresh prices or revalue an analysis.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/test_read_only_watchlist.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
git diff --check
```

Tests use synthetic temporary storage and require neither the local operating files nor a
Tiingo credential. Real SQLite, JSONL, provider responses, and secrets must remain outside
Git.

Local validation on 2026-09-06:

- focused watchlist plus documentation checks: 24 passed
- full offline suite: 468 passed
- desktop browser: summary, TEM detail/comparison, and reload PASS
- 390 x 844 browser viewport: vertical card layout and zero horizontal overflow PASS
- existing live-validation files: stored STRL/TEM/LPTH values, detail, and reload PASS;
  source hashes unchanged
- external provider/write/revalue/seed boundary: guarded by regression tests; PASS

M12-B1 remains `BLOCKED`. Production EOD ingestion, an API, remote/mobile hosting, alerts,
and write controls remain unimplemented.
