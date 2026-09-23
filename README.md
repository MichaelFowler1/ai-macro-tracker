# AI Job Displacement & Macroeconomic Tracker

I built this project because looking at aggregate national data often hides what is actually happening in specific sectors, especially tech. This is a local-first Streamlit dashboard that pulls from several government APIs to measure whether labor is losing leverage to tech capital. 

It tracks a mix of macroeconomic indicators and micro-level labor data, and calculates a dynamic risk index that you can adjust on the fly.

![AI Displacement Risk Index dashboard](docs/hero.png)

*The composite risk index is computed with `app.py`'s real Z-score formula over the 7 weighted factors, from live data pulled from FRED and the NY Fed at generation time. Regenerate with `python make_hero.py`.*

### What it tracks

* **Macro trends:** Total tech investment, labor productivity, and national job openings.
* **Labor health:** Recent graduate unemployment, average wage growth, and corporate profits.
* **Micro tech trends:** Layoffs and hiring demand specifically within the Information Sector (software, data, and web).
* **The graduate squeeze:** Recent-grad unemployment versus all workers, grad underemployment, and outcomes by college major (is Computer Science still a safe bet?).

### Where the data comes from

* **FRED (Federal Reserve Economic Data):** Used for the high-level macro series like productivity, wages, and capital investment.
* **BLS (Bureau of Labor Statistics):** Used for highly specific JOLTS data. It uses the 21-character series IDs to isolate layoffs and job openings strictly within the Information Sector.
* **NY Fed (Federal Reserve Bank of New York):** The [Labor Market for Recent College Graduates](https://www.newyorkfed.org/research/college-labor-market) dataset: monthly unemployment and underemployment for recent grads since 1990, plus outcomes broken down by college major. No API key required.

### Project Structure

* `app.py`: The main Streamlit dashboard containing the UI, charts, and the dynamic Z-score index calculator.
* `macro_tracker.py`: Handles the FRED connections and aligns the historical data to a fixed starting date. Uses the official API if you have a key, otherwise FRED's public CSV download.
* `bls_extractor.py`: Connects to the BLS API to pull sector-specific labor turnover.
* `nyfed_extractor.py`: Downloads the NY Fed college labor market Excel workbook and parses the unemployment, underemployment, and outcomes-by-major sheets.
* `make_hero.py`: Rebuilds `docs/hero.png` from live data using the same index math as the dashboard.

### How to run this locally

**1. Install the dependencies**
You'll need Python 3.11 or newer. Run this in your terminal:
```bash
pip install -r requirements.txt
```

**2. Add your API keys (optional)**
The dashboard runs without any keys. FRED falls back to its public CSV download and BLS to its v1 API, which caps you at 25 requests a day. If you've got keys, create a `.env` file in the project root:
```env
FRED_API_KEY=your_fred_key
BLS_API_KEY=your_bls_key
```

**3. Launch the dashboard**
```bash
streamlit run app.py
```