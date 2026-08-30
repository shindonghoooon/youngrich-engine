PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stocks (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    exchange TEXT,
    sector TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    as_of TEXT NOT NULL,
    case_type TEXT NOT NULL,
    capital_model TEXT,
    quant_score REAL,
    quant_grade TEXT,
    investment_grade TEXT,
    expectation_gap TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES stocks(ticker)
);

CREATE TABLE IF NOT EXISTS metric_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value REAL,
    unit TEXT,
    grade TEXT NOT NULL,
    trend TEXT,
    weight REAL NOT NULL,
    note TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);

CREATE TABLE IF NOT EXISTS valuations (
    analysis_id INTEGER PRIMARY KEY,
    current_price REAL,
    bear_value REAL,
    base_value REAL,
    bull_value REAL,
    status TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);

CREATE TABLE IF NOT EXISTS narratives (
    analysis_id INTEGER PRIMARY KEY,
    why_growth TEXT,
    why_continue TEXT,
    why_this_company TEXT,
    market_missing TEXT,
    thesis_break TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);

CREATE TABLE IF NOT EXISTS tracking_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    source TEXT,
    upgrade_condition TEXT,
    downgrade_condition TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    horizon_days INTEGER NOT NULL,
    stock_return REAL,
    benchmark_return REAL,
    alpha REAL,
    max_drawdown REAL,
    measured_at TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);
