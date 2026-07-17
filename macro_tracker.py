import pandas as pd
import os
from dotenv import load_dotenv
from fredapi import Fred

def fetch_all_macro_data(api_key, start_date="2014-01-01"):
    """
    Fetches raw macroeconomic indicators from FRED starting from a fixed date.
    Returns a dictionary of raw Pandas Series.
    """
    fred = Fred(api_key=api_key)
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
        "wages": "CES0500000003",        # Avg Hourly Earnings
        "profits": "CP"                  # Corporate Profits
    }

    print("Connecting to FRED API...")

    # 2. Safely fetch all data using a fixed start date (No more .tail() mismatches)
    for key, series_id in series_map.items():
        try:
            # observation_start guarantees all series anchor to the same timeline
            data[key] = fred.get_series(series_id, observation_start=start_date)
        except Exception as e:
            print(f"Warning: Failed to fetch {key} ({series_id}). Error: {e}")
            data[key] = pd.Series(dtype=float)

    # 3. Calculate compound metrics
    # Ensure both software and hardware successfully loaded before adding
    if not data["software_investment"].empty and not data["hardware_investment"].empty:
        data["total_tech_investment"] = data["software_investment"] + data["hardware_investment"]
    else:
        data["total_tech_investment"] = pd.Series(dtype=float)

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
        "wages": data["wages"],
        "profits": data["profits"]
    }

if __name__ == "__main__":
    load_dotenv()
    MY_API_KEY = os.getenv("FRED_API_KEY") 
    
    if MY_API_KEY:
        try:
            fetched_data = fetch_all_macro_data(MY_API_KEY)
            print("\nData pull successful! Validated Series Shapes:")
            for key, series in fetched_data.items():
                print(f" - {key}: {len(series)} data points")
        except Exception as e:
            print(f"Critical Error during execution: {e}")
    else:
        print("Error: Could not find FRED_API_KEY in your .env file.")