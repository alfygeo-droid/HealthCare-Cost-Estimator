from __future__ import annotations

import json
import os

TEMPLATE = """Your estimated patient expense is ₹{patient:,.0f}. Estimated treatment cost is ₹{cost:,.0f}, of which insurance is estimated to contribute ₹{ins:,.0f}.
{anomaly_text}
These figures come from the application's calculators and reference data, not from this explanation layer. Estimates are not quotations or claim decisions."""


def _anomaly_text(anomalies: list) -> str:
    if not anomalies:
        return "No unusual bill or claim patterns were flagged in the structured results."
    bits = []
    for a in anomalies[:5]:
        if isinstance(a, str):
            bits.append(a)
        elif isinstance(a, dict):
            bits.append(a.get("title") or a.get("detail") or str(a))
    return "Items that may require verification: " + "; ".join(bits) + "."


def template_explain(structured: dict) -> str:
    cost = float(structured.get("estimated_cost") or structured.get("expected_midpoint") or 0)
    ins = float(structured.get("insurance_contribution") or 0)
    patient = float(structured.get("patient_share") or 0)
    anomalies = structured.get("anomalies") or []
    return TEMPLATE.format(patient=patient, cost=cost, ins=ins, anomaly_text=_anomaly_text(anomalies)).strip()


def explain(structured: dict, user_question: str | None = None) -> dict:
    """LLM may only rephrase provided JSON. Fallback is a deterministic template."""
    base = template_explain(structured)
    key = os.getenv("OPENAI_API_KEY") or ""
    used = "template"
    text = base
    if key:
        try:
            import httpx

            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            sys = (
                "You explain healthcare COST CALCULATOR results. "
                "Use ONLY numbers and flags in the JSON. Never invent prices, tariffs, coverage, or medical facts. "
                "Never say fraud. Say unusual / requires verification. Keep to 3-6 sentences."
            )
            user = json.dumps({"question": user_question, "results": structured}, ensure_ascii=False)
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": sys},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=30,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            used = "llm"
        except Exception:
            text = base
            used = "template_fallback"
    return {
        "explanation": text,
        "engine": used,
        "grounding": structured,
        "assumptions": [
            "Explanation layer does not calculate insurance or tariffs.",
            "If no API key is configured, a template is used.",
        ],
        "warnings": [] if used != "template_fallback" else ["LLM call failed; template explanation used."],
    }
