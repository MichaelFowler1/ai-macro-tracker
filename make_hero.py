#!/usr/bin/env python3
"""
Generate docs/hero.png - the README image.

Pulls LIVE data at generation time — the same FRED series as the dashboard
plus the NY Fed college labor market workbook — and computes the composite
AI Displacement Risk Index with the app's REAL logic (normalize_series ->
Z-scores, the same +/- signs and weighted sum from app.py, all weights 1.0).

Run:  python make_hero.py     (needs the app's requirements + matplotlib,
                               and FRED_API_KEY in .env)
"""
import os
from datetime import date

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from macro_tracker import fetch_all_macro_data
from nyfed_extractor import fetch_college_labor_data

START = pd.Timestamp("2022-11-01")  # the dashboard's default post-LLM window

BG, INK, DIM = "#0b1017", "#e6ebf2", "#8493a6"
IDX_FILL, IDX_LINE = "#673ab7", "#b39ddb"   # app.py index colors


def normalize_series(series):
    """Z-score — identical to app.py's normalize_series."""
    if series.std() == 0 or len(series) < 2:
        return series * 0
    return (series - series.mean()) / series.std()


# --- pull everything live ---
load_dotenv()
api_key = os.getenv("FRED_API_KEY")
if not api_key:
    raise SystemExit("FRED_API_KEY not found in .env")

print("[*] Pulling FRED data...")
macro = fetch_all_macro_data(api_key)
print("[*] Pulling NY Fed college labor market data...")
underemp = fetch_college_labor_data()["underemployment"]["Recent graduates"]

# --- the seven pillars, signed exactly as app.py's index ---
pillars = {
    "tech":     ("Tech Investment", 1, "#1f77b4", macro["total_tech_investment"]),
    "prod":     ("Productivity", 1, "#ff7f0e", macro["productivity"]),
    "jobs":     ("Job Openings Rate", -1, "#2ca02c", macro["job_openings_rate"]),
    "unemp":    ("Grad Unemployment", 1, "#9467bd", macro["grad_unemp"]),
    "wage":     ("Wage Growth", -1, "#8c564b", macro["wages"]),
    "prof":     ("Corporate Profits", 1, "#e377c2", macro["profits"]),
    "underemp": ("Grad Underemployment", 1, "#d62728", underemp),
}
pillars = {k: (name, sign, col, s[s.index >= START])
           for k, (name, sign, col, s) in pillars.items()}

# weighted Z-score sum, EXACTLY as app.py builds Dynamic_Risk_Score (all weights 1.0)
df_index = pd.DataFrame({k: sign * normalize_series(s)
                         for k, (_, sign, _, s) in pillars.items()}).dropna()
risk = df_index.sum(axis=1)
print(f"[*] Index: {len(risk)} points, {risk.index[0]:%b %Y} -> {risk.index[-1]:%b %Y}")

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": "#1b2740"})
fig = plt.figure(figsize=(13, 7.2), facecolor=BG)
fig.text(0.045, 0.945, "AI JOB-DISPLACEMENT & MACRO TRACKER",
         fontsize=16, fontweight="bold")
fig.text(0.045, 0.900, "composite Z-score risk index from 7 live FRED / NY Fed factors  ·  "
                       "rising = labor losing leverage to tech capital  ·  live Streamlit dashboard",
         fontsize=9.5, color=DIM)

# ---- main: the risk index ----
ax = fig.add_axes([0.06, 0.40, 0.9, 0.40], facecolor="#0a0f18")
ax.fill_between(risk.index, risk.min() - 0.5, risk, color=IDX_FILL, alpha=0.30)
ax.plot(risk.index, risk, color=IDX_LINE, lw=2.2)
ax.axvline(START, color="#ff9800", ls="--", lw=1.1)
ax.text(START + pd.Timedelta(days=12), ax.get_ylim()[1] * 0.86,
        " late-2022 LLM inflection\n (dashboard start)", color="#ff9800", fontsize=8)
ax.xaxis.set_major_locator(mdates.AutoDateLocator())
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
ax.set_ylabel("Relative Risk Score (Z)", fontsize=9)
ax.tick_params(colors=DIM, labelsize=8)
ax.grid(color="#12203a", lw=0.6)
ax.set_xlim(START, risk.index[-1])  # keep the LLM-inflection marker in frame
ax.set_title("The AI Displacement Risk Index (Dynamic) — 7-factor weighted Z-score, adjustable live",
             fontsize=9.5, color=DIM, loc="left", pad=6)

# ---- bottom: the seven contributing pillars ----
for i, (k, (name, sign, col, s)) in enumerate(pillars.items()):
    axp = fig.add_axes([0.045 + i * 0.131, 0.09, 0.112, 0.20], facecolor="#0a0f18")
    z = normalize_series(s)
    axp.plot(z.index, z, color=col, lw=1.5)
    axp.fill_between(z.index, z.min(), z, color=col, alpha=0.12)
    axp.set_xticks([]); axp.set_yticks([])
    for sp in axp.spines.values():
        sp.set_edgecolor("#1b2740")
    up = z.iloc[-1] >= z.iloc[0]
    axp.set_title(f"{name}", fontsize=7.6, color=INK, loc="left", pad=3)
    axp.text(0.02, 0.06, f"{'+' if sign > 0 else '−'} weight",
             transform=axp.transAxes, fontsize=7.2, color=DIM)
    axp.text(0.97, 0.85, "▲" if up else "▼", transform=axp.transAxes,
             fontsize=9, color=("#ff6b6b" if (up == (sign > 0)) else "#5fd08a"),
             ha="right", va="top")

fig.text(0.045, 0.028, f"Live data pulled from FRED and the NY Fed on {date.today():%b %d, %Y}; "
                       "index computed with app.py's real Z-score formula. "
                       "Regenerate: python make_hero.py",
         fontsize=8, color=DIM)

os.makedirs("docs", exist_ok=True)
fig.savefig("docs/hero.png", dpi=140, facecolor=BG)
print("[+] wrote docs/hero.png")
