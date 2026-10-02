from __future__ import annotations


def calculate_insurance(payload: dict) -> dict:
    """Deterministic insurance arithmetic. Never uses an LLM."""
    total = float(payload.get("total_estimated_cost") or 0)
    sum_insured = float(payload.get("sum_insured") or 0)
    deductible = float(payload.get("deductible") or 0)
    copay_percent = float(payload.get("copay_percent") or 0)
    room_limit = payload.get("room_limit")
    room_rate = float(payload.get("room_rate") or 0)
    los = int(payload.get("length_of_stay") or 0)
    non_payable = float(payload.get("non_payable_expenses") or 0)
    if payload.get("non_payable_percent") and not payload.get("non_payable_expenses"):
        non_payable = total * float(payload["non_payable_percent"]) / 100.0
    exclusions = float(payload.get("exclusions") or 0)
    policy_type = payload.get("policy_type") or "indemnity"

    room_charge = room_rate * los
    room_capped = None
    room_excess = 0.0
    if room_limit not in (None, "", 0, "0"):
        room_limit = float(room_limit)
        room_capped = room_limit * los
        room_excess = max(0.0, room_charge - room_capped)
    else:
        room_limit = None

    eligible_before_cap = max(0.0, total - non_payable - exclusions - room_excess)
    above_si = max(0.0, eligible_before_cap - sum_insured) if sum_insured else 0.0
    capped = min(eligible_before_cap, sum_insured) if sum_insured else 0.0
    after_deductible = max(0.0, capped - deductible)
    copay_amount = round(after_deductible * copay_percent / 100.0, 2)
    insurer = round(after_deductible - copay_amount, 2)
    patient = round(total - insurer, 2)

    lines = [
        {"label": "Estimated hospital cost", "amount": round(total, 2)},
        {"label": "Non-payable expenses", "amount": -round(non_payable, 2)},
        {"label": "Exclusions", "amount": -round(exclusions, 2)},
        {"label": "Room-rent excess", "amount": -round(room_excess, 2)},
        {"label": "Base eligible expense", "amount": round(eligible_before_cap, 2)},
        {"label": "Amount above sum insured", "amount": -round(above_si, 2)},
        {"label": "Deductible", "amount": -round(min(deductible, capped), 2)},
        {"label": "Co-pay", "amount": -round(copay_amount, 2)},
        {"label": "Insurance estimated contribution", "amount": insurer},
        {"label": "Estimated patient share", "amount": patient},
    ]

    assumptions = [
        "Arithmetic is deterministic and does not depend on an LLM.",
        "Room-rent limit is applied as per-day × length of stay when provided.",
        "Non-payables and exclusions reduce eligible expense before sum-insured cap.",
        "This is not an insurer decision or pre-authorisation.",
    ]
    warnings = []
    if sum_insured <= 0:
        warnings.append("Sum insured is zero; entire bill is treated as patient share.")
    if room_excess > 0:
        warnings.append("Room category appears above the policy room-rent limit.")

    return {
        "policy_type": policy_type,
        "estimated_hospital_cost": round(total, 2),
        "insurance_eligible_amount": round(capped, 2),
        "insurance_estimated_contribution": insurer,
        "estimated_patient_share": patient,
        "room_charge": round(room_charge, 2),
        "room_limit_per_day": room_limit,
        "room_excess": round(room_excess, 2),
        "non_payable_expenses": round(non_payable, 2),
        "exclusions": round(exclusions, 2),
        "deductible": round(deductible, 2),
        "copay_percent": copay_percent,
        "copay_amount": copay_amount,
        "sum_insured": round(sum_insured, 2),
        "pre_hospitalization_days": int(payload.get("pre_hospitalization_days") or 0),
        "post_hospitalization_days": int(payload.get("post_hospitalization_days") or 0),
        "calculation_lines": lines,
        "warnings": warnings,
        "assumptions": assumptions,
    }
