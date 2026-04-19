Here is a complete, professional `README.md` file you can copy and paste directly into your GitHub repository. It includes your chosen description, a breakdown of the data, and clear instructions for anyone who wants to download and run your code.

```markdown
# AI Job Displacement Macro Tracker

An interactive Python/Streamlit dashboard that aggregates real-time FRED API data to visualize the relationship between tech capital investment, labor productivity, and national hiring trends. It is designed to track the broader macroeconomic footprint of AI and automation over time.

## 📊 What This Dashboard Tracks

This tool pulls live data from the Federal Reserve Economic Data (FRED) API to measure three core areas:

1. **Tech Capital (Software & Hardware):** Measures total private investment in software and information processing equipment (semiconductors, servers, etc.), showing the physical and digital build-out of AI.
2. **Labor Productivity:** Tracks the Nonfarm Business Sector Productivity Index to see if tech investments are actively making the existing workforce more efficient.
3. **Job Openings Rate:** Monitors the Total Nonfarm Job Openings Rate to gauge the overall tightness or looseness of the U.S. labor market.

Each metric is plotted alongside an **Investment/Productivity/Hiring Velocity** chart, which calculates the rolling rate-of-change to easily identify aggressive growth or contraction phases.

## 🛠️ Tech Stack

* **Python** (Data fetching and logic)
* **Streamlit** (Web framework and UI)
* **Altair / Pandas** (Data manipulation and charting)
* **FredAPI** (Direct connection to the St. Louis Fed database)

## 💻 How to Run Locally

To run this dashboard on your own machine, follow these steps:

### 1. Clone the repository
```bash
git clone [https://github.com/MichaelFowler1/ai-macro-tracker.git](https://github.com/MichaelFowler1/ai-macro-tracker.git)
cd ai-macro-tracker
```

### 2. Install dependencies
Make sure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Set up your API Key
You will need a free API key from the St. Louis Fed. 
1. Get a key at [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html).
2. Create a file named `.env` in the root folder of this project.
3. Add your key to the `.env` file like this:
```text
FRED_API_KEY=your_32_character_api_key_here
```
*(Note: The `.gitignore` file ensures your API key is never uploaded to GitHub).*

### 4. Run the application
```bash
streamlit run app.py
```
A browser window should automatically open to `http://localhost:8501` displaying the live dashboard.

## 📁 Project Structure

* `app.py`: The main Streamlit frontend file containing the UI layout and chart rendering.
* `macro_tracker.py`: The backend logic that authenticates the FRED API, fetches the specific data series, and performs the mathematical combinations (e.g., Software + Hardware).
* `.env`: (User created) Stores the hidden API key.
* `.gitignore`: Prevents sensitive files from being pushed to GitHub.
* `requirements.txt`: Lists all Python packages required to run the app.