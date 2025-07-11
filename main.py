import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

# ── Configure paths ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── Load LMS tables ─────────────────────────────────────────────────────────────
tables = {
    ("M", "length"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Length-for-age-Percentiles_LMS.csv")),
    ("M", "weight"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Weight-for-age-Percentiles_LMS.csv")),
    ("M", "wfl"):    pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Weight-for-length-Percentiles_LMS.csv")),
    ("F", "weight"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Girls-Weight-for-age-Percentiles_LMS.csv")),
    ("F", "wfl"):    pd.read_csv(os.path.join(DATA_DIR, "WHO-Girls-Weight-for-length-Percentiles_LMS.csv")),
}

app = FastAPI(title="WHO Growth API")

# ── Request schema ──────────────────────────────────────────────────────────────
class ZScoreRequest(BaseModel):
    sex: str                   # "M" or "F"
    indicator: str             # "length", "weight", or "wfl"
    years: int = None          # completed years (for length & weight)
    months: int = None         # additional months
    length: float = None       # cm (for length-for-age or wfl length)
    weight: float = None       # kg (for weight-for-age or wfl weight)

# ── Endpoint ────────────────────────────────────────────────────────────────────
@app.post("/zscore")
def compute_z(request: ZScoreRequest):
    sex = request.sex.upper()
    ind = request.indicator.lower()

    # 1) Pick the right table
    df = tables.get((sex, ind))
    if df is None:
        raise HTTPException(400, detail="Unknown sex or indicator")

    # 2) Match on age (months) or length (cm)
    if ind in ("length", "weight"):
        # require age + the correct measurement
        if request.years is None or request.months is None:
            raise HTTPException(400, detail="Provide both years and months")
        total_months = request.years * 12 + request.months

        # ensure the CSV has a “Month” column
        if "Month" not in df.columns:
            raise HTTPException(500, detail="Invalid table: missing Month")
        df["Month"] = pd.to_numeric(df["Month"], errors="coerce")
        row = df.loc[df["Month"] == total_months]

        # pick the measurement
        meas = request.length if ind == "length" else request.weight
        if meas is None:
            raise HTTPException(
                400,
                detail=f"Provide {'length (cm)' if ind=='length' else 'weight (kg)'}"
            )

    else:  # indicator == "wfl"
        # require both length & weight
        if request.length is None or request.weight is None:
            raise HTTPException(400, detail="Provide both length (cm) and weight (kg)")
        key_val = request.length
        col0 = df.columns[0]
        df[col0] = pd.to_numeric(df[col0], errors="coerce")
        row = df.loc[df[col0] == key_val]
        meas = request.weight

    if row.empty:
        raise HTTPException(400, detail="No data for given age or length")

    # 3) Extract L, M, S
    L = float(row["L"].values[0])
    M = float(row["M"].values[0])
    S = float(row["S"].values[0])

    # 4) Compute the z-score
    z = ((meas / M) ** L - 1) / (L * S)
    z_rounded = round(z, 1)

    # 5) Classify
    if ind == "length":
        if z < -3:
            cat = "Severely stunted"
        elif z < -2:
            cat = "Moderately stunted"
        elif z <= 2:
            cat = "Normal"
        else:
            cat = "Tall"

    elif ind == "weight":
        if z < -3:
            cat = "Severe underweight"
        elif z < -2:
            cat = "Underweight"
        elif z <= 2:
            cat = "Normal"
        else:
            cat = "Overweight"

    else:  # wfl
        if z < -3:
            cat = "Severe wasting"
        elif z < -2:
            cat = "Wasting"
        elif z <= 2:
            cat = "Normal"
        else:
            cat = "Overweight"

    return {"z_score": z_rounded, "classification": cat}
