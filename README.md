## README: Macroeconomic and Labor Market Data Tracker

This project is a Python-based utility designed to automate the collection of key economic indicators. It interfaces with two primary data sources: the **Federal Reserve Economic Data (FRED)** API and the **Bureau of Labor Statistics (BLS)** API.

The system is built to provide a "local-first" data foundation for analyzing productivity, tech investment, and labor market trends (such as layoffs) without relying on manual downloads or cloud-based dashboards.

---

### Key Components

#### 1. Data Sources
* **FRED API:** Used to retrieve time-series data for business productivity and total technological investment.
* **BLS API (v1):** Used to retrieve the "Layoffs and Discharges" series from the Job Openings and Labor Turnover Survey (JOLTS).

#### 2. Core Functions
* **`fetch_all_macro_data(api_key)`**:
    * Initializes the FRED client using a provided API key.
    * Retrieves specific series IDs (e.g., 'OPHNFB' for productivity).
    * Returns a dictionary of Pandas Series for further analysis.
* **`fetch_bls_layoffs()`**:
    * Sends a POST request to the BLS API using a JSON payload.
    * Navigates a nested JSON response to extract raw monthly layoff numbers.
    * Includes error handling to return an empty DataFrame if the API connection fails or data is missing.

#### 3. Security and Configuration
* **Environment Variables:** The project uses `python-dotenv` to load sensitive API credentials from a `.env` file. This ensures that secret keys are never hard-coded into the script.
* **The `.env` File Requirement:**
    `FRED_API_KEY=your_secret_key_here`

---

### Technical Workflow

1.  **Environment Setup:** The script checks for the existence of the `FRED_API_KEY`. If missing, the script terminates gracefully with an error message.
2.  **Request & Authentication:** The script uses the `requests` library to handle HTTP communication. Authentication is managed via the API key for FRED and headers for the BLS.
3.  **Data Processing:** Raw JSON and XML-style data are converted into **Pandas DataFrames**. This allows for immediate mathematical analysis, such as calculating the `tail()` to see the most recent trends.
4.  **Error Handling:** The implementation uses `try-except` blocks to catch common API issues (like `KeyError` or `IndexError`), ensuring the program remains stable even if external servers return unexpected responses.

---

### Requirements
* Python 3.x
* `pandas`
* `requests`
* `python-dotenv`
* `fredapi`

---

### Execution
The script is designed to be run as a standalone module. When executed, it triggers a "Pre-Flight Checklist" to verify API connectivity and prints a sample of the most recent data points to the terminal to confirm a successful pull.