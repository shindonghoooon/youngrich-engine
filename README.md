# YoungRich Engine

기업을 경제구조에 따라 분류하고, **고정된 Quant Core + Valuation + Narrative**를 결합해
투자 매력도와 실제 성과를 추적하는 주식 분석 엔진입니다.

## 핵심 원칙

1. 기업별 특이사항 때문에 Quant 지표를 추가하지 않는다.
2. Case는 기업의 영구 분류가 아니라 **현재 투자 아이디어의 경제구조**를 나타낸다.
3. Quant Quality와 Investment Grade를 분리한다.
4. 산업 특성은 Core 지표 추가가 아니라 **Capital Model benchmark**로 조정한다.
5. Narrative는 Quant 점수를 수정하지 않는다.
6. Valuation은 기업의 질과 별도로 평가한다.
7. 분석 결과는 구조화된 데이터로 저장하고 Dashboard / 1-page Report는 그 결과를 렌더링한다.
8. 장기적으로 실제 수익률과 Thesis 적중률을 측정해 분석 로직을 검증한다.

## Cases

1. Profitable Growth
2. Loss-making Growth
3. Cyclical / Mean Reversion
4. Quality Compounder
5. Large-cap Value / Mature Quality
6. Asset / Special Situation

현재 **Case 1: Profitable Growth**만 Quant Engine v1 초안이 정의되어 있습니다.

## Architecture

```text
Stock
  ↓
Case Router
  ↓
Capital Model
  ↓
Case Quant Engine
  ↓
Quant Quality
  ├── Valuation
  ├── Narrative
  └── Risk / Tracking
        ↓
Investment Grade
        ↓
SQLite
  ├── Dashboard
  └── 1-page Report
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python -m app.demo
```

Dashboard:

```bash
streamlit run dashboard/app.py
```

## Project Status

- [x] Overall architecture
- [x] Six-case taxonomy
- [x] Case 1 Quant Core 8
- [x] Capital Model concept
- [x] Structured analysis schema
- [ ] Case 1 scoring calibration
- [x] Router precedence smoke test
- [x] Cash Economics v1
- [ ] Router v1 calibration
- [ ] Valuation engine
- [ ] Narrative evaluation format
- [ ] Case 2–6 engines
- [ ] Performance tracking / backtest
- [ ] Automated 1-page report
