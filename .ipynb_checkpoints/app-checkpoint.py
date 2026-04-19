import streamlit as st
import altair as alt
import os
from dotenv import load_dotenv
from macro_tracker import fetch_all_macro_data

load_dotenv()

st.set_page_config(page_title="AI Job Impact Tracker", layout="wide")

st.title("Macro Indicators of AI Job Displacement")
st.write("Tracking the economic footprint of automation.")

API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    st.error("API Key not found. Please check your .env file.")
    st.stop()

@st.cache_data
def load_data():
    return fetch_all_macro_data(API_KEY)

data = load_data()

def plot_locked_chart(series_data, line_color):
    df = series_data.reset_index()
    df.columns = ["Date", "Value"] 
    chart = alt.Chart(df).mark_line(color=line_color).encode(
        x=alt.X("Date:T", title=""),      
        y=alt.Y("Value:Q", title="")      
    )
    st.altair_chart(chart, use_container_width=True)

# Draw the dashboard
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
    # This line fixes your NameError!
    plot_locked_chart(data["job_openings_rate"], "#2ca02c")
    
    st.write("---") 
    st.subheader("Hiring Velocity")
    st.write("MoM Growth (6-Month Rolling Avg)")
    job_roc = (data["job_openings_rate"].pct_change() * 100).rolling(window=6).mean().dropna()
    plot_locked_chart(job_roc, "#d62728")