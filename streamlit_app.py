# streamlit_app.py
# Nominal vs Real GDP (and implicit GDP deflator) with an interactive time slider

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Nominal vs Real GDP", layout="wide")
st.title("Nominal vs Real GDP (with GDP Deflator)")

st.caption(
    "Default data source: FRED (US). "
    "Nominal GDP series = GDP, Real GDP series = GDPC1 (chained dollars)."
)

# --- Inputs ---
nominal_series = st.text_input("FRED series ID for NOMINAL GDP", value="GDP")
real_series = st.text_input("FRED series ID for REAL GDP", value="GDPC1")

colA, colB, colC = st.columns(3)
with colA:
    show_deflator = st.checkbox("Show GDP Deflator (Nominal/Real)", value=True)
with colB:
    show_indexed = st.checkbox("Also show indexed chart (Base=100)", value=False)
with colC:
    base_year = st.number_input("Base year for index (Base=100)", min_value=1900, max_value=2100, value=2012)

@st.cache_data(show_spinner=False)
def fetch_fred_csv(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    df = df.dropna().sort_values("date")
    return df

with st.spinner("Downloading GDP data from FRED..."):
    nom = fetch_fred_csv(nominal_series)
    real = fetch_fred_csv(real_series)

# Merge on date
df = pd.merge(nom, real, on="date", how="inner").dropna()

# Compute implicit GDP deflator (index-like, base depends on Real series construction)
# Deflator = (Nominal / Real) * 100
df["deflator"] = (df[nominal_series] / df[real_series]) * 100

# Optional index (Base=100 in a chosen year)
df["year"] = df["date"].dt.year
base_nom = df.loc[df["year"] == base_year, nominal_series].mean()
base_real = df.loc[df["year"] == base_year, real_series].mean()
base_defl = df.loc[df["year"] == base_year, "deflator"].mean()

if pd.notna(base_nom) and base_nom != 0:
    df["nominal_index"] = (df[nominal_series] / base_nom) * 100
else:
    df["nominal_index"] = pd.NA

if pd.notna(base_real) and base_real != 0:
    df["real_index"] = (df[real_series] / base_real) * 100
else:
    df["real_index"] = pd.NA

if pd.notna(base_defl) and base_defl != 0:
    df["deflator_index"] = (df["deflator"] / base_defl) * 100
else:
    df["deflator_index"] = pd.NA

# Date window filter
min_date, max_date = df["date"].min().date(), df["date"].max().date()
start, end = st.date_input(
    "Date window",
    (min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
dff = df.loc[mask].copy()

# ---- Main chart: Levels ----
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=dff["date"], y=dff[nominal_series],
    mode="lines", name=f"Nominal GDP ({nominal_series})"
))
fig.add_trace(go.Scatter(
    x=dff["date"], y=dff[real_series],
    mode="lines", name=f"Real GDP ({real_series})"
))

fig.update_layout(
    height=520,
    xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date"),
    yaxis=dict(title="GDP level (units depend on series)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.subheader("GDP Levels")
st.plotly_chart(fig, use_container_width=True)

# ---- Deflator chart ----
if show_deflator:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=dff["date"], y=dff["deflator"],
        mode="lines", name="Implicit GDP Deflator = (Nominal/Real)×100"
    ))
    fig2.update_layout(
        height=360,
        xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date"),
        yaxis=dict(title="Deflator (index-like)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.subheader("Inflation component (GDP Deflator)")
    st.plotly_chart(fig2, use_container_width=True)

# ---- Indexed chart (Base=100) ----
if show_indexed:
    if dff["nominal_index"].isna().all() or dff["real_index"].isna().all():
        st.warning(f"Could not compute index for base year {base_year} (no data in that year). Try another base year.")
    else:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=dff["date"], y=dff["nominal_index"],
            mode="lines", name=f"Nominal GDP index (Base {base_year}=100)"
        ))
        fig3.add_trace(go.Scatter(
            x=dff["date"], y=dff["real_index"],
            mode="lines", name=f"Real GDP index (Base {base_year}=100)"
        ))
        if show_deflator and not dff["deflator_index"].isna().all():
            fig3.add_trace(go.Scatter(
                x=dff["date"], y=dff["deflator_index"],
                mode="lines", name=f"Deflator index (Base {base_year}=100)"
            ))

        fig3.update_layout(
            height=420,
            xaxis=dict(title="Date", rangeslider=dict(visible=True), type="date"),
            yaxis=dict(title="Index (Base=100)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.subheader("Indexed view (shows divergence clearly)")
        st.plotly_chart(fig3, use_container_width=True)

st.markdown(
    """
**How to read it (quick):**
- **Nominal GDP** rises because of **real growth + inflation**  
- **Real GDP** rises because of **real output growth only**  
- The **gap** between them is captured by the **GDP deflator** (inflation in the whole economy)
"""
)

st.info("If you run this on Streamlit Cloud, add a requirements.txt with: streamlit, plotly, pandas")
