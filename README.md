# CarePath — Healthcare Cost Estimator

A local, demonstrable healthcare financial-planning prototype: cost estimation, deterministic insurance calculations, hospital planning comparisons, bill review, multi-policy claim consistency checks, and 90-day exposure scenarios.

## Quick start

```powershell
python server.py
```

Open `http://127.0.0.1:8000`. No package installation is required for this local demo. `requirements.txt` documents the optional Flask/pandas/scikit-learn enhancement path specified in the project brief.

## Supplied dataset integration

`tariffs_tier1.csv`, `tariffs_tier2.csv`, and `tariffs_tier3.csv` are read live by `server.py` and power the reference tariff portion of estimates. Each estimate returns its source, source date and tier. The app intentionally treats these as reference tariffs, not hospital quotations.

The supplied `encounters.csv`, `procedures.csv`, `patients.csv`, `organizations.csv`, `payers.csv`, and `Hospital_Operations_Dataset.csv` are retained as historical/supporting source datasets. Their geography/currency and schema differ from the CGHS tariff data, so they are not silently blended into INR pricing.

`data/hospital_directory.csv` is the supplied India hospital directory. It powers hospital discovery by state, name, care type, and listed specialties. Run `python scripts/prepare_hospital_directory.py` to create a compact derived catalogue. Its Tier A/B/C labels describe source-listed service scope only; they do not imply quality, accreditation, pricing, or clinical suitability.

## Demo records

Run `python scripts/generate_demo_data.py` to create clearly labelled synthetic bill and multi-claim cases. The generator uses a fixed seed and includes a legitimate two-policy allocation and a duplicate-invoice scenario.

## Responsible-use statement

This is a financial estimation and decision-support prototype. Estimates are not hospital quotations or insurance approvals. Anomaly indicators identify unusual patterns that may require verification; they do not establish fraud. ML predictions depend on the availability and quality of labelled historical data.
