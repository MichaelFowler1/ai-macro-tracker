import os
import streamlit as st
import altair as alt
import pandas as pd
from dotenv import load_dotenv

# Import your custom data extractors
from macro_tracker import fetch_all_macro_data
from bls_extractor import fetch_bls_data
from nyfed_extractor import fetch_college_labor_data

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

@st.cache_data(ttl=24 * 3600)  # NY Fed updates quarterly; re-download at most daily
def load_nyfed_data():
    try:
        return fetch_college_labor_data()
    except Exception as e:
        print(f"Warning: NY Fed college labor data unavailable. Error: {e}")
        return None

# Load the raw data
raw_macro_data = load_macro_data()
raw_tech_layoffs, raw_tech_openings = load_bls_tech_data()
raw_nyfed_data = load_nyfed_data()

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
w_underemp = st.sidebar.slider("Grad Underemployment (+)", 0.0, 2.0, 1.0, 0.1)

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

nyfed_unemp = pd.DataFrame()
nyfed_underemp = pd.DataFrame()
nyfed_majors = pd.DataFrame()
if raw_nyfed_data is not None:
    nyfed_unemp = raw_nyfed_data["unemployment"]
    nyfed_unemp = nyfed_unemp[nyfed_unemp.index >= start_datetime]
    nyfed_underemp = raw_nyfed_data["underemployment"]
    nyfed_underemp = nyfed_underemp[nyfed_underemp.index >= start_datetime]
    nyfed_majors = raw_nyfed_data["majors"]

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

def plot_multiline_chart(df, y_title=""):
    """Line chart comparing several series from one DataFrame."""
    if df.empty:
        st.warning("No data available for this timeframe.")
        return

    long_df = df.reset_index().melt("Date", var_name="Series", value_name="Value")
    chart = alt.Chart(long_df).mark_line().encode(
        x=alt.X("Date:T", title=""),
        y=alt.Y("Value:Q", title=y_title, scale=alt.Scale(zero=False)),
        color=alt.Color("Series:N", legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Date:T", "Series:N", alt.Tooltip("Value:Q", format=".2f")]
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
    index_factors = {
        'tech': normalize_series(macro_data["total_tech_investment"]) * w_tech,
        'prod': normalize_series(macro_data["productivity"]) * w_prod,
        'jobs': -normalize_series(macro_data["job_openings_rate"]) * w_jobs,
        'unemp': normalize_series(macro_data["grad_unemp"]) * w_unemp,
        'wage': -normalize_series(macro_data["wages"]) * w_wage,
        'prof': normalize_series(macro_data["profits"]) * w_prof
    }
    # Underemployment (grads stuck in jobs not requiring a degree) captures
    # displacement that never shows up in the unemployment rate.
    if not nyfed_underemp.empty:
        index_factors['underemp'] = normalize_series(nyfed_underemp["Recent graduates"]) * w_underemp

    df_index = pd.DataFrame(index_factors).dropna()
    df_index['Dynamic_Risk_Score'] = df_index.sum(axis=1)
except KeyError:
    st.error("Missing expected data keys. Check API limits or variable names.")
    st.stop()

# --- MAIN UI ---
st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

n_factors = len(index_factors)
st.header("The AI Displacement Risk Index (Dynamic)")
st.write(f"A composite index tracking {n_factors} macro-factors. **Rising values** indicate labor losing leverage to tech capital.")

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

st.subheader("Unemployment by Education & Age (FRED)")
st.write(
    "Does more education still protect you? If AI is eating entry-level knowledge work, "
    "the youngest bachelor's cohort should decouple from the older and more credentialed ones. "
    "Series are not seasonally adjusted, so a 3-month moving average is applied to cut the noise."
)
edu_ladder = pd.DataFrame({
    "Bachelor's, 20-24": macro_data["grad_unemp"],
    "Bachelor's, 25-34": macro_data["grad_unemp_2534"],
    "Bachelor's, 25+": macro_data["grad_unemp_25o"],
    "Master's, 25+": macro_data["master_unemp_25o"],
}).rolling(3).mean().dropna(how="all")
edu_ladder.index.name = "Date"
plot_multiline_chart(edu_ladder, "Unemployment Rate (%, 3-mo MA)")

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

st.write("---")

# --- ROW 4: THE GRADUATE SQUEEZE (NY FED) ---
st.header("Phase 4: The Graduate Squeeze (NY Fed)")
st.write(
    "From the NY Fed's [Labor Market for Recent College Graduates]"
    "(https://www.newyorkfed.org/research/college-labor-market). "
    "Recent grads are the canary: entry-level roles are the first to be automated away."
)

if raw_nyfed_data is None:
    st.warning("Awaiting NY Fed Data... (download failed; dashboard is running without it)")
else:
    c9, c10 = st.columns(2)

    with c9:
        st.subheader("Unemployment: Grads vs. Everyone")
        st.write("Historically recent grads ran *below* all workers. The inversion is the story.")
        plot_multiline_chart(nyfed_unemp[["Recent graduates", "All workers"]], "Unemployment Rate (%)")
        if not nyfed_unemp.empty:
            gap = nyfed_unemp["Recent graduates"].iloc[-1] - nyfed_unemp["All workers"].iloc[-1]
            st.metric("Grad Gap (Recent Grads − All Workers)", f"{gap:+.2f} pts",
                      "Grads doing worse than average" if gap > 0 else "Grads doing better than average",
                      delta_color="inverse" if gap > 0 else "normal")

    with c10:
        st.subheader("Grad Underemployment")
        st.write("Share of recent grads in jobs that don't require a degree.")
        if not nyfed_underemp.empty:
            plot_locked_chart(nyfed_underemp["Recent graduates"], "#d62728", "Underemployment Rate (%)")
            change = get_yoy_change(nyfed_underemp["Recent graduates"], periods=12)
            st.metric("Latest Rate", f"{nyfed_underemp['Recent graduates'].iloc[-1]:.1f}%",
                      f"{change:.2f}% YoY" if change else "N/A", delta_color="inverse")

    st.subheader("Unemployment by Major: Is Tech Still a Safe Bet?")
    if not nyfed_majors.empty:
        majors_df = nyfed_majors.reset_index()
        tech_majors = ["Computer Science", "Computer Engineering", "Information Systems & Management"]
        overall_rate = nyfed_majors.loc["Overall", "Unemployment Rate"] if "Overall" in nyfed_majors.index else None

        top = majors_df[majors_df["Major"] != "Overall"].nlargest(15, "Unemployment Rate")
        top["Group"] = top["Major"].apply(lambda m: "Tech" if m in tech_majors else "Other")

        bars = alt.Chart(top).mark_bar().encode(
            x=alt.X("Unemployment Rate:Q", title="Unemployment Rate (%)"),
            y=alt.Y("Major:N", sort="-x", title=""),
            color=alt.Color("Group:N",
                            scale=alt.Scale(domain=["Tech", "Other"], range=["#d62728", "#9e9e9e"]),
                            legend=None),
            tooltip=["Major:N", alt.Tooltip("Unemployment Rate:Q", format=".2f"),
                     alt.Tooltip("Underemployment Rate:Q", format=".2f"),
                     alt.Tooltip("Median Wage Early Career:Q", format="$,.0f")]
        ).properties(height=400)

        if overall_rate is not None:
            rule = alt.Chart(pd.DataFrame({"x": [overall_rate]})).mark_rule(
                color="#673ab7", strokeDash=[6, 4]
            ).encode(x="x:Q")
            bars = bars + rule
            st.write(f"Top 15 majors by unemployment rate. Dashed line = overall average ({overall_rate:.1f}%). Tech majors in red.")
        st.altair_chart(bars, width="stretch")