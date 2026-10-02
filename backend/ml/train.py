from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT.parent if (ROOT.parent / "Hospital_Operations_Dataset.csv").exists() else ROOT.parent
# backend/ml -> backend -> repo root
REPO = Path(__file__).resolve().parents[2]
OPS = REPO / "Hospital_Operations_Dataset.csv"
ENCOUNTERS = REPO / "encounters.csv"
POLICY_SCHEMA = REPO / "data" / "external" / "health_insurance_with_policy_product_and_company.csv"
CEP_HOSPITALS = REPO / "data" / "external" / "cep_empanelled_hospitals.csv"
ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

DEPTS = ["Orthopedics", "Cardiology", "General Surgery", "Neurology", "Oncology", "Emergency", "ICU"]


def _ops_frame(sample: int = 25000) -> pd.DataFrame:
    df = pd.read_csv(OPS)
    if len(df) > sample:
        df = df.sample(sample, random_state=42)
    df = df[df["Length_of_Stay_Days"].notna() & df["Treatment_Cost_USD"].notna()]
    med = df.groupby("Department")["Treatment_Cost_USD"].transform("median")
    df["cost_ratio"] = df["Treatment_Cost_USD"] / med.replace(0, np.nan)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["cost_ratio", "Length_of_Stay_Days"])
    df["cost_ratio"] = df["cost_ratio"].clip(0.4, 2.5)
    return df


def train() -> dict:
    df = _ops_frame()
    policy_rows = pd.read_csv(POLICY_SCHEMA) if POLICY_SCHEMA.exists() else pd.DataFrame()
    cep_rows = pd.read_csv(CEP_HOSPITALS) if CEP_HOSPITALS.exists() else pd.DataFrame()
    enc = OneHotEncoder(handle_unknown="ignore")
    X_cat = enc.fit_transform(df[["Department", "Severity_Level"]])
    X_num = df[["Length_of_Stay_Days"]].to_numpy()
    from scipy import sparse

    X = sparse.hstack([X_cat, X_num]).tocsr()
    y_los = df["Length_of_Stay_Days"].to_numpy()
    y_ratio = df["cost_ratio"].to_numpy()

    # LOS model actually uses dept+severity only
    X_los = enc.transform(df[["Department", "Severity_Level"]])
    results = {}
    models = {
        "linear": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=80, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingRegressor(random_state=42),
    }
    Xtr, Xte, ytr, yte = train_test_split(X, y_ratio, test_size=0.2, random_state=42)
    best_name, best_mae, best_est = None, 1e18, None
    for name, est in models.items():
        est.fit(Xtr, ytr)
        pred = est.predict(Xte)
        mae = float(mean_absolute_error(yte, pred))
        r2 = float(r2_score(yte, pred))
        results[name] = {"mae": mae, "r2": r2, "target": "department_median_cost_ratio"}
        if mae < best_mae:
            best_name, best_mae, best_est = name, mae, est

    los_model = RandomForestRegressor(n_estimators=60, random_state=42, n_jobs=-1)
    Xl_tr, Xl_te, yl_tr, yl_te = train_test_split(X_los, y_los, test_size=0.2, random_state=42)
    los_model.fit(Xl_tr, yl_tr)
    los_pred = los_model.predict(Xl_te)
    results["los_random_forest"] = {
        "mae": float(mean_absolute_error(yl_te, los_pred)),
        "r2": float(r2_score(yl_te, los_pred)),
        "target": "length_of_stay_days",
    }

    iso_stats = {}
    if ENCOUNTERS.exists():
        enc_df = pd.read_csv(ENCOUNTERS, usecols=["TOTAL_CLAIM_COST", "ENCOUNTERCLASS"])
        amounts = enc_df.loc[enc_df["TOTAL_CLAIM_COST"] > 0, "TOTAL_CLAIM_COST"].sample(
            min(8000, (enc_df["TOTAL_CLAIM_COST"] > 0).sum()), random_state=42
        )
        iso = IsolationForest(random_state=42, contamination=0.05)
        iso.fit(amounts.to_numpy().reshape(-1, 1))
        joblib.dump(iso, ART / "claim_iforest.joblib")
        iso_stats = {
            "n": int(len(amounts)),
            "median_usd": float(amounts.median()),
            "data_origin": "synthea_encounters_usd",
        }

    joblib.dump(
        {
            "encoder": enc,
            "ratio_model": best_est,
            "ratio_model_name": best_name,
            "los_model": los_model,
            "metrics": results,
            "best_ratio_model": best_name,
            "data_origin": "hospital_operations_usd",
            "data_sources": {
                "cost_training": {"file": str(OPS), "rows_used": int(len(df))},
                "policy_schema_reference": {"file": str(POLICY_SCHEMA), "rows": int(len(policy_rows)), "target": "Coverage_Amount"},
                "empanelled_hospital_reference": {"file": str(CEP_HOSPITALS), "rows": int(len(cep_rows)), "target": "hospital directory/tier reference"},
            },
            "policy_schema_summary": {
                "rows": int(len(policy_rows)),
                "max_coverage": float(policy_rows["Coverage_Amount"].max()) if not policy_rows.empty else 0,
                "median_coverage": float(policy_rows["Coverage_Amount"].median()) if not policy_rows.empty else 0,
            },
            "limitation": "Cost model is trained on USD hospital-operations rows; policy and empanelled-hospital datasets are integrated as coverage and directory references, not blended into INR final-bill pricing.",
            "claim_iforest_stats": iso_stats,
        },
        ART / "cost_bundle.joblib",
    )
    (ART / "metrics.json").write_text(
        __import__("json").dumps({"ratio_models": results, "best": best_name, "iforest": iso_stats}, indent=2),
        encoding="utf-8",
    )
    return {"best": best_name, "metrics": results, "iforest": iso_stats}


if __name__ == "__main__":
    print(train())
