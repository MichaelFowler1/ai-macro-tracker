import pandas as pd
import os
from dotenv import load_dotenv
from fredapi import Fred

def fetch_all_macro_data(api_key):
    fred = Fred(api_key=api_key)
    
    # --- Data Pulls ---
    # V1 Basics
    productivity = fred.get_series('OPHNFB').tail(40)
    job_openings = fred.get_series('JTSJOR').tail(120)
    software = fred.get_series('B985RC1Q027SBEA').tail(40)
    hardware = fred.get_series('Y006RC1Q027SBEA').tail(40)
    tech_invest = software + hardware
    
    # V2 New Additions
    grad_unemp = fred.get_series('LNS14027662').tail(120) # College Grad Unemployment
    wages = fred.get_series('CES0500000003').tail(120)    # Avg Hourly Earnings
    profits = fred.get_series('CP').tail(40)              # Corp Profits
    
    # --- Alignment & Merging ---
    # Resample all to Quarterly ('QE') to match the slowest data points
    df = pd.DataFrame({
        'tech': tech_invest.resample('QE').last(),
        'prod': productivity.resample('QE').last(),
        'jobs': job_openings.resample('QE').mean(),
        'grad_unemp': grad_unemp.resample('QE').mean(),
        'wages': wages.resample('QE').mean(),
        'profits': profits.resample('QE').last()
    }).dropna()
    
    # --- Index Math (Base 100) ---
    for col in df.columns:
        df[f'{col}_100'] = (df[col] / df[col].iloc[0]) * 100
        
    # Inversions (Lower values = Higher Risk)
    df['jobs_inverse'] = 200 - df['jobs_100']
    df['wages_inverse'] = 200 - df['wages_100']
    
    # Final V2 Index Calculation (Average of 6 factors)
    # Higher = More displacement risk
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
        "job_openings_rate": job_openings,
        "total_tech_investment": tech_invest,
        "grad_unemp": grad_unemp,
        "wages": wages,
        "profits": profits,
        "ai_displacement_index": df['ai_displacement_index']
    }