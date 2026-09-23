import os
import streamlit as st
import altair as alt
import pandas as pd
from dotenv import load_dotenv

# Import your custom data extractors
from macro_tracker import fetch_all_macro_data
from bls_extractor import fetch_bls_data
from nyfed_extractor import fetch_college_labor_data
from risk_index import FACTORS, BASELINE, factor_scores, contributions
from cps_extractor import load_exposure_table, exposed_share_index

# Load environment variables
load_dotenv()
st.set_page_config(page_title="AI Job Impact Tracker", layout="wide")

# --- DATA LOADING & SETUP ---
API_KEY = os.getenv("FRED_API_KEY")  # optional; without it FRED is read via the keyless CSV endpoint

# Every source publishes monthly at most, so re-download at most daily
@st.cache_data(ttl=24 * 3600)
def load_macro_data():
    return fetch_all_macro_data(API_KEY)

@st.cache_data(ttl=24 * 3600)
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
weights = {
    key: st.sidebar.slider(f"{label} ({'+' if sign > 0 else '-'})", 0.0, 2.0, 1.0, 0.1)
    for key, (label, sign, _, _) in FACTORS.items()
}

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

# --- DYNAMIC INDEX CALCULATION ---
# Scored on the full history (the baseline is fixed at 2015-2019), then cropped
# to the start date, so moving the date doesn't change any values.
index_sources = dict(raw_macro_data)
if raw_nyfed_data is not None:
    # Underemployment (grads stuck in jobs not requiring a degree) captures
    # displacement that never shows up in the unemployment rate.
    index_sources["underemp"] = raw_nyfed_data["underemployment"]["Recent graduates"]

all_scores = factor_scores(index_sources)
factor_shares = contributions(all_scores, weights)
factor_shares = factor_shares[factor_shares.index >= start_datetime]
risk_score = factor_shares.sum(axis=1)

# --- MAIN UI ---
st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

n_factors = all_scores.shape[1]
st.header("The AI Displacement Risk Index (Dynamic)")
st.write(
    f"The weighted average of {n_factors} factors, each measured in standard deviations from its "
    f"{BASELINE[0][:4]}-{BASELINE[1][:4]} average. **0 is the pre-pandemic normal** and +1 means "
    "labor is one standard deviation worse off than that. Dollar series are growth rates net of "
    "CPI inflation, so they don't trend up on their own."
)

if not risk_score.empty:
    idx_df = risk_score.reset_index()
    idx_df.columns = ["Date", "Value"]
    index_chart = alt.Chart(idx_df).mark_area(
        color="#673ab7", line={'color': '#4527a0'}, opacity=0.3
    ).encode(
        x=alt.X("Date:T", title=""),
        y=alt.Y("Value:Q", title="SDs from 2015-2019 normal", scale=alt.Scale(zero=False)),
        tooltip=["Date:T", alt.Tooltip("Value:Q", format=".2f")]
    ).properties(height=350) 
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#9e9e9e", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(index_chart + zero, width="stretch")

    latest = factor_shares.iloc[-1].rename(index={k: FACTORS[k][0] for k in FACTORS}).reset_index()
    latest.columns = ["Factor", "Contribution"]
    st.subheader(f"What's driving it ({factor_shares.index[-1]:%b %Y})")
    st.write("How much each factor adds to the latest reading. The bars sum to the index.")
    drivers = alt.Chart(latest).mark_bar().encode(
        x=alt.X("Contribution:Q", title="Contribution to index"),
        y=alt.Y("Factor:N", sort="-x", title=""),
        color=alt.condition(alt.datum.Contribution > 0, alt.value("#d62728"), alt.value("#2ca02c")),
        tooltip=["Factor:N", alt.Tooltip("Contribution:Q", format="+.2f")]
    ).properties(height=250)
    st.altair_chart(drivers, width="stretch")
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
    change = get_yoy_change(macro_data["grad_unemp"], periods=12)
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

st.write("---")

# --- ROW 5: WHO WORKS IN AI-EXPOSED JOBS (CPS MICRODATA) ---
st.header("Phase 5: Are Young Workers Being Squeezed Out of AI-Exposed Jobs? (CPS)")
st.write(
    "The test from Brynjolfsson, Chandar & Chen's *Canaries in the Coal Mine* (2025), rebuilt from public "
    "Census microdata. Every worker's occupation is scored for LLM exposure "
    "([Eloundou et al. 2023](https://arxiv.org/abs/2303.10130)) and occupations are split into fifths by "
    "2019 employment. If AI is replacing entry-level work, **the youngest line should fall while older "
    "workers hold steady**. A recession or a small graduating class hits every job in an age group at "
    "once, so it doesn't move these shares."
)

exposure_table = load_exposure_table()
if exposure_table is None:
    st.warning("CPS summary not built yet. Run `python cps_extractor.py` (one-time download of about 1.7GB).")
else:
    c11, c12 = st.columns([3, 1])
    with c12:
        grads_only = st.toggle("Bachelor's degree holders only", value=False)
        quintile = st.select_slider(
            "Exposure fifth", options=[1, 2, 3, 4, 5], value=5,
            format_func=lambda q: {1: "1 (least)", 5: "5 (most)"}.get(q, str(q)),
        )
        st.caption("12-month averages, indexed so each age group's 2022 average = 100.")
    with c11:
        shares = exposed_share_index(exposure_table, quintile=quintile, bachelors_only=grads_only)
        shares = shares[["22-25", "26-30", "31-40", "41+"]]
        shares.index.name = "Date"
        long_df = shares.reset_index().melt("Date", var_name="Age", value_name="Index")
        lines = alt.Chart(long_df).mark_line().encode(
            x=alt.X("Date:T", title=""),
            y=alt.Y("Index:Q", title="Share in this fifth (2022 = 100)", scale=alt.Scale(zero=False)),
            color=alt.Color("Age:N", sort=["22-25", "26-30", "31-40", "41+"],
                            scale=alt.Scale(range=["#d62728", "#ff7f0e", "#9e9e9e", "#616161"]),
                            legend=alt.Legend(orient="bottom", title="Age")),
            strokeWidth=alt.condition(alt.datum.Age == "22-25", alt.value(3), alt.value(1.5)),
            tooltip=["Date:T", "Age:N", alt.Tooltip("Index:Q", format=".1f")],
        )
        chatgpt = alt.Chart(pd.DataFrame({"x": [pd.Timestamp("2022-11-30")]})).mark_rule(
            color="#673ab7", strokeDash=[6, 4]).encode(x="x:T")
        st.altair_chart((lines + chatgpt).properties(height=380), width="stretch")

    latest = shares.iloc[-1]
    m1, m2, m3 = st.columns(3)
    signed = lambda x: f"{round(x, 1) + 0:+.1f}"  # + 0 turns -0.0 into 0.0
    m1.metric("Ages 22-25 vs. 2022", f"{signed(latest['22-25'] - 100)}%")
    m2.metric("Ages 41+ vs. 2022", f"{signed(latest['41+'] - 100)}%")
    m3.metric("Young minus old", f"{signed(latest['22-25'] - latest['41+'])} pts")
    st.caption(
        f"Through {shares.index[-1]:%b %Y}. The survey has roughly 500-900 employed 22-25 year olds per "
        "fifth each month (far fewer with the degree filter on), so moves of a few points are within "
        "the noise. Purple line = ChatGPT's release."
    )
