import os
import requests
import pandas as pd
import json
from datetime import datetime

def fetch_bls_data(series_id='JTS510000000000000LDL'):
    """
    Fetches layoff or job opening data from the BLS API.
    Note: BLS JOLTS Series IDs must be exactly 21 characters long.
    """
    print(f"Connecting to BLS API for series {series_id}...")
    
    # Optional: Get a free API key from BLS and save it in your .env file
    # This upgrades you to the V2 API (500 requests/day instead of 25)
    bls_key = os.getenv("BLS_API_KEY") 
    
    # Calculate the last 5 years dynamically
    current_year = datetime.now().year
    
    api_payload = {
        "seriesid": [series_id],
        "startyear": str(current_year - 5),
        "endyear": str(current_year),
        "registrationkey": bls_key # Ignored if None
    }
    
    # Use V2 if you have a key, otherwise fallback to V1
    api_version = "v2" if bls_key else "v1"
    url = f'https://api.bls.gov/publicAPI/{api_version}/timeseries/data/'
    headers = {'Content-type': 'application/json'}
    
    try:
        response = requests.post(url, data=json.dumps(api_payload), headers=headers)
        response.raise_for_status() # Catches standard HTTP errors (like 404 or 500)
        json_data = response.json()
        
        series_data = json_data['Results']['series'][0]['data']
        if not series_data:
            print("Warning: BLS returned an empty dataset. Ensure your Series ID is exactly 21 characters.")
            return pd.DataFrame()
            
    except (KeyError, IndexError, requests.exceptions.RequestException) as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(series_data)
    
    # Clean up the month code (M01 -> 01) and create a proper Date column
    df['Month_Num'] = df['period'].str.replace('M', '')
    df['Date'] = pd.to_datetime(df['year'] + '-' + df['Month_Num'] + '-01')
    
    # Format and clean columns
    df['Value_in_Thousands'] = pd.to_numeric(df['value'])
    
    # Sort chronologically and keep only what we need
    df = df.sort_values('Date')
    df = df[['Date', 'Value_in_Thousands']].reset_index(drop=True)
    
    print("Data successfully extracted and cleaned!")
    return df

if __name__ == "__main__":
    # Pulling Information Sector Layoffs (Note the 15 zeros padding the middle)
    my_data = fetch_bls_data('JTS510000000000000LDL')
    
    print("\nHere are the most recent 5 months of data:")
    if not my_data.empty:
        print(my_data.tail())