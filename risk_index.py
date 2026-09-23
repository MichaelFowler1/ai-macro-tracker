"""
The AI Displacement Risk Index, shared by app.py and make_hero.py.

Each factor is turned into something that doesn't trend on its own:
dollar and output series become year-over-year growth (dollar series net of
CPI inflation, so 2022's nominal wage gains don't read as labor strength),
and rates stay as rates.
Every factor is then Z-scored against a fixed pre-pandemic baseline
(2015-2019), so 0 means "normal before COVID and before LLMs" and a value
doesn't change when you move the dashboard's start date.

The index is the weighted average of those Z-scores, so it stays in
standard-deviation units however many factors loaded.
"""
import pandas as pd

BASELINE = ("2015-01-01", "2019-12-31")

# key: (label, sign, transform, source key)
# sign +1 means a higher reading = labor losing leverage
FACTORS = {
    "tech":     ("Real Tech Investment Growth", +1, "real_yoy_q", "total_tech_investment"),
    "prod":     ("Productivity Growth", +1, "yoy_q", "productivity"),
    "jobs":     ("Job Openings Rate", -1, "level", "job_openings_rate"),
    "gap":      ("Young Grad Gap", +1, "ma3", "young_grad_gap"),
    "wage":     ("Real Wage Growth", -1, "real_yoy_m", "wages"),
    "labshare": ("Labor Share Change", -1, "yoy_q", "labor_share"),
    "underemp": ("Grad Underemployment", +1, "level", "underemp"),
}


def _transform(series, how, cpi):
    if how == "yoy_q":   # quarterly level -> YoY % growth
        return series.pct_change(4) * 100
    if how == "real_yoy_q":   # quarterly dollars -> YoY % growth minus CPI inflation
        inflation = cpi.resample("QS").mean().pct_change(4) * 100
        return series.pct_change(4) * 100 - inflation.reindex(series.index)
    if how == "real_yoy_m":   # monthly dollars -> YoY % growth minus CPI inflation
        inflation = cpi.pct_change(12) * 100
        return series.pct_change(12) * 100 - inflation.reindex(series.index)
    if how == "ma3":     # not seasonally adjusted rate -> 3-month average
        return series.rolling(3).mean()
    return series


def _to_monthly(series):
    """
    Put every factor on a month-start grid. A quarterly value (dated at the
    quarter's first month) fills only the months inside its own quarter, so
    nothing is carried past the period it describes.
    """
    series = series.dropna()
    months = pd.date_range(series.index.min(), series.index.max() + pd.offsets.MonthBegin(2), freq="MS")
    return series.reindex(months).ffill(limit=2)


def factor_scores(sources):
    """
    sources: dict of raw series keyed like FACTORS' source keys, plus 'cpi'.
    Returns a monthly DataFrame of signed baseline Z-scores, one column per
    factor. Factors whose source is missing or empty are left out.
    """
    cpi = sources.get("cpi")
    scores = {}
    for key, (_, sign, how, src) in FACTORS.items():
        raw = sources.get(src)
        if raw is None or raw.empty:
            continue
        if how.startswith("real_") and (cpi is None or cpi.empty):
            continue
        s = _to_monthly(_transform(raw, how, cpi))
        base = s.loc[BASELINE[0]:BASELINE[1]]
        if len(base) < 2 or base.std() == 0:
            continue
        scores[key] = sign * (s - base.mean()) / base.std()
    return pd.DataFrame(scores).dropna()


def contributions(scores, weights=None):
    """
    Each factor's share of the index: weight * Z-score / total weight.
    Summing across a row gives the index. weights: dict key -> float (default 1).
    """
    weights = weights or {}
    w = pd.Series({k: weights.get(k, 1.0) for k in scores.columns}, dtype=float)
    if w.sum() == 0:
        return scores * 0
    return scores * w / w.sum()


def risk_index(scores, weights=None):
    """Weighted average of factor Z-scores."""
    return contributions(scores, weights).sum(axis=1)
