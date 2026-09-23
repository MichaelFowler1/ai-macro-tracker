"""
Employment by AI exposure and age, built from Census CPS microdata.

This is a build script, not something the dashboard runs live. It downloads
the monthly Current Population Survey public-use files (about 12MB each,
2015 onward), tags every employed person with how exposed their occupation
is to LLMs, and writes a small summary table the dashboard reads:
data/ai_exposure_employment.csv.

The design follows Brynjolfsson, Chandar & Chen (2025), "Canaries in the
Coal Mine", which used ADP payroll data: if AI is replacing entry-level
work, young workers' employment should fall in the most exposed occupations
relative to the least exposed ones, while older workers in the same
occupations hold steady.

Pieces:
  - Exposure: OpenAI/UPenn "GPTs are GPTs" (Eloundou et al. 2023), GPT-4
    rated beta score per O*NET occupation (data/crosswalk/occ_level.csv)
  - Census occupation codes -> SOC codes: the Census 2018 code list, and its
    2010 -> 2018 crosswalk for the 2015-2019 files, which use 2010 codes
    (data/crosswalk/2018-occupation-code-list-and-crosswalk.xlsx)

Run:  python cps_extractor.py            (downloads any months not cached yet)
"""
import gzip
import io
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import requests

BASE_URL = "https://www2.census.gov/programs-surveys/cps/datasets/{year}/basic/{mon}{yy}pub.dat.gz"
FIRST_MONTH = date(2015, 1, 1)
CODES_2018_FROM = date(2020, 1, 1)  # CPS switched to 2018 Census occupation codes in Jan 2020

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "data", "cps_cache")
CROSSWALK_XLSX = os.path.join(HERE, "data", "crosswalk", "2018-occupation-code-list-and-crosswalk.xlsx")
EXPOSURE_CSV = os.path.join(HERE, "data", "crosswalk", "occ_level.csv")
SOURCE_URLS = {
    CROSSWALK_XLSX: "https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/"
                    "2018-occupation-code-list-and-crosswalk.xlsx",
    EXPOSURE_CSV: "https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv",
}
OUTPUT_CSV = os.path.join(HERE, "data", "ai_exposure_employment.csv")

# Fixed-width positions (1-indexed, inclusive) from the Census record layouts.
# Identical in every layout from January 2015 through 2026.
FIELDS = {
    "age": (122, 123),     # PRTAGE
    "educ": (137, 138),    # PEEDUCA (43+ = bachelor's or higher)
    "status": (180, 181),  # PEMLR (1-2 = employed)
    "weight": (846, 855),  # PWCMPWGT, 4 implied decimals
    "occ": (860, 863),     # PEIO1OCD / PTIO1OCD, primary job occupation
}

AGE_BINS = [16, 22, 26, 31, 41, 200]
AGE_LABELS = ["16-21", "22-25", "26-30", "31-40", "41+"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
GZIP_MAGIC = bytes([0x1F, 0x8B])
ZIP_MAGIC = b"PK"
HEADERS = {"User-Agent": "ai-macro-tracker (github.com/MichaelFowler1/ai-macro-tracker)"}


# --- exposure by Census occupation code ---

def _code(value):
    """Census occupation codes as 4-digit strings; blanks and headers become None."""
    s = str(value).strip()
    return s.zfill(4) if s.isdigit() else None


def _soc_exposure(soc, onet):
    """
    Mean exposure over the O*NET occupations under a SOC code. Census
    sometimes uses aggregated SOC codes, either with X wildcards (15-12XX)
    or as broad groups ending in 0 (53-3030 covers 53-3031, 53-3032...).
    Some "all other" codes (21-1029) have no O*NET entry at all. Try the
    exact code first, then widen one digit at a time down to the minor group
    (21-1), so an unlisted occupation gets the average of its neighbors.
    """
    soc = str(soc).strip()
    if not re.match(r"^\d\d-[\dX]{4}$", soc):
        return None
    prefix = soc.replace("X", r"\d")
    while len(prefix.replace(r"\d", "X")) >= 4:
        hits = onet[onet["soc"].str.match("^" + prefix)]
        if not hits.empty:
            return hits["beta"].mean()
        prefix = prefix[:-2] if prefix.endswith(r"\d") else prefix[:-1]
    return None


def _ensure_sources():
    """Downloads the crosswalk and exposure files on first run."""
    for path, url in SOURCE_URLS.items():
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)


def exposure_by_census_code():
    """
    Returns two dicts, {census code: exposure}, for the 2018 codes (2020+
    files) and the 2010 codes (2015-2019 files).
    """
    _ensure_sources()
    onet = pd.read_csv(EXPOSURE_CSV)
    onet = pd.DataFrame({"soc": onet["O*NET-SOC Code"].str[:7], "beta": onet["dv_rating_beta"]})

    codes18 = pd.read_excel(CROSSWALK_XLSX, sheet_name="2018 Census Occ Code List", header=None)
    exp18 = {}
    for _, row in codes18.iterrows():
        code = _code(row[2])
        if code is None:
            continue
        e = _soc_exposure(row[3], onet)
        if e is not None:
            exp18[code] = e

    # The crosswalk lists each 2010 code once, with continuation rows under it
    # when it was split into several 2018 codes.
    xwalk = pd.read_excel(CROSSWALK_XLSX, sheet_name="2010 to 2018 Crosswalk ", header=None).iloc[4:]
    xwalk = pd.DataFrame({"soc10": xwalk[0], "c10": xwalk[1].map(_code), "c18": xwalk[4].map(_code)})
    own_soc = xwalk.dropna(subset=["c10"]).set_index("c10")["soc10"]
    xwalk["c10"] = xwalk["c10"].ffill()
    xwalk["e"] = xwalk["c18"].map(exp18)
    exp10 = xwalk.dropna(subset=["e"]).groupby("c10")["e"].mean().to_dict()
    # 2010 codes folded into a broader 2018 code have no 2018 code listed,
    # but their own 2010 SOC code still scores directly
    for c10, soc in own_soc.items():
        if c10 not in exp10:
            e = _soc_exposure(soc, onet)
            if e is not None:
                exp10[c10] = e
    return exp18, exp10


# --- monthly microdata ---

def _month_list(last):
    months, d = [], FIRST_MONTH
    while d <= last:
        months.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return months


def _cache_path(month):
    return os.path.join(CACHE_DIR, f"{month:%Y%m}.csv.gz")


def _download(url, magic):
    """
    Returns the file's bytes, None on 404 (not published, or a month the
    survey skipped, like the Oct 2025 shutdown), or b"" if the server keeps
    sending something that isn't the expected file type. Census occasionally
    answers with an HTML error page under load, hence the retries.
    """
    for attempt in range(3):
        resp = requests.get(url, headers=HEADERS, timeout=300)
        if resp.status_code == 404:
            return None
        if resp.ok and resp.content[:len(magic)] == magic:
            return resp.content
        time.sleep(10 * (attempt + 1))
    return b""


def fetch_month(month):
    """
    Downloads one month's public-use file and keeps only employed people's
    age, education, occupation and weight (~60k rows). Cached as a small
    .csv.gz so re-aggregating never needs another download.
    Returns the month on success, None if Census hasn't published it yet.
    """
    path = _cache_path(month)
    if os.path.exists(path):
        return month
    url = BASE_URL.format(year=month.year, mon=MONTHS[month.month - 1], yy=f"{month.year % 100:02d}")
    raw = _download(url, GZIP_MAGIC)
    if raw is None:
        return None
    if raw:
        text = gzip.open(io.BytesIO(raw), "rt", encoding="latin-1")
    else:
        # A few .dat.gz files on the Census server are broken (Dec 2018 is a
        # 247-byte error page), but the .zip of the same month is fine
        raw = _download(url.replace(".dat.gz", ".zip"), ZIP_MAGIC)
        if not raw:
            raise RuntimeError(f"{url}: neither the .dat.gz nor the .zip is valid")
        z = zipfile.ZipFile(io.BytesIO(raw))
        text = io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1")

    rows = []
    with text as f:
        for line in f:
            rec = {k: line[a - 1:b].strip() for k, (a, b) in FIELDS.items()}
            if rec["status"] not in ("1", "2") or not rec["occ"].lstrip("-").isdigit():
                continue
            rows.append(rec)

    df = pd.DataFrame(rows)
    df = df.assign(
        age=pd.to_numeric(df["age"]), educ=pd.to_numeric(df["educ"]),
        weight=pd.to_numeric(df["weight"]) / 10_000, occ=df["occ"].str.zfill(4),
    ).drop(columns="status")
    df = df[(df["weight"] > 0) & (df["age"] >= 16)]
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")
    return month


# --- aggregation ---

def build_table():
    """
    Month x age group x degree x exposure quintile table of weighted employment.

    Quintiles are fixed on 2019 employment (all ages), so each holds about a
    fifth of 2019's workers. Holding the cutoffs fixed means a shift in
    where young people work shows up as a change in shares, not as the
    quintiles themselves moving.
    """
    exp18, exp10 = exposure_by_census_code()
    months = sorted(m for m in (pd.Timestamp(f[:6] + "01") for f in os.listdir(CACHE_DIR) if f.endswith(".csv.gz")))

    frames = []
    for m in months:
        df = pd.read_csv(_cache_path(m.date()), dtype={"occ": str})
        codes = exp18 if m.date() >= CODES_2018_FROM else exp10
        df["exposure"] = df["occ"].map(codes)
        df["date"] = m
        frames.append(df)
    micro = pd.concat(frames, ignore_index=True)

    coverage = micro.loc[micro["exposure"].notna(), "weight"].sum() / micro["weight"].sum()
    print(f"[*] Exposure score matched for {coverage:.1%} of weighted employment")
    micro = micro.dropna(subset=["exposure"])

    # Employment-weighted quintile cutoffs from 2019
    base = micro[micro["date"].dt.year == 2019].sort_values("exposure")
    cum = base["weight"].cumsum() / base["weight"].sum()
    cuts = [base.loc[cum >= q, "exposure"].iloc[0] for q in (0.2, 0.4, 0.6, 0.8)]
    micro["quintile"] = pd.cut(micro["exposure"], [-1] + cuts + [2], labels=[1, 2, 3, 4, 5], right=True).astype(int)

    micro["age_group"] = pd.cut(micro["age"], AGE_BINS, labels=AGE_LABELS, right=False)
    micro["bachelors"] = micro["educ"] >= 43

    table = (micro.groupby(["date", "age_group", "bachelors", "quintile"], observed=True)
             .agg(employment=("weight", "sum"), respondents=("weight", "size"))
             .reset_index())
    table["employment"] = (table["employment"] / 1000).round(1)  # thousands
    return table


def load_exposure_table():
    """The summary table this script builds, or None if it hasn't been built."""
    if not os.path.exists(OUTPUT_CSV):
        return None
    return pd.read_csv(OUTPUT_CSV, parse_dates=["date"])


def exposed_share_index(table, quintile=5, bachelors_only=False, base_year=2022, window=12):
    """
    For each age group, the share of its employed people working in the given
    exposure quintile, as a 12-month moving average, indexed to its
    base_year average (= 100).

    Using a share rather than a headcount cancels out things that hit a whole
    age group at once: a recession, or a smaller cohort. A falling line means
    that age group is moving away from those occupations relative to its
    own other jobs. 12 months of pooling is needed because the CPS only has
    a few hundred 22-25 year olds per quintile each month.
    """
    t = table[table["bachelors"]] if bachelors_only else table
    wide = t.pivot_table(index=["date", "age_group"], columns="quintile", values="employment", aggfunc="sum")
    share = (wide[quintile] / wide.sum(axis=1)).unstack("age_group")
    # Put missing survey months (Oct 2025 was never collected) back on the
    # calendar so the window spans 12 calendar months, and allow one gap
    share = share.asfreq("MS").rolling(window, min_periods=window - 1).mean()
    base = share[share.index.year == base_year].mean()
    return (share / base * 100).dropna(how="all")


def main():
    today = date.today()
    months = [m for m in _month_list(date(today.year, today.month, 1))]
    todo = [m for m in months if not os.path.exists(_cache_path(m))]
    print(f"[*] {len(months) - len(todo)} months cached, {len(todo)} to fetch")

    def fetch(m):
        try:
            return "ok" if fetch_month(m) else "not available"
        except Exception as e:  # one bad month shouldn't sink the other 140
            return f"FAILED ({e})"

    with ThreadPoolExecutor(max_workers=3) as pool:
        for m, result in zip(todo, pool.map(fetch, todo)):
            print(f"    {m:%Y-%m}: {result}", flush=True)

    table = build_table()
    table.to_csv(OUTPUT_CSV, index=False)
    print(f"[+] wrote {OUTPUT_CSV}: {table['date'].nunique()} months, "
          f"{table['date'].min():%Y-%m} to {table['date'].max():%Y-%m}")


if __name__ == "__main__":
    sys.exit(main())
