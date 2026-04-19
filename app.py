import os
import streamlit as st
import altair as alt
from dotenv import load_dotenv
from macro_tracker import fetch_all_macro_data

# Load environment variables
load_dotenv()
st.set_page_config(page_title="AI Job Impact Tracker", layout="wide")

st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

# API Key Check
API_KEY = os.getenv("FRED_API_KEY")
if not API_KEY:
    st.error("API Key not found in .env. Please check your credentials.")
    st.stop()

# Cache data to prevent hitting FRED limits
@st.cache_data
def load_data():
    return fetch_all_macro_data(API_KEY)

data = load_data()

# --- HELPER FUNCTIONS ---

def plot_locked_chart(series_data, line_color, title=""):
    """Generates a clean Altair line chart."""
    df = series_data.reset_index()
    df.columns = ["Date", "Value"] 
    chart = alt.Chart(df).mark_line(color=line_color).encode(
        x=alt.X("Date:T", title=""),      
        y=alt.Y("Value:Q", title=title, scale=alt.Scale(zero=False))      
    )
    st.altair_chart(chart, width="stretch")

def get_yoy_change(series):
    """Calculates Year-over-Year % change based on Quarterly data (4 periods)."""
    if len(series) < 4:
        return 0
    current = series.iloc[-1]
    last_year = series.iloc[-4]
    return ((current - last_year) / last_year) * 100

# --- MASTER INDEX SECTION ---

st.header("The AI Displacement Risk Index (V2)")
st.write("A composite index tracking 6 macro-factors. **Rising values** indicate labor losing leverage to tech capital.")

with st.expander("How is this calculated? (V2 Methodology)"):
    st.markdown("""
    **The 6 Pillars of the Index:**
    1. **Tech Capital (+):** Spending on AI-adjacent hardware/software.
    2. **Productivity (+):** Output per hour (efficiency gains).
    3. **Job Openings (-):** Market demand for new human labor.
    4. **Grad Unemployment (+):** Stress on entry-level cognitive roles.
    5. **Wage Growth (-):** Decoupling of worker pay from company gains.
    6. **Corporate Profits (+):** Value capture from automation.
    """)

# Main Index Area Chart
idx_df = data["ai_displacement_index"].reset_index()
idx_df.columns = ["Date", "Value"]
index_chart = alt.Chart(idx_df).mark_area(
    color="#673ab7", line={'color': '#4527a0'}, opacity=0.3
).encode(
    x=alt.X("Date:T", title=""),
    y=alt.Y("Value:Q", title="Risk Score", scale=alt.Scale(zero=False))
).properties(height=350) 
st.altair_chart(index_chart, width="stretch")

st.write("---")

# --- ROW 1: THE CORE PILLARS ---
st.header("Phase 1: Capital & Demand")
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("Tech Investment")
    plot_locked_chart(data["total_tech_investment"], "#1f77b4")
with c2:
    st.subheader("Labor Productivity")
    plot_locked_chart(data["productivity"], "#ff7f0e")
with c3:
    st.subheader("Job Openings Rate")
    plot_locked_chart(data["job_openings_rate"], "#2ca02c")

st.write("---")

# --- ROW 2: THE LABOR BLEED (WITH YoY METRICS) ---
st.header("Phase 2: Labor & Profit Health")
c4, c5, c6 = st.columns(3)

with c4:
    st.subheader("Recent Grad Unemployment")
    st.write("Bachelor's degree (Ages 20-24)")
    plot_locked_chart(data["grad_unemp"], "#9467bd")
    
    # YoY Metric
    change = get_yoy_change(data["grad_unemp"])
    st.metric("Latest Rate", f"{data['grad_unemp'].iloc[-1]:.1f}%", f"{change:.2f}% YoY")

with c5:
    st.subheader("Wage Levels")
    st.write("Avg Hourly Earnings ($)")
    plot_locked_chart(data["wages"], "#8c564b")
    
    # YoY Metric
    change = get_yoy_change(data["wages"])
    st.metric("Latest Hourly", f"${data['wages'].iloc[-1]:.2f}", f"{change:.2f}% YoY")

with c6:
    st.subheader("Corporate Profits")
    st.write("After Tax (Billions)")
    plot_locked_chart(data["profits"], "#e377c2")
    
    # YoY Metric
    change = get_yoy_change(data["profits"])
    st.metric("Total Profits", f"${data['profits'].iloc[-1]:.1f}B", f"{change:.2f}% YoY")