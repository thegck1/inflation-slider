# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Inflation vs Commodity Price", layout="wide")
st.title("Inflation-adjusted commodity price (Nominal vs Real)")

# --- Choose series (defaults: WTI + CPI) ---
commodity_series = st.text_input("FRED commodity series ID", value="WTISPLC")  # WTI monthly
cpi_series = st.text_input("FRED CPI series ID", value="CPIAUCNS")            # CPI-U NSA

st.caption("Tip: Try other commodities too (e.g., GASREGCOVW for US gasoline retail, if available in FRED).")

@st.cache_data(show_spinner=False)
def fetch_fred_csv(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date")
    return df

with st.spinner("Downloading data from FRED..."):
    commodity = fetch_fred_csv(commodity_series)
    cpi = fetch_fred_csv(cpi_series)

# Align to monthly (WTISPLC is monthly already; CPI is monthly)
df = pd.merge_asof(
    commodity.sort_values("date"),
    cpi.sort_values("date"),
    on="date",
    direction="nearest",
    tolerance=pd.Timedelta("31D"),
    suffixes=("_commodity", "_cpi"),
).dropna()

# Build base-year selector from available years
years = sorted(df["date"].dt.year.unique())
base_year = st.slider("Base year for 'real' (inflation-adjusted) dollars", min_value=years[0], max_value=years[-1], value=years[-1])

# Use average CPI in the base year as the deflator anchor
base_cpi = df.loc[df["date"].dt.year == base_year, "value_cpi"].mean()
df["real_price"] = df["value_commodity"] * (base_cpi / df["value_cpi"])

# Optional date range filter (extra interactivity)
min_date, max_date = df["date"].min().date(), df["date"].max().date()
start, end = st.date_input("Date window", (min_date, max_date), min_value=min_date, max_value=max_date)
mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
dff = df.loc[mask].copy()

fig = go.Figure()
fig.add_trace(go.Scatter(x=dff["date"], y=dff["value_commodity"], mode="lines", name="Nominal price"))
fig.add_trace(go.Scatter(x=dff["date"], y=dff["real_price"], mode="lines", name=f"Real price ({base_year} dollars)"))

fig.update_layout(
    height=520,
    xaxis=dict(
        title="Date",
        rangeslider=dict(visible=True),   # <-- the slider
        type="date",
    ),
    yaxis=dict(title="Price"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)

st.plotly_chart(fig, use_container_width=True)

st.write("Data sources:")
st.write(f"- Commodity: FRED series {commodity_series}")
st.write(f"- Inflation: FRED series {cpi_series}")
