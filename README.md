# AI Job Displacement & Macroeconomic Tracker

I built this project because looking at aggregate national data often hides what is actually happening in specific sectors, especially tech. This is a local-first Streamlit dashboard that pulls from several government APIs to measure whether labor is losing leverage to tech capital. 

It tracks a mix of macroeconomic indicators and micro-level labor data, and calculates a dynamic risk index that you can adjust on the fly.

### What it tracks

* **Macro trends:** Total tech investment, labor productivity, and national job openings.
* **Labor health:** Recent graduate unemployment, average wage growth, and corporate profits.
* **Micro tech trends:** Layoffs, hiring demand, and H-1B visa volume specifically within the Information Sector (software, data, and web).

### Where the data comes from

* **FRED (Federal Reserve Economic Data):** Used for the high-level macro series like productivity, wages, and capital investment.
* **BLS (Bureau of Labor Statistics):** Used for highly specific JOLTS data. It uses the 21-character series IDs to isolate layoffs and job openings strictly within the Information Sector.
* **USCIS (U.S. Citizenship and Immigration Services):** A custom scraper that downloads massive annual Employer Data Hub CSVs to see which corporate sponsors are utilizing the most tech-related H-1B visas.

### Project Structure

* `app.py`: The main Streamlit dashboard containing the UI, charts, and the dynamic Z-score index calculator.
* `macro_tracker.py`: Handles the FRED API connections and aligns the historical data to a fixed starting date.
* `bls_extractor.py`: Connects to the BLS API to pull sector-specific labor turnover.
* `h1b_extractor.py`: Spoofs browser headers to download raw USCIS CSVs, cleans the data, and aggregates total tech visa approvals by company.

### How to run this locally

**1. Install the dependencies**
You will need Python 3 installed. Run this in your terminal:
```bash
pip install streamlit altair pandas requests python-dotenv fredapi