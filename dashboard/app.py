import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="YoungRich Engine", layout="wide")
st.title("YoungRich Engine")
st.caption("Quant Quality + Valuation + Narrative")

example = Path("data/examples/STRL.example.json")

if not example.exists():
    st.info("No example analysis found.")
    st.stop()

data = json.loads(example.read_text(encoding="utf-8"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ticker", data["ticker"])
c2.metric("Case", data["case"])
c3.metric("Quant", data.get("quant_grade") or "-")
c4.metric("Investment", data.get("investment_grade") or "-")

st.subheader("Quant Core")
rows = []
for m in data["metrics"]:
    rows.append({
        "Metric": m["name"],
        "Value": m.get("value"),
        "Grade": m["grade"],
        "Trend": m.get("trend"),
        "Weight": m["weight"],
    })
st.dataframe(rows, use_container_width=True)

st.subheader("Narrative")
n = data.get("narrative") or {}
for key in ["why_growth", "why_continue", "why_this_company", "market_missing", "thesis_break"]:
    st.markdown(f"**{key.replace('_', ' ').title()}**")
    st.write(n.get(key) or "-")

st.subheader("Tracking")
for t in data.get("tracking", []):
    st.write(f"- {t['name']}")
