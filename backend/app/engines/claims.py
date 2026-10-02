from __future__ import annotations

from collections import defaultdict

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover
    IsolationForest = None


def _indicator(ok: bool, pass_text: str, fail_text: str, severity="medium"):
    return {
        "ok": ok,
        "severity": "info" if ok else severity,
        "text": pass_text if ok else fail_text,
    }


def claim_risk(payload: dict) -> dict:
    """Explainable rule-based claim-risk. Never labelled as fraud."""
    claimed = float(payload.get("claimed_amount") or payload.get("bill_total") or 0)
    estimate = float(payload.get("estimated_midpoint") or 0)
    anomalies = payload.get("bill_anomalies") or []
    invoice = payload.get("invoice_number")
    invoices_seen = payload.get("invoices_in_other_claims") or []
    missing_fields = [f for f in ("patient_id", "hospital_id", "procedure_code", "admission_date") if not payload.get(f)]
    repeated_days = int(payload.get("repeat_claims_days") or 0)
    amount_high = bool(payload.get("unusually_high_amount"))
    if estimate and claimed > estimate * 1.5:
        amount_high = True

    indicators = []
    flags = 0

    if estimate:
        within = claimed <= estimate * 1.35
        indicators.append(_indicator(
            within,
            "Claim amount is within a broad expected range versus the estimate.",
            f"Claim amount ₹{claimed:,.0f} is substantially above the estimate ₹{estimate:,.0f}.",
            "high" if claimed > estimate * 1.6 else "medium",
        ))
        if not within:
            flags += 1
    else:
        indicators.append(_indicator(True, "No pre-admission estimate was supplied for amount comparison.", "", "info"))

    dup_items = [a for a in anomalies if a.get("type") == "duplicate"]
    indicators.append(_indicator(
        not dup_items,
        "No repeated bill line item detected.",
        dup_items[0]["detail"] if dup_items else "Repeated service detected.",
        "medium",
    ))
    if dup_items:
        flags += 1

    price_items = [a for a in anomalies if a.get("type") == "price"]
    indicators.append(_indicator(
        not price_items,
        "No price outlier versus reference/expected range.",
        price_items[0]["detail"] if price_items else "Unusual price compared with reference range.",
        "medium",
    ))
    if price_items:
        flags += 1

    qty_items = [a for a in anomalies if a.get("type") == "quantity"]
    indicators.append(_indicator(
        not qty_items,
        "No unusual quantities flagged.",
        qty_items[0]["detail"] if qty_items else "Unusually high quantity.",
        "medium",
    ))
    if qty_items:
        flags += 1

    dup_inv = invoice and invoice in invoices_seen
    indicators.append(_indicator(
        not dup_inv,
        "No duplicate invoice detected across claims.",
        f"Invoice {invoice} appears in more than one claim.",
        "high",
    ))
    if dup_inv:
        flags += 1

    indicators.append(_indicator(
        not missing_fields,
        "Required claim fields appear present.",
        f"Missing information: {', '.join(missing_fields)}.",
        "low",
    ))
    if missing_fields:
        flags += 1

    indicators.append(_indicator(
        repeated_days <= 0 or repeated_days > 30,
        "No repeated claim in a short period was supplied.",
        f"Another claim for the same patient/procedure within {repeated_days} days.",
        "medium",
    ))
    if 0 < repeated_days <= 30:
        flags += 1

    if amount_high:
        indicators.append(_indicator(False, "", "Claimed amount is unusually high versus the available estimate/reference.", "high"))
        flags += 1
    else:
        indicators.append(_indicator(True, "No additional high-amount rule triggered.", "", "info"))

    if flags == 0:
        level = "LOW"
    elif flags <= 2:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "level": level,
        "indicator_count": flags,
        "indicators": indicators,
        "disclaimer": "Risk level is an explainable indicator for verification. It does not prove fraud or decide a claim.",
        "assumptions": ["Rules are transparent and listed. Thresholds are prototype defaults."],
        "warnings": [],
    }


def cross_check_claims(claims: list[dict], hospital_bill_total: float | None = None) -> dict:
    """Distinguish legitimate multi-policy splits from potential overlaps."""
    findings = []
    by_invoice = defaultdict(list)
    by_proc_dates = defaultdict(list)
    total_claimed = 0.0

    for c in claims:
        total_claimed += float(c.get("claimed_amount") or 0)
        inv = c.get("invoice_number")
        if inv:
            by_invoice[inv].append(c)
        key = (
            c.get("patient_id"),
            c.get("hospital_id"),
            c.get("procedure_code") or c.get("procedure"),
            c.get("admission_date"),
        )
        by_proc_dates[key].append(c)

    overlap = False
    for inv, group in by_invoice.items():
        if len(group) > 1:
            ids = [g.get("claim_id") for g in group]
            amounts = [float(g.get("claimed_amount") or 0) for g in group]
            # If amounts sum near bill and policies differ, likely coordination of benefits
            findings.append({
                "type": "same_invoice",
                "severity": "high",
                "title": "Potential claim overlap",
                "detail": f"Invoice {inv} and the same procedure appear in multiple claims ({', '.join(str(i) for i in ids)}).",
                "requires_verification": True,
                "claims": ids,
                "amounts": amounts,
            })
            overlap = True

    legitimate_split = False
    if hospital_bill_total and len(claims) >= 2:
        if abs(total_claimed - hospital_bill_total) <= max(1.0, 0.02 * hospital_bill_total):
            policies = {c.get("policy_id") for c in claims}
            if len(policies) >= 2 and not overlap:
                legitimate_split = True
            elif len(policies) >= 2 and overlap:
                # Same invoice + amounts that still sum to bill: still flag invoice, but note possible COB
                findings.append({
                    "type": "coordination",
                    "severity": "medium",
                    "title": "Same invoice across policies",
                    "detail": "Amounts sum to the hospital bill, but the same invoice number is reused. Requires verification.",
                    "requires_verification": True,
                })

    if hospital_bill_total and total_claimed > hospital_bill_total * 1.05:
        findings.append({
            "type": "amount_overlap",
            "severity": "high",
            "title": "Potential overlapping claim amount",
            "detail": f"Claimed total ₹{total_claimed:,.0f} exceeds hospital bill ₹{hospital_bill_total:,.0f}.",
            "requires_verification": True,
        })
        overlap = True

    if legitimate_split:
        summary = "MULTI-POLICY CLAIM CONSISTENCY"
        detail = "No obvious duplicate expense detected. Claimed amounts add up to the hospital bill across policies."
    elif overlap:
        summary = "POTENTIAL CLAIM OVERLAP"
        detail = "The same invoice, procedure, or amount pattern appears in multiple claims. Requires verification."
    else:
        summary = "CROSS-CHECK COMPLETE"
        detail = "No obvious duplicate expense pattern was detected with the supplied records."

    return {
        "summary": summary,
        "detail": detail,
        "legitimate_multi_policy": legitimate_split,
        "requires_verification": overlap and not legitimate_split,
        "hospital_bill": hospital_bill_total,
        "total_claimed": round(total_claimed, 2),
        "findings": findings,
        "disclaimer": "Multiple claims for one hospitalisation are not automatically improper. This is a consistency check.",
        "warnings": [],
        "assumptions": ["Comparison uses patient, hospital, dates, procedure, invoice and amounts supplied by the user/demo."],
    }


def anomaly_portfolio(amounts: list[float], contamination: float = 0.08) -> dict:
    arr = np.array(amounts, dtype=float).reshape(-1, 1)
    n = len(arr)
    if n < 10:
        return {
            "total": n,
            "method": "insufficient_sample",
            "normal": n,
            "requires_verification": 0,
            "high_anomaly": 0,
            "note": "Need more labelled claims for statistical/ML portfolio scoring.",
        }
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1 or 1
    iqr_flags = (arr[:, 0] > q3 + 1.5 * iqr) | (arr[:, 0] < q1 - 1.5 * iqr)
    mean, std = float(arr.mean()), float(arr.std() or 1)
    z_flags = np.abs((arr[:, 0] - mean) / std) > 3
    iso_flags = np.zeros(n, dtype=bool)
    method = "IQR + z-score"
    if IsolationForest is not None and n >= 30:
        iso = IsolationForest(random_state=42, contamination=contamination)
        iso_flags = iso.fit_predict(arr) == -1
        method = "IQR + z-score + IsolationForest (sklearn)"
    high = iso_flags | (iqr_flags & z_flags)
    review = (iqr_flags | z_flags | iso_flags) & ~high
    return {
        "total": n,
        "method": method,
        "normal": int((~review & ~high).sum()),
        "requires_verification": int(review.sum()),
        "high_anomaly": int(high.sum()),
        "thresholds": {"q1": float(q1), "q3": float(q3), "mean": mean, "std": std},
        "note": "Statistical outliers among labelled claim amounts. Not a fraud determination.",
        "data_origin": "mix of demo synthetic claims and optional Synthea USD claims (flagged in source).",
    }
