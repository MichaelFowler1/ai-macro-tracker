import os
import streamlit as st
import altair as alt
from dotenv import load_dotenv
from macro_tracker import fetch_all_macro_data

load_dotenv()

st.set_page_config(page_title="AI Job Impact Tracker", layout="wide")

st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    st.error("API Key not found in .env")
    st.stop()

# cache fred api response
@st.cache_data
def load_data():
    return fetch_all_macro_data(API_KEY)

data = load_data()

# helper for basic line charts
def plot_locked_chart(series_data, line_color):
    df = series_data.reset_index()
    df.columns = ["Date", "Value"] 
    chart = alt.Chart(df).mark_line(color=line_color).encode(
        x=alt.X("Date:T", title=""),      
        y=alt.Y("Value:Q", title="")      
    )
    st.altair_chart(chart, use_container_width=True)

# --- Master Index ---
st.header("The AI Displacement Risk Index (V1)")
st.write("A custom composite index. **Rising values** indicate a macroeconomic shift favoring tech capital over human labor. (Base 100)")

# expandable button for the math explanation
with st.expander("How is this calculated?"):
    st.markdown("""
    **The Components:**
    This index combines three distinct macroeconomic forces into a single score:
    1. **Tech Capital:** Investment in software and hardware.
    2. **Labor Productivity:** Nonfarm business sector output per hour.
    3. **Hiring Demand:** Total nonfarm job openings rate.
    
    **The Math:**
    * **Alignment:** Since job openings are reported monthly and the others are quarterly, we resample everything to a standard quarterly timeline.
    * **Base 100 Normalization:** You can't add billions of dollars to a percentage rate. We normalize all three metrics by setting their starting value to 100. 
    * **Inversion:** We invert the job openings metric. If job openings fall, the displacement risk *rises*. (Formula: `200 - Normalized Job Openings`).
    * **The Final Score:** We average the three normalized numbers together. If capital investment and productivity are climbing while hiring demand falls, the index spikes.
    """)

index_df = data["ai_displacement_index"].reset_index()
index_df.columns = ["Date", "Index Value"]

# main area chart
index_chart = alt.Chart(index_df).mark_area(
    color="#673ab7", 
    line={'color': '#4527a0'},
    opacity=0.3
).encode(
    x=alt.X("Date:T", title=""),
    y=alt.Y("Index Value:Q", title="Displacement Risk Score", scale=alt.Scale(zero=False))
).properties(height=350) 

st.altair_chart(index_chart, use_container_width=True)

# index roc
st.subheader("Index Velocity")
st.write("QoQ Growth (4-Quarter Rolling Avg)")
index_roc = (data["ai_displacement_index"].pct_change() * 100).rolling(window=4).mean().dropna()
plot_locked_chart(index_roc, "#d62728")

st.write("---")

# --- Breakdown ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. Tech Capital")
    st.write("Investment in Software & Hardware (Billions)")
    plot_locked_chart(data["total_tech_investment"], "#1f77b4") 
    
    st.write("---") 
    st.subheader("Investment Velocity")
    st.write("QoQ Growth (4-Quarter Rolling Avg)")
    tech_roc = (data["total_tech_investment"].pct_change() * 100).rolling(window=4).mean().dropna()
    plot_locked_chart(tech_roc, "#d62728")

with col2:
    st.subheader("2. Labor Productivity")
    st.write("Nonfarm Business Sector Productivity Index")
    plot_locked_chart(data["productivity"], "#ff7f0e")
    
    st.write("---") 
    st.subheader("Productivity Velocity")
    st.write("QoQ Growth (4-Quarter Rolling Avg)")
    prod_roc = (data["productivity"].pct_change() * 100).rolling(window=4).mean().dropna()
    plot_locked_chart(prod_roc, "#d62728")

with col3:
    st.subheader("3. Job Openings Rate")
    st.write("Total Nonfarm Job Openings Rate (%)")
    plot_locked_chart(data["job_openings_rate"], "#2ca02c")
    
    st.write("---") 
    st.subheader("Hiring Velocity")
    st.write("MoM Growth (6-Month Rolling Avg)")
    job_roc = (data["job_openings_rate"].pct_change() * 100).rolling(window=6).mean().dropna()
    plot_locked_chart(job_roc, "#d62728")