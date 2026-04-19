import pandas as pd
import os
from dotenv import load_dotenv
from fredapi import Fred


def fetch_all_macro_data(api_key):
    fred = Fred(api_key=api_key)
    
    # 1. Labor Productivity - Quarterly
    productivity = fred.get_series('OPHNFB').tail(40)
    
    # 2. Total Job Market (Total Nonfarm Openings RATE) - Monthly
    job_openings_rate = fred.get_series('JTSJOR').tail(120)
    
    # 3. Tech Investment - Quarterly (Software + Hardware)
    software = fred.get_series('B985RC1Q027SBEA').tail(40)
    hardware = fred.get_series('Y006RC1Q027SBEA').tail(40)
    
    total_tech_investment = software + hardware
    
    return {
        "productivity": productivity,
        "job_openings_rate": job_openings_rate,
        "total_tech_investment": total_tech_investment
    }

if __name__ == "__main__":
    
    load_dotenv()
    
    MY_API_KEY = os.getenv("FRED_API_KEY") 
    
    if MY_API_KEY:
        
        data = fetch_all_macro_data(MY_API_KEY)
        print("Data pull successful. Ready for the dashboard.")
        print(f"Sample data pulled: \n{data['total_tech_investment'].tail(1)}")
    else:
        print("Error: Could not find FRED_API_KEY in your .env file.")