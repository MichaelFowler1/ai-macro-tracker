import requests
import pandas as pd
import json

def fetch_bls_layoffs():
    print("Connecting to BLS API...")
    
    url = 'https://api.bls.gov/publicAPI/v1/timeseries/data/'
    
    api_payload = {
        "seriesid": ['JTS000000000000000LDL'],
        "startyear": "2023",
        "endyear": "2024"
    }
    
    headers = {'Content-type': 'application/json'}
    
    response = requests.post(url, data=json.dumps(api_payload), headers=headers)
    json_data = response.json()
    
    try:
        series_data = json_data['Results']['series'][0]['data']
    except (KeyError, IndexError):
        print("Error: Could not find data in the BLS response.")
        return pd.DataFrame()

    # Convert raw list into a Pandas DataFrame
    df = pd.DataFrame(series_data)
    
    df = df[['year', 'period', 'periodName', 'value']]
    
    df.columns = ['Year', 'Month_Code', 'Month', 'Layoffs_in_Thousands']
    
    # Convert the layoff values from text into numbers
    df['Layoffs_in_Thousands'] = pd.to_numeric(df['Layoffs_in_Thousands'])
    
    print("Data successfully extracted and cleaned!")
    return df

# Test the file directly
if __name__ == "__main__":
    my_data = fetch_bls_layoffs()
    print("\nHere are the top 5 rows of our new BLS Data:")
    print(my_data.head())