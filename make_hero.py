#!/usr/bin/env python3
# Copyright 2026 Michael Fowler
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Generate docs/hero.png - the README image.

Pulls LIVE data at generation time (the same FRED series as the dashboard
plus the NY Fed college labor market workbook) and computes the composite
AI Displacement Risk Index with the same risk_index module the app uses,
all weights 1.0.

Run:  python make_hero.py     (needs the app's requirements + matplotlib;
                               FRED_API_KEY in .env is optional)
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
from risk_index import FACTORS, BASELINE, factor_scores, risk_index

START = pd.Timestamp("2022-11-01")  # the dashboard's default post-LLM window

BG, INK, DIM = "#0b1017", "#e6ebf2", "#8493a6"
IDX_FILL, IDX_LINE = "#673ab7", "#b39ddb"   # app.py index colors


# --- pull everything live ---
load_dotenv()
api_key = os.getenv("FRED_API_KEY")  # optional, see macro_tracker.py

print("[*] Pulling FRED data...")
macro = fetch_all_macro_data(api_key)
print("[*] Pulling NY Fed college labor market data...")
macro["underemp"] = fetch_college_labor_data()["underemployment"]["Recent graduates"]

scores = factor_scores(macro)
scores = scores[scores.index >= START]
risk = risk_index(scores)
COLORS = {"tech": "#1f77b4", "prod": "#ff7f0e", "jobs": "#2ca02c", "gap": "#9467bd",
          "wage": "#8c564b", "labshare": "#e377c2", "underemp": "#d62728"}
print(f"[*] Index: {len(risk)} points, {risk.index[0]:%b %Y} -> {risk.index[-1]:%b %Y}")

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": "#1b2740"})
fig = plt.figure(figsize=(13, 7.2), facecolor=BG)
fig.text(0.045, 0.945, "AI JOB-DISPLACEMENT & MACRO TRACKER",
         fontsize=16, fontweight="bold")
fig.text(0.045, 0.900, f"composite risk index from {scores.shape[1]} live FRED / NY Fed factors  ·  "
                       f"0 = {BASELINE[0][:4]}-{BASELINE[1][:4]} normal  ·  "
                       "rising = labor losing leverage to tech capital",
         fontsize=9.5, color=DIM)

# ---- main: the risk index ----
ax = fig.add_axes([0.06, 0.40, 0.9, 0.40], facecolor="#0a0f18")
ax.fill_between(risk.index, risk.min() - 0.5, risk, color=IDX_FILL, alpha=0.30)
ax.plot(risk.index, risk, color=IDX_LINE, lw=2.2)
ax.axvline(START, color="#ff9800", ls="--", lw=1.1)
ax.axhline(0, color=DIM, ls=":", lw=1)
ax.text(START + pd.Timedelta(days=12), ax.get_ylim()[1] * 0.86,
        " late-2022 LLM inflection\n (dashboard start)", color="#ff9800", fontsize=8)
ax.xaxis.set_major_locator(mdates.AutoDateLocator())
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
ax.set_ylabel("SDs from 2015-2019 normal", fontsize=9)
ax.tick_params(colors=DIM, labelsize=8)
ax.grid(color="#12203a", lw=0.6)
ax.set_xlim(START, risk.index[-1])  # keep the LLM-inflection marker in frame
ax.set_title("The AI Displacement Risk Index (Dynamic): weighted average of Z-scores vs. the pre-pandemic baseline",
             fontsize=9.5, color=DIM, loc="left", pad=6)

# ---- bottom: the contributing factors (already signed, so up = more risk) ----
for i, k in enumerate(scores.columns):
    name, sign, _, _ = FACTORS[k]
    col = COLORS[k]
    axp = fig.add_axes([0.045 + i * 0.131, 0.09, 0.112, 0.20], facecolor="#0a0f18")
    z = scores[k]
    axp.plot(z.index, z, color=col, lw=1.5)
    axp.fill_between(z.index, z.min(), z, color=col, alpha=0.12)
    axp.set_xticks([]); axp.set_yticks([])
    for sp in axp.spines.values():
        sp.set_edgecolor("#1b2740")
    up = z.iloc[-1] >= z.iloc[0]
    axp.set_title(name, fontsize=7.6, color=INK, loc="left", pad=3)
    axp.text(0.02, 0.06, "up = more risk" if sign > 0 else "inverted: up = more risk",
             transform=axp.transAxes, fontsize=7.2, color=DIM)
    axp.text(0.97, 0.85, "▲" if up else "▼", transform=axp.transAxes,
             fontsize=9, color=("#ff6b6b" if up else "#5fd08a"),
             ha="right", va="top")

fig.text(0.045, 0.028, f"Live data pulled from FRED and the NY Fed on {date.today():%b %d, %Y}; "
                       "index computed with the same risk_index.py the dashboard uses. "
                       "Regenerate: python make_hero.py",
         fontsize=8, color=DIM)

os.makedirs("docs", exist_ok=True)
fig.savefig("docs/hero.png", dpi=140, facecolor=BG)
print("[+] wrote docs/hero.png")
