import os
import streamlit as st
import altair as alt
import pandas as pd
from dotenv import load_dotenv

# Import your custom data extractors
from macro_tracker import fetch_all_macro_data
from bls_extractor import fetch_bls_data

# Load environment variables
load_dotenv()
st.set_page_config(page_title="AI Job Impact Tracker", layout="wide")

# --- DATA LOADING & SETUP ---
API_KEY = os.getenv("FRED_API_KEY")
if not API_KEY:
    st.error("FRED API Key not found in .env. Please check your credentials.")
    st.stop()

@st.cache_data
def load_macro_data():
    return fetch_all_macro_data(API_KEY)

@st.cache_data
def load_bls_tech_data():
    layoffs = fetch_bls_data('JTS510000000000000LDL')  # Information Sector Layoffs
    openings = fetch_bls_data('JTS510000000000000JOL') # Information Sector Job Openings
    
    # Format for the helper functions
    if not layoffs.empty:
        layoffs.set_index('Date', inplace=True)
        layoffs = layoffs['Value_in_Thousands']
        
    if not openings.empty:
        openings.set_index('Date', inplace=True)
        openings = openings['Value_in_Thousands']
        
    return layoffs, openings

# Load the raw data
raw_macro_data = load_macro_data()
raw_tech_layoffs, raw_tech_openings = load_bls_tech_data()

# --- SIDEBAR INTERACTIVITY ---
st.sidebar.title("Dashboard Controls")

st.sidebar.header("1. Timeline Filter")
st.sidebar.write("Filter data to observe the post-LLM acceleration.")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2022-11-01"))
start_datetime = pd.to_datetime(start_date)

st.sidebar.header("2. Index Weights")
st.sidebar.write("Adjust the importance of each pillar in the composite Risk Index.")
w_tech = st.sidebar.slider("Tech Investment (+)", 0.0, 2.0, 1.0, 0.1)
w_prod = st.sidebar.slider("Productivity (+)", 0.0, 2.0, 1.0, 0.1)
w_jobs = st.sidebar.slider("Job Openings Rate (-)", 0.0, 2.0, 1.0, 0.1)
w_unemp = st.sidebar.slider("Grad Unemployment (+)", 0.0, 2.0, 1.0, 0.1)
w_wage = st.sidebar.slider("Wage Growth (-)", 0.0, 2.0, 1.0, 0.1)
w_prof = st.sidebar.slider("Corporate Profits (+)", 0.0, 2.0, 1.0, 0.1)

# --- APPLY FILTERS ---
macro_data = {}
for key, series in raw_macro_data.items():
    macro_data[key] = series[series.index >= start_datetime]

tech_layoffs = pd.Series(dtype=float)
if not raw_tech_layoffs.empty:
    tech_layoffs = raw_tech_layoffs[raw_tech_layoffs.index >= start_datetime]

tech_openings = pd.Series(dtype=float)
if not raw_tech_openings.empty:
    tech_openings = raw_tech_openings[raw_tech_openings.index >= start_datetime]

# --- HELPER FUNCTIONS ---
def plot_locked_chart(series_data, line_color, title=""):
    """Generates a clean Altair line chart."""
    if series_data.empty:
        st.warning("No data available for this timeframe.")
        return
        
    df = series_data.reset_index()
    df.columns = ["Date", "Value"] 
    chart = alt.Chart(df).mark_line(color=line_color).encode(
        x=alt.X("Date:T", title=""),      
        y=alt.Y("Value:Q", title=title, scale=alt.Scale(zero=False)),
        tooltip=["Date:T", "Value:Q"] 
    )
    st.altair_chart(chart, width="stretch")

def get_yoy_change(series, periods=4):
    """Calculates YoY % change safely using Pandas native methods."""
    try:
        if len(series) < periods + 1:
            return 0
        change = series.pct_change(periods=periods).iloc[-1] * 100
        return change
    except Exception:
        return 0

def normalize_series(series):
    """Converts raw data to Z-scores so distinct units can be combined."""
    if series.std() == 0 or len(series) < 2: 
        return series * 0
    return (series - series.mean()) / series.std()

# --- DYNAMIC INDEX CALCULATION ---
try:
    df_index = pd.DataFrame({
        'tech': normalize_series(macro_data["total_tech_investment"]) * w_tech,
        'prod': normalize_series(macro_data["productivity"]) * w_prod,
        'jobs': -normalize_series(macro_data["job_openings_rate"]) * w_jobs, 
        'unemp': normalize_series(macro_data["grad_unemp"]) * w_unemp,
        'wage': -normalize_series(macro_data["wages"]) * w_wage, 
        'prof': normalize_series(macro_data["profits"]) * w_prof
    }).dropna()
    
    df_index['Dynamic_Risk_Score'] = df_index.sum(axis=1)
except KeyError:
    st.error("Missing expected data keys. Check API limits or variable names.")
    st.stop()

# --- MAIN UI ---
st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

st.header("The AI Displacement Risk Index (Dynamic)")
st.write("A composite index tracking 6 macro-factors. **Rising values** indicate labor losing leverage to tech capital.")

if not df_index.empty:
    idx_df = df_index['Dynamic_Risk_Score'].reset_index()
    idx_df.columns = ["Date", "Value"]
    index_chart = alt.Chart(idx_df).mark_area(
        color="#673ab7", line={'color': '#4527a0'}, opacity=0.3
    ).encode(
        x=alt.X("Date:T", title=""),
        y=alt.Y("Value:Q", title="Relative Risk Score", scale=alt.Scale(zero=False)),
        tooltip=["Date:T", alt.Tooltip("Value:Q", format=".2f")]
    ).properties(height=350) 
    st.altair_chart(index_chart, width="stretch")
else:
    st.warning("Not enough data points in this timeframe to calculate the index.")

st.write("---")

# --- ROW 1: THE CORE PILLARS ---
st.header("Phase 1: Capital & Demand (Macro)")
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("Tech Investment")
    plot_locked_chart(macro_data["total_tech_investment"], "#1f77b4")
with c2:
    st.subheader("Labor Productivity")
    plot_locked_chart(macro_data["productivity"], "#ff7f0e")
with c3:
    st.subheader("Job Openings Rate")
    plot_locked_chart(macro_data["job_openings_rate"], "#2ca02c")

st.write("---")

# --- ROW 2: THE LABOR BLEED ---
st.header("Phase 2: Labor & Profit Health (Macro)")
c4, c5, c6 = st.columns(3)

with c4:
    st.subheader("Recent Grad Unemployment")
    plot_locked_chart(macro_data["grad_unemp"], "#9467bd")
    change = get_yoy_change(macro_data["grad_unemp"], periods=4) 
    st.metric("Latest Rate", f"{macro_data['grad_unemp'].iloc[-1]:.1f}%", f"{change:.2f}% YoY" if change else "N/A")

with c5:
    st.subheader("Wage Levels")
    plot_locked_chart(macro_data["wages"], "#8c564b")
    change = get_yoy_change(macro_data["wages"], periods=12) 
    st.metric("Avg Hourly", f"${macro_data['wages'].iloc[-1]:.2f}", f"{change:.2f}% YoY" if change else "N/A")

with c6:
    st.subheader("Corporate Profits")
    plot_locked_chart(macro_data["profits"], "#e377c2")
    change = get_yoy_change(macro_data["profits"], periods=4) 
    st.metric("Total Profits", f"${macro_data['profits'].iloc[-1]:.1f}B", f"{change:.2f}% YoY" if change else "N/A")

st.write("---")

# --- ROW 3: MICRO-TRENDS (TECH SECTOR VULNERABILITY) ---
st.header("Phase 3: Sector-Specific Tech Labor (Micro)")
st.write("Tracking the 'Information Sector' (Software, Data, Web) directly via BLS.")

c7, c8 = st.columns(2)

with c7:
    st.subheader("Tech Layoffs (Thousands)")
    st.write("Information Sector Discharges")
    if not tech_layoffs.empty:
        plot_locked_chart(tech_layoffs, "#d62728") 
        change = get_yoy_change(tech_layoffs, periods=12)
        # delta_color="inverse" makes an upward trend show as RED, since higher layoffs are bad
        st.metric("Latest Monthly Layoffs", f"{tech_layoffs.iloc[-1]}k", f"{change:.2f}% YoY" if change else "N/A", delta_color="inverse")
    else:
        st.warning("Awaiting BLS Data...")

with c8:
    st.subheader("Tech Job Openings (Thousands)")
    st.write("Information Sector Hiring Demand")
    if not tech_openings.empty:
        plot_locked_chart(tech_openings, "#2ca02c") 
        change = get_yoy_change(tech_openings, periods=12)
        st.metric("Latest Openings", f"{tech_openings.iloc[-1]}k", f"{change:.2f}% YoY" if change else "N/A")
    else:
        st.warning("Awaiting BLS Data...")