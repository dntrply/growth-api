import os, logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
# ── Custom OpenAPI with servers block ──────────────────────────────────────────
from fastapi.openapi.utils import get_openapi


# ── Create FastAPI app ─────────────────────────────────────────────────────────
app = FastAPI()


def custom_openapi():
    """Inject a stable servers list so ChatGPT recognizes only one host."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="WHO Growth API",
        version="0.1.0",
        description="Compute WHO z-scores for children (education only).",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        { "url": "https://growth-api.vercel.app" }   # ← your permanent alias
    ]

    # 2) Tell ChatGPT this call is safe to 'always allow'
    if "/zscore" in openapi_schema["paths"]:
        openapi_schema["paths"]["/zscore"]["post"]["x-openai-isConsequential"] = False

    app.openapi_schema = openapi_schema
    return openapi_schema

# Register the custom generator once
app.openapi = custom_openapi

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Setup paths ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

# ── Load LMS tables once at startup ───────────────────────────────────────────
tables = {
    ("M", "length"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Length-for-age-Percentiles_LMS.csv")),
    ("M", "weight"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Weight-for-age-Percentiles_LMS.csv")),
    ("M", "wfl"):    pd.read_csv(os.path.join(DATA_DIR, "WHO-Boys-Weight-for-length-Percentiles_LMS.csv")),
    ("F", "length"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Girls-Length-for-age-Percentiles_LMS.csv")),
    ("F", "weight"): pd.read_csv(os.path.join(DATA_DIR, "WHO-Girls-Weight-for-age-Percentiles_LMS.csv")),
    ("F", "wfl"):    pd.read_csv(os.path.join(DATA_DIR, "WHO-Girls-Weight-for-length-Percentiles_LMS.csv")),
}


# ── Request schema ─────────────────────────────────────────────────────────────
class ZScoreRequest(BaseModel):
    sex: str            # "M" or "F"
    indicator: str      # "length", "weight", or "wfl"
    years: int = None
    months: int = None
    length: float = None
    weight: float = None

# ── Endpoint ───────────────────────────────────────────────────────────────────
@app.post("/zscore")
async def compute_z(request: ZScoreRequest):
    logger.info(f"POST /zscore - payload: {request.dict()}")
    sex = request.sex.upper()
    ind = request.indicator.lower()

    # Log the API call
    logger.info(f"API call - Sex: {sex}, Indicator: {ind}, Years: {request.years}, Months: {request.months}, Length: {request.length}, Weight: {request.weight}")

    # 1) Select the correct table
    df = tables.get((sex, ind))
    if df is None:
        raise HTTPException(status_code=400, detail="Unknown sex or indicator")

    # 2) Lookup row based on indicator
    if ind in ("length", "weight"):
        if request.years is None or request.months is None:
            raise HTTPException(status_code=400, detail="Provide both years and months")
        total_months = request.years * 12 + request.months
        if "Month" not in df.columns:
            raise HTTPException(status_code=500, detail="Invalid table: missing Month column")
        df["Month"] = pd.to_numeric(df["Month"], errors="coerce")
        row = df.loc[df["Month"] == total_months]
        meas = request.length if ind == "length" else request.weight
        if meas is None:
            raise HTTPException(status_code=400, detail=("Provide length (cm)" if ind == "length" else "Provide weight (kg)"))
    else:
        # weight-for-length uses length as key
        if request.length is None or request.weight is None:
            raise HTTPException(status_code=400, detail="Provide both length (cm) and weight (kg)")
        key_val = request.length
        col0 = df.columns[0]
        df[col0] = pd.to_numeric(df[col0], errors="coerce")
        row = df.loc[df[col0] == key_val]
        meas = request.weight

    if row.empty:
        raise HTTPException(status_code=400, detail="No data for given age or length")

    # 3) Extract L, M, S
    L = float(row["L"].values[0])
    M = float(row["M"].values[0])
    S = float(row["S"].values[0])

    # 4) Compute z-score
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
    else:
        if z < -3:
            cat = "Severe wasting"
        elif z < -2:
            cat = "Wasting"
        elif z <= 2:
            cat = "Normal"
        else:
            cat = "Overweight"

    return {"z_score": z_rounded, "classification": cat}
