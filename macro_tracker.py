import pandas as pd
import os
from dotenv import load_dotenv
from fredapi import Fred

def fetch_all_macro_data(api_key):
    fred = Fred(api_key=api_key)
    
    # 1. Raw Data Pulls
    productivity = fred.get_series('OPHNFB').tail(40)
    job_openings_rate = fred.get_series('JTSJOR').tail(120)
    software = fred.get_series('B985RC1Q027SBEA').tail(40)
    hardware = fred.get_series('Y006RC1Q027SBEA').tail(40)
    total_tech_investment = software + hardware
    
    # Step A: Align frequencies to Quarterly
    # Take the last reported value of each quarter for prod/tech, and the average for jobs
    prod_q = productivity.resample('QE').last()
    tech_q = total_tech_investment.resample('QE').last()
    jobs_q = job_openings_rate.resample('QE').mean()
    
    # Step B: Combine into one DataFrame and drop missing dates
    df = pd.DataFrame({
        'tech': tech_q,
        'prod': prod_q,
        'jobs': jobs_q
    }).dropna()
    
    # Step C: Normalize to Base 100 (Set the first chronological row as 100)
    df['tech_100'] = (df['tech'] / df['tech'].iloc[0]) * 100
    df['prod_100'] = (df['prod'] / df['prod'].iloc[0]) * 100
    df['jobs_100'] = (df['jobs'] / df['jobs'].iloc[0]) * 100
    
    # Step D: Calculate the Custom Index
    # Invert job openings: If jobs drop to 80, the inverted impact is 120 (higher displacement risk)
    df['jobs_inverse'] = 200 - df['jobs_100']
    
    # Average the three components together into a single master index
    df['ai_displacement_index'] = (df['tech_100'] + df['prod_100'] + df['jobs_inverse']) / 3
    
    return {
        "productivity": productivity,
        "job_openings_rate": job_openings_rate,
        "total_tech_investment": total_tech_investment,
        "ai_displacement_index": df['ai_displacement_index']
    }

if __name__ == "__main__":
    load_dotenv()
    MY_API_KEY = os.getenv("FRED_API_KEY") 
    
    if MY_API_KEY:
        data = fetch_all_macro_data(MY_API_KEY)
        print("Data pull successful. Ready for the dashboard.")
        print(f"Sample Index Data: \n{data['ai_displacement_index'].tail(3)}")
    else:
        print("Error: Could not find FRED_API_KEY in your .env file.")