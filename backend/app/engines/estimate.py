from __future__ import annotations

from ..db import get_conn, rows_to_dicts
from .procedure_meta import (
    DEFAULT_LOS,
    DRIVER_SHARES,
    EXPECTED_CATEGORIES,
    FEATURED_CODES,
    ROOM_KEYS,
    SPECIALITY_TO_DEPT,
)


def pick_tariff_rate(row: dict, accreditation: str) -> float:
    acc = (accreditation or "nabh").lower()
    if acc in ("non_nabh", "non-nabh", "non nabh"):
        return float(row["non_nabh_rate"] or 0)
    if acc in ("super", "super_speciality", "super-speciality"):
        return float(row["super_speciality_rate"] or 0)
    return float(row["nabh_rate"] or 0)


def get_tariff(cghs_code: str, city_tier: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM tariffs WHERE cghs_code = ? AND city_tier = ?",
        (cghs_code, city_tier),
    ).fetchone()
    return dict(row) if row else None


def search_procedures(q: str = "", featured_only: bool = False, limit: int = 80) -> list[dict]:
    conn = get_conn()
    if featured_only:
        placeholders = ",".join("?" * len(FEATURED_CODES))
        rows = conn.execute(
            f"""SELECT cghs_code, procedure_name, speciality,
                       MIN(nabh_rate) AS min_nabh, MAX(nabh_rate) AS max_nabh
                FROM tariffs WHERE cghs_code IN ({placeholders})
                GROUP BY cghs_code, procedure_name, speciality
                ORDER BY procedure_name""",
            FEATURED_CODES,
        ).fetchall()
        return rows_to_dicts(rows)
    if q:
        like = f"%{q}%"
        rows = conn.execute(
            """SELECT cghs_code, procedure_name, speciality,
                      MIN(nabh_rate) AS min_nabh, MAX(nabh_rate) AS max_nabh
               FROM tariffs
               WHERE procedure_name LIKE ? OR cghs_code LIKE ? OR speciality LIKE ?
               GROUP BY cghs_code, procedure_name, speciality
               ORDER BY procedure_name LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()
        return rows_to_dicts(rows)
    rows = conn.execute(
        """SELECT cghs_code, procedure_name, speciality,
                  MIN(nabh_rate) AS min_nabh, MAX(nabh_rate) AS max_nabh
           FROM tariffs
           GROUP BY cghs_code, procedure_name, speciality
           ORDER BY procedure_name LIMIT ?""",
        (limit,),
    ).fetchall()
    return rows_to_dicts(rows)


def get_hospital(hospital_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,)).fetchone()
    return dict(row) if row else None


def list_hospitals() -> list[dict]:
    conn = get_conn()
    return rows_to_dicts(conn.execute("SELECT * FROM hospitals ORDER BY city, name").fetchall())


def _ml_los_hint(speciality: str) -> dict:
    """Use trained LOS model if present; otherwise None."""
    try:
        from ..ml.predict import predict_los
    except Exception:
        return {"available": False}
    dept = SPECIALITY_TO_DEPT.get(speciality, "General Surgery")
    try:
        pred = predict_los(dept)
        return {"available": True, "predicted_los": pred, "department_mapped": dept, "data_origin": "hospital_operations_usd"}
    except Exception:
        return {"available": False}


def estimate_cost(payload: dict) -> dict:
    code = payload.get("procedure_code") or payload.get("cghs_code")
    city_tier = payload.get("city_tier") or "Tier I"
    accreditation = payload.get("accreditation") or "nabh"
    room_type = (payload.get("room_type") or "private").lower()
    hospital_id = payload.get("hospital_id")
    warnings = []
    assumptions = [
        "Reference tariff is a CGHS reference rate, not a hospital quotation.",
        "Room, diagnostics and medicines shown as illustrative cost drivers around the package.",
        "ML predictions are used only when labelled historical data can be mapped; otherwise tariff fallback applies.",
    ]

    tariff = get_tariff(code, city_tier)
    if not tariff:
        # try any tier
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM tariffs WHERE cghs_code = ? LIMIT 1", (code,)
        ).fetchone()
        if not row:
            raise ValueError(f"No matching tariff for procedure {code}")
        tariff = dict(row)
        warnings.append(f"No row for {code} in {city_tier}; used {tariff['city_tier']} instead.")

    ref = pick_tariff_rate(tariff, accreditation)
    hospital = get_hospital(hospital_id) if hospital_id else None
    markup = float(hospital["markup"]) if hospital else float(payload.get("markup") or 1.12)
    if hospital:
        city_tier = hospital.get("city_tier") or city_tier
        accreditation = hospital.get("accreditation") or accreditation
        ref_row = get_tariff(code, city_tier) or tariff
        ref = pick_tariff_rate(ref_row, accreditation)
        tariff = ref_row

    los = int(payload.get("length_of_stay") or DEFAULT_LOS.get(code, 4))
    ml = _ml_los_hint(tariff.get("speciality") or "")
    if payload.get("use_ml_los") and ml.get("available"):
        los = max(1, int(round(ml["predicted_los"])))
        assumptions.append("Length of stay adjusted using Hospital Operations labelled stays (USD dataset; mapped by department).")

    room_key = ROOM_KEYS.get(room_type, "room_private")
    room_rate = 4000.0
    if hospital:
        room_rate = float(hospital.get(room_key) or room_rate)
    else:
        room_rate = float(payload.get("room_rate") or {"general": 2500, "sharing": 3500, "private": 5500, "icu": 9000}.get(room_type, 5500))

    package = ref * markup
    room_cost = room_rate * los
    # Blend: CGHS packages are typically inclusive of stay at empanelled rates.
    # We show package as surgery-dominant, then add room upgrade vs a general-ward baseline.
    baseline_room = 2500 * los
    room_upgrade = max(0.0, room_cost - baseline_room)

    shares = DRIVER_SHARES.copy()
    cats = EXPECTED_CATEGORIES.get(code, EXPECTED_CATEGORIES["_default"])
    breakdown = []
    remaining_share = sum(shares[c] for c in cats if c in shares) or 1.0
    for cat in cats:
        share = shares.get(cat, 0.05) / remaining_share
        amount = round(package * share, 2)
        if cat == "Room":
            amount = round(amount + room_upgrade, 2)
        breakdown.append({"category": cat, "amount": amount, "share": round(share, 3)})

    midpoint = round(sum(b["amount"] for b in breakdown), 2)
    # Statistical band: ±12% tariff uncertainty + room upgrade variance
    low = round(midpoint * 0.86, 2)
    high = round(midpoint * 1.18, 2)

    ml_mid = None
    ml_info = {"used": False, "reason": "No labelled INR final-bill dataset mapped to this CGHS code."}
    try:
        from ..ml.predict import predict_additional_ratio

        dept = SPECIALITY_TO_DEPT.get(tariff.get("speciality") or "", "General Surgery")
        ratio = predict_additional_ratio(dept, los)
        ml_mid = round(midpoint * ratio, 2)
        ml_info = {
            "used": True,
            "additional_ratio": ratio,
            "model_midpoint": ml_mid,
            "data_origin": "hospital_operations_usd",
            "note": "Ratio learned from labelled hospital-operations costs (USD) mapped by department; applied to CGHS-based estimate.",
        }
        low = round(min(low, ml_mid * 0.82), 2)
        high = round(max(high, ml_mid * 1.22), 2)
        midpoint = round((midpoint + ml_mid) / 2, 2)
    except Exception:
        warnings.append("ML cost model unavailable or untrained; showing reference-tariff-based estimate.")

    confidence = "medium" if ml_info.get("used") else "tariff-only"
    if not ml_info.get("used"):
        warnings.append(
            "No labelled historical data is available for this procedure in INR. "
            "We are showing the reference-tariff-based estimate instead of an ML prediction."
        )

    drivers = [b["category"] for b in sorted(breakdown, key=lambda x: -x["amount"])[:5]]

    return {
        "procedure_code": code,
        "procedure_name": tariff["procedure_name"],
        "speciality": tariff.get("speciality"),
        "city_tier": tariff["city_tier"],
        "accreditation": accreditation,
        "hospital": {"id": hospital["id"], "name": hospital["name"], "city": hospital["city"], "is_synthetic": True}
        if hospital
        else None,
        "room_type": room_type,
        "length_of_stay": los,
        "room_rate_per_day": room_rate,
        "reference_tariff": round(ref, 2),
        "hospital_markup": markup,
        "estimated_low": low,
        "estimated_high": high,
        "expected_midpoint": midpoint,
        "breakdown": breakdown,
        "major_cost_drivers": drivers,
        "confidence": confidence,
        "ml": ml_info,
        "los_model": ml,
        "tariff_source": {
            "source": tariff.get("source"),
            "source_date": tariff.get("source_date"),
            "city_tier": tariff["city_tier"],
            "procedure": tariff["procedure_name"],
            "cghs_code": code,
            "reference_rate": round(ref, 2),
            "note": "Reference tariff ≠ final hospital bill.",
        },
        "warnings": warnings,
        "assumptions": assumptions,
        "disclaimer": "This is a financial estimate, not a hospital quotation or insurance approval.",
    }
