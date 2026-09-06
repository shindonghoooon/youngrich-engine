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

The only action is `저장본 다시 불러오기`, which rereads the same local files. It does not
refresh prices or revalue an analysis.

## UI/UX display pass

The investment-review view changes presentation only. It does not change frozen
calculation, grade, reason-code, snapshot, or persistence contracts.

- Case labels are shown as **Case 1 · 흑자 성장** and **Case 2 · 비대칭 성장**.
- **핵심 평가 지표** contains Core metrics. **참고 지표** contains Supporting metrics.
  A resolved Supporting metric without a grade is shown as **참고 지표 · 등급 미부여**,
  not as unresolved.
- **자료 부족**, **적용 대상 아님**, and an intentionally ungraded Supporting metric
  are separate display states.
- **최근 실적 추세** is explicitly separate from **기업등급**. The UI shows the stored
  period end and says **비교기간 정보 없음** when no exact comparison interval is
  stored; it never invents year-over-year or quarter-over-quarter scope.
- Stored provenance drives the small **검증 데이터**, **검증용 가정**, and
  **예시 데이터** labels. A real market price does not make the whole analysis
  production-ready.
- Summary cards omit policy strings, IDs, and exact timestamps. Those values, raw metric
  values, and reason codes remain available in **모델·원본 정보**.

Formatting is metric-semantic rather than based on a generic ratio unit. Growth,
dilution, capital-efficiency, and per-share values are percentages; Cash Economics,
Balance Sheet, and numeric Cash Burn values are multiples; margin changes preserve the
Case-specific percentage-point contract; runway is months. Formatting never mutates or
rounds a stored value used by comparison or calculation, and zero remains distinct from
missing.

The summary uses a CSS grid: one column below 768 CSS pixels, two columns from 768 through
1199, and three from 1200 upward. Grade and reason text wraps instead of truncating.
Declared normal-text color pairs meet a 4.5:1 contrast ratio.

## Investment decision trace (P0)

Every READY card shows four short **판단 근거** rows below the two grades. The detail
view separates the recorded **가치평가 초기 판단**, business/Narrative/Current/funding/
confidence/breaker evidence, **최종 투자등급**, and actual **판정 제한**. Price and
financial-period information follows the decision path.

The immutable display-only projection uses the saved evaluation and reference analysis.
It never reapplies a policy, derives intermediate grades, or invents a cap from a Quant
grade. Active adjustments retain their stored sequence; inactive records and raw codes
remain available in **판정 근거 자세히**. An absent adjustment means **추가 판정 제한
기록 없음**, not a passing check. Missing funding evidence remains UNKNOWN.

The stored examples distinguish:

- STRL: business analysis complete / company grade A; valuation assumptions absent.
- TEM: initial B and final B; the recorded confidence cap B is not portrayed as the sole
  cause of the grade.
- LPTH: valuation calculated, but **가치평가 조합의 등급 기준 미정의**. The structured
  unresolved reason does not authorize inventing a funding, dilution, or revenue cause.

Initial and final grades stay visible even when equal. Labels stay short on cards;
long explanations and original reason codes are available in detail. This is a
presentation contract, not a new Investment Grade or persistence version.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests/test_read_only_watchlist.py -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
git diff --check
```

Tests use synthetic temporary storage and require neither the local operating files nor a
Tiingo credential. Real SQLite, JSONL, provider responses, and secrets must remain outside
Git.

UI/UX-pass validation on 2026-09-06:

- focused watchlist UI tests: 28 passed
- full offline suite: 479 passed
- desktop browser: summary, detail, keyboard selection/reload/expander PASS
- 320, 375, 768, 1024, and 1440 CSS-pixel browser checks: expected 1/1/2/2/3 card
  columns, zero document horizontal overflow, and no grade/reason overflow
- 200% text-size check at 375 CSS pixels: zero document horizontal overflow and no
  grade/reason overflow
- existing live-validation files: stored STRL/TEM/LPTH values, detail, and reload PASS;
  source hashes unchanged
- external provider/write/revalue/seed boundary: guarded by regression tests; PASS

Decision-trace follow-up validation on 2026-09-06:

- focused watchlist tests: 32 passed; full offline suite: 483 passed
- initial/final equality and difference, stored cap order, missing-adjustment semantics,
  STRL/TEM/LPTH reason distinctions, and source-model invariance: PASS
- actual stored results in the local browser: decision summaries and LPTH detail PASS
- 320/375/768/1024/1440 CSS-pixel checks: 1/1/2/2/3 columns; no horizontal or
  grade/reason/decision-trace overflow; 200% text-size check at 375 pixels: PASS
- existing SQLite/JSONL source hashes unchanged after browser reads; no API, seed,
  revalue, calculation, or storage write added

M12-B1 remains `BLOCKED`. Production EOD ingestion, an API, remote/mobile hosting, alerts,
and write controls remain unimplemented.
