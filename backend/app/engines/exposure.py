from __future__ import annotations

import numpy as np


def ninety_day_exposure(payload: dict) -> dict:
    """Financial scenario modelling. Does not invent medical outcomes."""
    patient_share = float(payload.get("patient_share") or 0)
    procedure_code = payload.get("procedure_code") or ""
    los = int(payload.get("length_of_stay") or 4)
    include_opd = payload.get("include_followup_opd", True)
    include_meds = payload.get("include_medicines", True)
    complication_weight = float(payload.get("complication_weight") or 0.15)

    # Assumption-driven add-ons (INR), scaled lightly by LOS / share
    followup_visits = 3 if include_opd else 0
    opd_unit = 800 if procedure_code.startswith("OP") else 1200
    meds_month = 2500 if include_meds else 0
    physio = 4500 if procedure_code.startswith("OR") else 0
    diagnostics = 2000

    base = followup_visits * opd_unit + meds_month * 3 + physio + diagnostics
    # Residual patient share already incurred is not double-counted; this is post-discharge only
    p50 = base
    p10 = max(0.0, base * 0.35)
    p90 = base + patient_share * complication_weight * 0.25 + los * 400

    rng = np.random.default_rng(42)
    sim = rng.gamma(shape=2.2, scale=max(p50 / 2.2, 1), size=2000)
    sim = np.clip(sim, 0, p90 * 1.4)
    p10_s, p50_s, p90_s = np.percentile(sim, [10, 50, 90])

    assumptions = [
        "This is financial scenario modelling, not a prediction of clinical complications.",
        f"Follow-up OPD visits assumed: {followup_visits} at ₹{opd_unit:,.0f} each." if include_opd else "Follow-up OPD excluded by user.",
        "Medicines assumed as a 90-day outpatient allowance, not a prescription.",
        f"Upper-band weight for unexpected extra expense: {complication_weight:.0%} applied only as a financial stress factor.",
        "P10/P50/P90 come from a seeded gamma simulation around those assumptions.",
    ]
    if procedure_code.startswith("OR"):
        assumptions.append("Physiotherapy sessions included as a typical joint-replacement financial add-on.")

    return {
        "p10": round(float(p10_s), 2),
        "p50": round(float(p50_s), 2),
        "p90": round(float(p90_s), 2),
        "components": {
            "followup_opd": followup_visits * opd_unit,
            "medicines_90d": meds_month * 3,
            "physiotherapy": physio,
            "diagnostics": diagnostics,
            "stress_weight": complication_weight,
        },
        "horizon_days": 90,
        "warnings": [],
        "assumptions": assumptions,
        "disclaimer": "90-day figures depend entirely on the stated assumptions and are not medical outcomes.",
    }
