import io

import pandas as pd
import requests

# The NY Fed publishes the workbook behind its "Labor Market for Recent College
# Graduates" interactive (https://www.newyorkfed.org/research/college-labor-market).
# Updated quarterly. The server rejects the default python-requests User-Agent
# with a 403, so we send browser-style headers.
DATA_URL = (
    "https://www.newyorkfed.org/medialibrary/Research/Interactives/Data/"
    "college-labor-market/College-labor-data"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def _extract_table(raw, anchor):
    """
    Each sheet buries its table under a variable number of branding/notes rows.
    Rather than hardcoding row offsets (which break when the NY Fed reshuffles
    the cover text), locate the header row by its anchor cell ('Date' or
    'Major') and slice from there.
    """
    mask = raw.astype(str).eq(anchor)
    hits = list(zip(*mask.values.nonzero()))
    if not hits:
        raise ValueError(f"Could not find '{anchor}' header cell in sheet.")
    row, col = hits[0]

    header = raw.iloc[row, col:].tolist()
    n_cols = sum(1 for h in header if pd.notna(h))

    table = raw.iloc[row + 1:, col:col + n_cols].copy()
    table.columns = [str(h).strip() for h in header[:n_cols]]
    table = table.dropna(subset=[anchor])
    return table


def _parse_timeseries(xl, sheet_name):
    raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    table = _extract_table(raw, "Date")
    table["Date"] = pd.to_datetime(table["Date"], errors="coerce")
    table = table.dropna(subset=["Date"]).set_index("Date")
    return table.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def _parse_majors(xl):
    raw = pd.read_excel(xl, sheet_name="outcomes by major", header=None)
    table = _extract_table(raw, "Major")
    table = table.set_index("Major")
    return table.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def fetch_college_labor_data():
    """
    Downloads the NY Fed college labor market workbook and returns a dict:
      - 'unemployment':   monthly rates since 1990 for recent grads (22-27),
                          all college grads, young non-grads, and all workers
      - 'underemployment': monthly share of grads in jobs not requiring a degree
      - 'majors':         latest unemployment/underemployment/wages per major
                          (includes an 'Overall' benchmark row)
    Raises on network/parse failure; callers decide how to degrade.
    """
    resp = requests.get(DATA_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    xl = pd.ExcelFile(io.BytesIO(resp.content))

    return {
        "unemployment": _parse_timeseries(xl, "unemployed"),
        "underemployment": _parse_timeseries(xl, "underemployed"),
        "majors": _parse_majors(xl),
    }


if __name__ == "__main__":
    data = fetch_college_labor_data()
    for key, df in data.items():
        print(f"\n=== {key}: {df.shape[0]} rows x {df.shape[1]} cols")
        print(df.tail(3))
