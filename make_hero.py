#!/usr/bin/env python3
"""
Generate docs/hero.png - the README image.

The composite AI Displacement Risk Index is computed with the app's REAL logic
(normalize_series -> Z-scores, the same +/- signs and weighted sum from app.py).
The six underlying FRED/BLS series are illustrative stand-ins (the live app pulls
them from FRED/BLS/USCIS with your API keys), shaped to the documented thesis:
labor losing leverage to tech capital after the late-2022 LLM inflection.

Run:  python make_hero.py     (needs numpy + matplotlib)
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(7)
N = 32  # monthly points, Nov 2022 -> ~Jun 2025

BG, INK, DIM = "#0b1017", "#e6ebf2", "#8493a6"
IDX_FILL, IDX_LINE = "#673ab7", "#b39ddb"   # app.py index colors


def normalize_series(x):
    """Z-score — identical to app.py's normalize_series."""
    s = np.std(x)
    return (x - np.mean(x)) / s if s else x * 0


def trend(slope, noise=0.35, start=0.0):
    base = start + slope * np.linspace(0, 1, N)
    return base + rng.normal(0, noise, N) * np.std(base if np.std(base) else 1) * 0.5 + rng.normal(0, noise, N)


# --- six illustrative pillars (raw units), directions per the thesis ---
pillars = {
    "tech":  ("Tech Investment", "+", "#1f77b4", trend(3.0)),
    "prod":  ("Productivity", "+", "#ff7f0e", trend(1.6)),
    "jobs":  ("Job Openings Rate", "−", "#2ca02c", trend(-2.4)),
    "unemp": ("Grad Unemployment", "+", "#9467bd", trend(2.2)),
    "wage":  ("Wage Growth", "−", "#8c564b", trend(-1.2)),
    "prof":  ("Corporate Profits", "+", "#e377c2", trend(2.0)),
}
# weighted Z-score sum, EXACTLY as app.py builds Dynamic_Risk_Score (all weights 1.0)
sign = {"tech": 1, "prod": 1, "jobs": -1, "unemp": 1, "wage": -1, "prof": 1}
risk = np.zeros(N)
for k, (_, _, _, series) in pillars.items():
    risk += sign[k] * normalize_series(series)

# smooth a touch for display
risk_s = np.convolve(risk, np.ones(3) / 3, mode="same")
x = np.arange(N)

# month tick labels
labels = {0: "Nov '22", 7: "Jun '23", 14: "Jan '24", 21: "Aug '24", 28: "Mar '25"}

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": "#1b2740"})
fig = plt.figure(figsize=(13, 7.2), facecolor=BG)
fig.text(0.045, 0.945, "AI JOB-DISPLACEMENT & MACRO TRACKER",
         fontsize=16, fontweight="bold")
fig.text(0.045, 0.900, "composite Z-score risk index from 6 FRED / BLS factors  ·  "
                       "rising = labor losing leverage to tech capital  ·  live Streamlit dashboard",
         fontsize=9.5, color=DIM)

# ---- main: the risk index ----
ax = fig.add_axes([0.06, 0.40, 0.9, 0.40], facecolor="#0a0f18")
ax.fill_between(x, risk_s.min() - 0.5, risk_s, color=IDX_FILL, alpha=0.30)
ax.plot(x, risk_s, color=IDX_LINE, lw=2.2)
ax.axvline(0, color="#ff9800", ls="--", lw=1.1)
ax.text(0.4, ax.get_ylim()[1] * 0.86, " late-2022 LLM inflection\n (dashboard start)",
        color="#ff9800", fontsize=8)
ax.set_xticks(list(labels)); ax.set_xticklabels(labels.values())
ax.set_ylabel("Relative Risk Score (Z)", fontsize=9)
ax.tick_params(colors=DIM, labelsize=8)
ax.grid(color="#12203a", lw=0.6)
ax.set_xlim(0, N - 1)
ax.set_title("The AI Displacement Risk Index (Dynamic) — 6-factor weighted Z-score, adjustable live",
             fontsize=9.5, color=DIM, loc="left", pad=6)

# ---- bottom: the six contributing pillars ----
cols = 6
for i, (k, (name, sgn, col, series)) in enumerate(pillars.items()):
    axp = fig.add_axes([0.06 + i * 0.152, 0.09, 0.128, 0.20], facecolor="#0a0f18")
    z = normalize_series(series)
    axp.plot(x, z, color=col, lw=1.5)
    axp.fill_between(x, z.min(), z, color=col, alpha=0.12)
    axp.set_xticks([]); axp.set_yticks([])
    for s in axp.spines.values():
        s.set_edgecolor("#1b2740")
    up = z[-1] >= z[0]
    axp.set_title(f"{name}", fontsize=8.2, color=INK, loc="left", pad=3)
    axp.text(0.02, 0.06, f"{sgn} weight", transform=axp.transAxes, fontsize=7.2, color=DIM)
    axp.text(0.97, 0.85, "▲" if up else "▼", transform=axp.transAxes,
             fontsize=9, color=("#ff6b6b" if (up == (sign[k] > 0)) else "#5fd08a"),
             ha="right", va="top")

fig.text(0.045, 0.028, "Index computed with app.py's real Z-score formula; the 6 FRED/BLS input series "
                       "shown here are illustrative stand-ins. Regenerate: python make_hero.py",
         fontsize=8, color=DIM)

os.makedirs("docs", exist_ok=True)
fig.savefig("docs/hero.png", dpi=140, facecolor=BG)
print("[+] wrote docs/hero.png")
