import pandas as pd
import os
from dotenv import load_dotenv
from fredapi import Fred

def fetch_all_macro_data(api_key):
    fred = Fred(api_key=api_key)
    
    # 1. Raw Data Pulls (Phase 1)
    productivity = fred.get_series('OPHNFB').tail(40)
    job_openings_rate = fred.get_series('JTSJOR').tail(120)
    software = fred.get_series('B985RC1Q027SBEA').tail(40)
    hardware = fred.get_series('Y006RC1Q027SBEA').tail(40)
    total_tech_investment = software + hardware
    
    # 2. Raw Data Pulls (Phase 2 - The Missing Variables!)
    grad_unemp = fred.get_series('CGBD2024').tail(120) # 20-24 years old (Actual Recent Grads)
    wages = fred.get_series('CES0500000003').tail(120)    
    profits = fred.get_series('CP').tail(40)              
    
    # Step A: Align frequencies to Quarterly
    df = pd.DataFrame({
        'tech': total_tech_investment.resample('QE').last(),
        'prod': productivity.resample('QE').last(),
        'jobs': job_openings_rate.resample('QE').mean(),
        'grad_unemp': grad_unemp.resample('QE').mean(),
        'wages': wages.resample('QE').mean(),
        'profits': profits.resample('QE').last()
    })
    
    # Forward-fill lagging data, backward-fill to protect starting row, then drop gaps
    df = df.ffill().bfill().dropna()
    
    if df.empty:
        raise ValueError("Merged dataframe is empty. FRED data dates did not overlap.")
    
    # Step C: Normalize to Base 100
    for col in df.columns:
        df[f'{col}_100'] = (df[col] / df[col].iloc[0]) * 100
        
    # Step D: Inversions
    df['jobs_inverse'] = 200 - df['jobs_100']
    df['wages_inverse'] = 200 - df['wages_100']
    
    # Step E: Final V2 Index Calculation (Average of 6 factors)
    df['ai_displacement_index'] = (
        df['tech_100'] + 
        df['prod_100'] + 
        df['jobs_inverse'] + 
        df['grad_unemp_100'] + 
        df['wages_inverse'] + 
        df['profits_100']
    ) / 6
    
    return {
        "productivity": productivity,
        "job_openings_rate": job_openings_rate,
        "total_tech_investment": total_tech_investment,
        "grad_unemp": grad_unemp,
        "wages": wages,
        "profits": profits,
        "ai_displacement_index": df['ai_displacement_index']
    }

if __name__ == "__main__":
    load_dotenv()
    MY_API_KEY = os.getenv("FRED_API_KEY") 
    
    if MY_API_KEY:
        data = fetch_all_macro_data(MY_API_KEY)
        print("V2 Data pull successful. Ready for the dashboard.")
        print(f"Sample Index Data: \n{data['ai_displacement_index'].tail(3)}")
    else:
        print("Error: Could not find FRED_API_KEY in your .env file.")