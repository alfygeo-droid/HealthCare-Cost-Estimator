from __future__ import annotations

from collections import defaultdict

import numpy as np

from .procedure_meta import EXPECTED_CATEGORIES


def _stats(values: list[float]) -> dict:
    arr = np.array(values, dtype=float)
    if len(arr) < 2:
        med = float(arr[0]) if len(arr) else 0.0
        return {"median": med, "q1": med * 0.7, "q3": med * 1.4, "iqr": med * 0.7, "mean": med, "std": med * 0.2 or 1.0}
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    return {
        "median": float(np.median(arr)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr if iqr else np.std(arr) or 1),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr) or 1.0),
    }


def analyze_bill(payload: dict) -> dict:
    items = payload.get("items") or []
    procedure_code = payload.get("procedure_code")
    estimate_mid = float(payload.get("estimated_midpoint") or 0)
    expected_ranges = payload.get("expected_ranges") or {}

    anomalies = []
    total = 0.0
    by_name = defaultdict(list)
    by_cat_price = defaultdict(list)
    invoices = defaultdict(list)

    for i, item in enumerate(items):
        name = (item.get("item") or item.get("name") or f"item-{i}").strip()
        category = (item.get("category") or "Other").strip()
        qty = float(item.get("quantity") or 1)
        unit = float(item.get("unit_price") or 0)
        line_total = float(item.get("total_price") or unit * qty)
        inv = item.get("invoice_number") or payload.get("invoice_number")
        total += line_total
        rec = {**item, "item": name, "category": category, "quantity": qty, "unit_price": unit, "total_price": line_total, "index": i}
        by_name[name.lower()].append(rec)
        by_cat_price[category].append(unit)
        if inv:
            invoices[str(inv)].append(rec)

        # Quantity anomaly (gloves etc.)
        expected_qty = item.get("expected_quantity_range")
        if expected_qty:
            lo, hi = expected_qty
            if qty < lo or qty > hi:
                anomalies.append({
                    "type": "quantity",
                    "severity": "medium" if qty <= hi * 2 else "high",
                    "title": "Unusual quantity — requires verification",
                    "item": name,
                    "detail": f"Expected range: {lo}–{hi}. Claimed quantity: {qty}.",
                    "why": "Quantity is outside the expected range for this item.",
                    "action": "Verify with the hospital billing department.",
                    "amount": line_total,
                })
        elif name.lower() in ("surgical gloves", "gloves", "syringes") and qty > 40:
            anomalies.append({
                "type": "quantity",
                "severity": "medium",
                "title": "Unusual quantity — requires verification",
                "item": name,
                "detail": f"Claimed quantity: {qty}. Typical consumable counts are much lower.",
                "why": "Quantity is unusually high compared with typical ranges used in this prototype.",
                "action": "Verify with the hospital billing department.",
                "amount": line_total,
            })

    # Duplicates: same item name + same unit price appearing more than once
    for key, recs in by_name.items():
        if len(recs) >= 2:
            prices = [r["total_price"] for r in recs]
            if len(set(round(p, 2) for p in prices)) == 1 or len(recs) >= 2:
                anomalies.append({
                    "type": "duplicate",
                    "severity": "medium",
                    "title": "Potential duplicate charge",
                    "item": recs[0]["item"],
                    "detail": f"{recs[0]['item']} appears {len(recs)} times (₹{recs[0]['total_price']:,.0f}).",
                    "why": "The same item may have been billed more than once.",
                    "action": "Verify with the hospital billing department.",
                    "amount": recs[0]["total_price"],
                    "occurrences": len(recs),
                })

    # Price vs expected / IQR within category
    for cat, prices in by_cat_price.items():
        st = _stats(prices)
        for rec in items:
            if (rec.get("category") or "Other") != cat:
                continue
            unit = float(rec.get("unit_price") or 0)
            name = rec.get("item") or rec.get("name")
            exp = expected_ranges.get(name) or expected_ranges.get(cat)
            if exp:
                lo, hi = exp
                if unit > hi * 1.15:
                    anomalies.append({
                        "type": "price",
                        "severity": "high" if unit > hi * 1.8 else "medium",
                        "title": "Potential price anomaly",
                        "item": name,
                        "detail": f"Expected {cat.lower()} charge around ₹{lo:,.0f}–₹{hi:,.0f}. Actual unit price: ₹{unit:,.0f}.",
                        "why": "Unit price is outside the reference/expected range.",
                        "action": "Compare with the hospital's rate card and CGHS reference where applicable.",
                        "amount": unit,
                    })
            else:
                upper = st["q3"] + 1.5 * st["iqr"]
                z = (unit - st["mean"]) / (st["std"] or 1)
                if unit > upper and z > 2 and unit > 0:
                    anomalies.append({
                        "type": "price",
                        "severity": "medium",
                        "title": "Potential price anomaly",
                        "item": name,
                        "detail": f"Unit price ₹{unit:,.0f} is a high outlier versus other {cat} items on this bill (IQR/z-score).",
                        "why": "Statistical outlier on this bill — requires verification, not proof of error.",
                        "action": "Verify with the hospital billing department.",
                        "amount": unit,
                    })

    # Estimate vs final
    deviation_pct = None
    if estimate_mid:
        deviation_pct = round((total - estimate_mid) / estimate_mid * 100, 1)
        if abs(deviation_pct) >= 25:
            anomalies.append({
                "type": "estimate_vs_final",
                "severity": "high" if abs(deviation_pct) >= 40 else "medium",
                "title": "Estimated vs final bill anomaly",
                "item": "Bill total",
                "detail": f"Estimated: ₹{estimate_mid:,.0f}. Final: ₹{total:,.0f}. Difference: ₹{total - estimate_mid:,.0f} ({deviation_pct:+.1f}%).",
                "why": "The billed total differs substantially from the pre-admission estimate.",
                "action": "Request an itemised explanation of the difference.",
                "amount": total - estimate_mid,
            })

    # Consistency vs expected categories
    expected_cats = EXPECTED_CATEGORIES.get(procedure_code, EXPECTED_CATEGORIES["_default"])
    present = { (i.get("category") or "Other") for i in items }
    unexpected = [c for c in present if c not in expected_cats and c not in ("Other", "Implant", "ICU", "Package")]
    missing = [c for c in expected_cats if c not in present]
    consistency = {
        "expected_categories": expected_cats,
        "present_categories": sorted(present),
        "unexpected_categories": unexpected,
        "missing_categories": missing,
        "note": "This is a document/category consistency check, not a medical judgement.",
    }
    for cat in unexpected:
        anomalies.append({
            "type": "consistency",
            "severity": "low",
            "title": "Item requires verification",
            "item": cat,
            "detail": f"Category '{cat}' is not in the usual set for this procedure package view.",
            "why": "Financial/document consistency check only.",
            "action": "Confirm whether this service belongs to this admission.",
            "amount": 0,
        })

    # Deduplicate anomaly titles for same item+type
    seen = set()
    unique = []
    for a in anomalies:
        k = (a["type"], a.get("item"), a.get("detail"))
        if k in seen:
            continue
        seen.add(k)
        unique.append(a)

    expected_low = estimate_mid * 0.86 if estimate_mid else None
    expected_high = estimate_mid * 1.18 if estimate_mid else None

    return {
        "bill_total": round(total, 2),
        "item_count": len(items),
        "expected_range": [round(expected_low, 2), round(expected_high, 2)] if estimate_mid else None,
        "estimated_midpoint": estimate_mid or None,
        "deviation_percent": deviation_pct,
        "anomalies": unique,
        "anomaly_count": len(unique),
        "consistency": consistency,
        "method": "Rule-based duplicates + IQR/z-score price outliers + estimate deviation + category consistency.",
        "language_note": "Flags mean unusual pattern that may require verification. They do not establish fraud.",
        "warnings": [] if unique else ["No unusual patterns detected on this bill."],
        "assumptions": [
            "Duplicate detection uses repeated item names on the same bill.",
            "Price outliers use IQR / z-score within the uploaded bill when no reference range is supplied.",
        ],
    }


def final_bill_audit(estimate_breakdown: list[dict], bill_items: list[dict], estimate_mid: float, final_total: float) -> dict:
    est = {b["category"]: b["amount"] for b in (estimate_breakdown or [])}
    actual = defaultdict(float)
    for i in bill_items:
        actual[i.get("category") or "Other"] += float(i.get("total_price") or 0)
    cats = sorted(set(est) | set(actual))
    contributors = []
    for c in cats:
        e = est.get(c, 0)
        a = actual.get(c, 0)
        contributors.append({"category": c, "estimate": round(e, 2), "actual": round(a, 2), "delta": round(a - e, 2)})
    contributors.sort(key=lambda x: -abs(x["delta"]))
    return {
        "initial_estimate": round(estimate_mid, 2),
        "final_bill": round(final_total, 2),
        "difference": round(final_total - estimate_mid, 2),
        "contributors": contributors,
    }
