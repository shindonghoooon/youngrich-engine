"""Research-time curator for the offline historical stress basket.

This script is intentionally networked and is never imported by pytest. It freezes SEC
filing timestamps and Yahoo Finance daily chart observations into deterministic JSON.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests" / "fixtures" / "performance_historical"
RETRIEVED_AT = "2026-09-04T12:00:00Z"
SEC_USER_AGENT = "youngrich-engine historical-calibration research@example.com"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

SAMPLES = (
    ("adbe_fy2017", "ADBE", "Adobe", "case1_profitable_growth", "2017-12-01", "0000796343", "B", "CALIBRATION"),
    ("adbe_fy2021", "ADBE", "Adobe", "case1_profitable_growth", "2021-12-03", "0000796343", "D", "CALIBRATION"),
    ("pypl_fy2021", "PYPL", "PayPal", "case1_profitable_growth", "2021-12-31", "0001633917", "C", "CALIBRATION"),
    ("nvda_fy2018", "NVDA", "NVIDIA", "case1_profitable_growth", "2018-01-28", "0001045810", "B", "SUPPORTING_BOUNDARY"),
    ("pltr_fy2021", "PLTR", "Palantir", "case2_emerging_asymmetric_growth", "2021-12-31", "0001321655", "B", "CALIBRATION"),
    ("crwd_fy2020", "CRWD", "CrowdStrike", "case2_emerging_asymmetric_growth", "2020-01-31", "0001535527", "B", "CALIBRATION"),
    ("net_fy2020", "NET", "Cloudflare", "case2_emerging_asymmetric_growth", "2020-12-31", "0001477333", "C", "CALIBRATION"),
    ("shop_fy2015", "SHOP", "Shopify", "case2_emerging_asymmetric_growth", "2015-12-31", "0001594805", "B", "CALIBRATION"),
    ("tsla_fy2014", "TSLA", "Tesla", "case2_emerging_asymmetric_growth", "2014-12-31", "0001318605", "C", "CALIBRATION"),
    ("mdb_fy2020", "MDB", "MongoDB", "case2_emerging_asymmetric_growth", "2020-01-31", "0001441816", "B", "CALIBRATION"),
    ("fsly_fy2021", "FSLY", "Fastly", "case2_emerging_asymmetric_growth", "2021-12-31", "0001517413", "D", "CALIBRATION"),
    ("sklz_fy2021", "SKLZ", "Skillz", "case2_emerging_asymmetric_growth", "2021-12-31", "0001801661", "D", "CALIBRATION"),
    ("vldr_fy2020", "VLDR", "Velodyne Lidar", "case2_emerging_asymmetric_growth", "2020-12-31", "0001745317", None, "CALIBRATION"),
)


def _json(url: str, *, sec: bool = False) -> dict:
    headers = {"User-Agent": SEC_USER_AGENT if sec else "Mozilla/5.0"}
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def filing(cik: str, report_date: str) -> dict:
    root_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    root = _json(root_url, sec=True)
    blocks = [root["filings"]["recent"]]
    block_urls = []
    for item in root["filings"].get("files", []):
        url = f"https://data.sec.gov/submissions/{item['name']}"
        block_urls.append(url)
        blocks.append(_json(url, sec=True))
    for block in blocks:
        for index, (form, period) in enumerate(zip(block["form"], block["reportDate"], strict=True)):
            if form in {"10-K", "20-F", "40-F"} and period == report_date:
                accession = block["accessionNumber"][index]
                primary = block["primaryDocument"][index]
                accession_path = accession.replace("-", "")
                cik_path = str(int(cik))
                return {
                    "form": form,
                    "report_date": period,
                    "filing_date": block["filingDate"][index],
                    "accepted_at": block["acceptanceDateTime"][index],
                    "accession_number": accession,
                    "primary_document": primary,
                    "source_url": f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accession_path}/{primary}",
                    "submission_index_url": root_url,
                    "submission_archive_urls": block_urls,
                }
    raise LookupError(f"filing not found for CIK {cik} report date {report_date}")


def chart(ticker: str, start: date, end: date) -> tuple[list[dict], str]:
    period1 = int(datetime.combine(start, time.min, timezone.utc).timestamp())
    period2 = int(datetime.combine(end + timedelta(days=1), time.min, timezone.utc).timestamp())
    query = urlencode({"period1": period1, "period2": period2, "interval": "1d", "events": "history,splits"})
    url = f"{YAHOO_CHART.format(ticker=ticker)}?{query}"
    payload = _json(url)["chart"]["result"][0]
    timestamps = payload.get("timestamp", [])
    quote = payload["indicators"]["quote"][0]
    rows = []
    exchange = ZoneInfo("America/New_York")
    for stamp, close in zip(timestamps, quote["close"], strict=True):
        if close is None:
            continue
        session_date = datetime.fromtimestamp(stamp, timezone.utc).astimezone(exchange).date()
        close_at = datetime.combine(session_date, time(16), exchange).astimezone(timezone.utc)
        rows.append({"timestamp": close_at.isoformat().replace("+00:00", "Z"), "price": close})
    return rows, url


def first_after(rows: list[dict], accepted_at: datetime) -> dict:
    return next(row for row in rows if datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) > accepted_at)


def first_on_or_after(rows: list[dict], target: date) -> dict:
    return next(row for row in rows if date.fromisoformat(row["timestamp"][:10]) >= target)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for sample_id, ticker, company, case, report_date, cik, grade, role in SAMPLES:
        filing_data = filing(cik, report_date)
        accepted_at = datetime.fromisoformat(filing_data["accepted_at"].replace("Z", "+00:00"))
        stock_error = None
        try:
            stock_rows, stock_url = chart(ticker, accepted_at.date(), accepted_at.date() + timedelta(days=390))
            reference = first_after(stock_rows, accepted_at)
            reference_at = datetime.fromisoformat(reference["timestamp"].replace("Z", "+00:00"))
            one_year_target = date(reference_at.year + 1, reference_at.month, reference_at.day)
            evaluation = first_on_or_after(stock_rows, one_year_target)
            evaluation_at = datetime.fromisoformat(evaluation["timestamp"].replace("Z", "+00:00"))
            stock_rows = [row for row in stock_rows if reference_at <= datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) <= evaluation_at]
            benchmark_rows, benchmark_url = chart("SPY", accepted_at.date(), accepted_at.date() + timedelta(days=390))
            benchmark_reference = next((row for row in benchmark_rows if row["timestamp"] == reference["timestamp"]), None)
            benchmark_rows = [row for row in benchmark_rows if reference_at <= datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) <= evaluation_at]
        except (HTTPError, LookupError, StopIteration) as error:
            stock_error = f"{type(error).__name__}: {error}"
            stock_url = YAHOO_CHART.format(ticker=ticker)
            benchmark_url = YAHOO_CHART.format(ticker="SPY")
            stock_rows, benchmark_rows = [], []
            reference = evaluation = benchmark_reference = None
        fixture = {
            "schema_version": "historical-performance-stress-v0.1",
            "sample_id": sample_id,
            "ticker": ticker,
            "company": company,
            "historical_case": case,
            "sample_role": role,
            "reporting_period_end": report_date,
            "information_available_at": filing_data["accepted_at"],
            "analysis_as_of": filing_data["accepted_at"],
            "analysis_input_state": "ANALYSIS_INPUT_INCOMPLETE",
            "canonical_investment_grade": grade,
            "canonical_grade_range": ["D", "X"] if sample_id == "vldr_fy2020" else None,
            "expectation_gap": "negative" if sample_id == "adbe_fy2021" else None,
            "funding_stress": None,
            "commercial_inflection": None,
            "thesis_status": None,
            "analysis_provenance": filing_data,
            "reference_price": ({
                "timestamp": reference["timestamp"], "price": reference["price"],
                "timing_rule": "first provider EOD close timestamp strictly after SEC acceptance",
            } if reference else None),
            "evaluation_as_of": evaluation["timestamp"] if evaluation else None,
            "price_basis": "split_adjusted",
            "return_type": "price_return",
            "currency": "USD",
            "adjustment_version": "yahoo_chart_v8_split_adjusted_2026-09-04",
            "price_source": {"provider": "Yahoo Finance Chart API", "stock_url": stock_url,
                             "retrieved_at": RETRIEVED_AT,
                             "error": stock_error,
                             "note": "Provider chart OHLC close series frozen offline; treated as split-adjusted price return, not total return."},
            "benchmark_assignment": {"ticker": "SPY", "version": 1,
                                     "valid_from": filing_data["accepted_at"],
                                     "rationale": "Explicit US broad-market benchmark for curated stress calibration",
                                     "source_url": benchmark_url,
                                     "reference_timestamp": benchmark_reference["timestamp"] if benchmark_reference else None,
                                     "reference_price": benchmark_reference["price"] if benchmark_reference else None},
            "stock_prices": stock_rows,
            "benchmark_prices": benchmark_rows,
            "notes": [
                "Outcome-aware curated sample; not an unbiased strategy backtest.",
                "Canonical grade comes from preserved project instruction; detailed historical Quant/Narrative inputs are incomplete.",
            ],
        }
        path = OUTPUT / f"{sample_id}.json"
        path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
        manifest.append({"sample_id": sample_id, "path": path.name})
        print(sample_id, filing_data["accepted_at"], reference["timestamp"] if reference else "UNRESOLVED", len(stock_rows))
    (OUTPUT / "manifest.json").write_text(json.dumps({"schema_version": "historical-performance-stress-v0.1", "samples": manifest}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
