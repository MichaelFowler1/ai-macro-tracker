import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv
from fredapi import Fred

# FRED's public chart-download endpoint. Needs no API key, so the dashboard
# still runs for anyone who clones the repo without registering for one.
FREDGRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def _get_series_keyless(series_id, start_date):
    """Same result as Fred.get_series, pulled from the keyless CSV endpoint."""
    resp = requests.get(FREDGRAPH_URL, params={"id": series_id, "cosd": start_date}, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), index_col=0, parse_dates=True)
    # Missing observations come through as "." so coerce them to NaN
    return pd.to_numeric(df.iloc[:, 0], errors="coerce")


def fetch_all_macro_data(api_key=None, start_date="2014-01-01"):
    """
    Fetches raw macroeconomic indicators from FRED starting from a fixed date.
    Uses the official API when api_key is set, otherwise the keyless CSV endpoint.
    Returns a dictionary of raw Pandas Series.
    """
    if api_key:
        fred = Fred(api_key=api_key)
        get_series = lambda sid: fred.get_series(sid, observation_start=start_date)
    else:
        get_series = lambda sid: _get_series_keyless(sid, start_date)
    data = {}
    
    # 1. Define the series we want to track
    series_map = {
        "productivity": "OPHNFB",
        "job_openings_rate": "JTSJOR",
        "software_investment": "B985RC1Q027SBEA",
        "hardware_investment": "Y006RC1Q027SBEA",
        "grad_unemp": "CGBD2024",        # Bachelor's, 20-24 years old
        "grad_unemp_2534": "CGBD2534",   # Bachelor's, 25-34 years old
        "grad_unemp_25o": "CGBD25O",     # Bachelor's, 25 and over
        "master_unemp_25o": "CGMD25O",   # Master's, 25 and over
        "unemp_2024": "LNU04000036",     # Everyone 20-24 years old (same survey, also not seasonally adjusted)
        "labor_share": "PRS85006173",    # Nonfarm business labor share, 2017=100
        "wages": "CES0500000003",        # Avg Hourly Earnings
        "profits": "CP",                 # Corporate Profits
        "cpi": "CPIAUCSL"                # CPI, to turn nominal growth into real growth
    }

    print("Connecting to FRED API...")

    # 2. Safely fetch all data using a fixed start date (No more .tail() mismatches)
    for key, series_id in series_map.items():
        try:
            # observation_start guarantees all series anchor to the same timeline
            data[key] = get_series(series_id)
        except Exception as e:
            print(f"Warning: Failed to fetch {key} ({series_id}). Error: {e}")
            data[key] = pd.Series(dtype=float)

    # 3. Calculate compound metrics
    # Ensure both software and hardware successfully loaded before adding
    if not data["software_investment"].empty and not data["hardware_investment"].empty:
        data["total_tech_investment"] = data["software_investment"] + data["hardware_investment"]
    else:
        data["total_tech_investment"] = pd.Series(dtype=float)

    # Young grads vs. everyone their age. Age and the business cycle hit both
    # groups, so what's left is the value of the degree itself.
    if not data["grad_unemp"].empty and not data["unemp_2024"].empty:
        data["young_grad_gap"] = (data["grad_unemp"] - data["unemp_2024"]).dropna()
    else:
        data["young_grad_gap"] = pd.Series(dtype=float)

    # 4. Clean up any trailing NaN values (if one series hasn't released this month's data yet)
    for key in data:
        if not data[key].empty:
            # Forward-fill gaps, then drop remaining NaNs
            data[key] = data[key].ffill().dropna()

    return {
        "productivity": data["productivity"],
        "job_openings_rate": data["job_openings_rate"],
        "total_tech_investment": data["total_tech_investment"],
        "grad_unemp": data["grad_unemp"],
        "grad_unemp_2534": data["grad_unemp_2534"],
        "grad_unemp_25o": data["grad_unemp_25o"],
        "master_unemp_25o": data["master_unemp_25o"],
        "young_grad_gap": data["young_grad_gap"],
        "labor_share": data["labor_share"],
        "wages": data["wages"],
        "profits": data["profits"],
        "cpi": data["cpi"]
    }

if __name__ == "__main__":
    load_dotenv()
    MY_API_KEY = os.getenv("FRED_API_KEY") 
    
    if not MY_API_KEY:
        print("No FRED_API_KEY in .env, using the keyless CSV endpoint.")
    try:
        fetched_data = fetch_all_macro_data(MY_API_KEY)
        print("\nData pull successful! Validated Series Shapes:")
        for key, series in fetched_data.items():
            print(f" - {key}: {len(series)} data points")
    except Exception as e:
        print(f"Critical Error during execution: {e}")