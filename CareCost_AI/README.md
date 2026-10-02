# CareCost AI

CareCost AI provides an early dataset-based estimate of hospital treatment costs and a separate lookup for Indian CGHS tariff references. The USD model is informational and does not produce a final hospital bill.

## Architecture

- `backend/app/ml` defines the shared model feature contract; `ml/` prepares the training data and contains the training template.
- `backend/app/services/model_service.py` loads the trained pipeline and predicts USD.
- `backend/app/services/cghs_service.py` searches the CGHS files and returns INR rates.
- `backend/app/services/insurance_service.py` calculates a deterministic INR coverage estimate from a supplied policy configuration.
- `backend/app/documents/` validates private bill uploads, extracts readable PDF text, and stores minimal metadata in SQLite.
- `backend/app/auth/` verifies a configured Sign ID/password account and issues short-lived server-side sessions.
- FastAPI serves both services through API routes; React requests go through `frontend/src/services/api.js`.

## Data

`data/raw/Hospital_Operations_Dataset.csv` contains 100,000 records and target `Treatment_Cost_USD`. Features are Age, Gender, Department, Diagnosis, Severity_Level, Length_of_Stay_Days, Wait_Time_Minutes, and Insurance_Type. Patient_ID and Doctor_ID are excluded identifiers; admission/discharge dates and post-treatment fields are excluded from the form. The inspected operations dataset has no missing values. The new claims, premium, policy-product, and handbook files remain at the project root as supplied; see [`ml/README.md`](ml/README.md) for training suitability and data handling. Other existing CSVs are preserved in `data/raw/`. CGHS references are in `data/reference/cghs/`.

CGHS INR rates remain separate from USD model training. The app does not apply an exchange rate. The operations dataset is not an India-specific pricing source, so its USD estimates are not a substitute for local hospital quotes.

## Install and run

From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python ml/prepare_cost_dataset.py
python ml/train_cost_model.py
python -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173` or `http://127.0.0.1:5173`. `.env.example` documents backend path and CORS settings. Both local Vite origins are allowed by default; `FRONTEND_ORIGIN` can add the configured frontend origin. Copy `backend/.env.example` to `backend/.env` for local authentication settings; `.env` is ignored by Git.

## Training and evaluation

The reproducible ML workspace and dataset review are documented in [`ml/README.md`](ml/README.md). `ml/prepare_cost_dataset.py` writes a PII-minimized training file from the operations CSV, retaining only the estimator features and target. `ml/train_cost_model.py` provides the training pipeline; the old `scripts/train_cost_model.py` command remains as a compatibility entry point. The pipeline uses an 80/20 split and fixed seed, imputes missing feature values, one-hot encodes categories, and fits a HistGradientBoostingRegressor. It prints MAE, RMSE, R², and MAPE on nonzero targets, and stores the model and metadata under `backend/models/`.

On the supplied data and seed 42, the current holdout metrics are MAE **$1,382.06**, RMSE **$2,725.27**, R² **0.874**, and MAPE **51.05%**. The high MAPE is a reminder that the estimate can be substantially off for individual cases.

## API

- `GET /api/health` reports service status.
- `POST /api/v1/estimate` accepts the eight model fields and returns predicted cost, `currency: USD`, source, estimate type, and bill disclaimer.
- `GET /api/v1/cghs/{code}` looks up a code across tiers and returns the procedure, category/speciality, available rates, tier, INR currency, and source file.
- `GET /api/v1/insurance/demo-policy` returns an editable sample policy labeled **Demo Policy**.
- `POST /api/v1/insurance/calculate` accepts a policy configuration and INR treatment/room amounts, then returns a deterministic coverage and out-of-pocket breakdown.
- `POST /api/v1/insurance/calculate-from-cghs` uses a selected CGHS code, tier, and rate type as the INR treatment reference for the same calculation. The returned label is **CGHS reference rate**, not actual hospital cost.

Invalid fields and ranges receive validation errors. An unavailable model returns 503; prediction errors do not expose stack traces. Estimate requests are small validated JSON, and source patient data is not exposed by the API. The app does not provide a chatbot or anomaly detection.

## Phase 2: Insurance and out-of-pocket estimate

The insurance engine is separate from the USD machine-learning model and uses INR-only values supplied by the user or selected CGHS reference rates. It applies the configured room limit, treatment sub-limit, deductible, co-pay, and remaining sum insured in that order. Previous claims reduce remaining cover rupee-for-rupee. The calculation uses Decimal amounts and reports room-rent excess, sub-limit excess, deductible, co-pay, policy-limit impact, insurer payable, and estimated out-of-pocket.

The frontend starts with a clearly labeled **Demo Policy** whose values are illustrative, not a real insurer product. The values can be edited. The percentage-of-sum-insured room rule is interpreted as a per-day room cap. Room-rent excess is excluded; policy-specific proportionate reductions to other charges are not modeled. Waiting-period eligibility is not calculated because policy tenure and treatment dates are not supplied. Pre- and post-hospitalization costs are not added unless separately provided. Only configured exclusions are applied, so the full policy wording must be verified.

The CGHS integration identifies its amount as a **CGHS reference rate**. A reference tariff is not an actual hospital bill or a guaranteed covered amount. Results are estimates from supplied terms; the final bill, network eligibility, policy interpretation, and insurer's claim decision must be confirmed with the hospital and insurer. The frontend labels values as known (user entry or reference), estimated (calculated), or unknown (needs verification).

## Phase 3A: Secure bill upload and extraction

The app accepts PDF, JPEG, and PNG files up to 10 MiB at `POST /api/v1/documents/upload`. It checks extension, declared MIME type, file signatures, PDF readability/page count, image format, and image dimensions. Stored files use random document IDs and permissions restricted to the server process where supported. The configured upload directory must be outside `frontend/`; by default it is `%LOCALAPPDATA%/CareCostAI/private-documents` on Windows, with a system temp-directory fallback if the app-data directory is unavailable. Set `DOCUMENT_UPLOAD_DIR` in `.env` to choose another private directory.

Readable PDF text is parsed with deterministic label and line-item rules. The extractor records INR or USD only when the document contains an explicit currency marker; otherwise currency needs review. The frontend formats extracted amounts using that marker and only offers the one-click insurance handoff for bills marked INR. Scanned PDFs and images use the optional OCR adapter only when `pytesseract`, Tesseract, and (for PDF) `pdf2image` plus Poppler are installed. When those tools are unavailable, the response reports `ocr_unavailable` and leaves extracted amounts blank. OCR output and original file contents are not logged. Patient names and identifiers are intentionally not extracted, saved in metadata, or returned. OCR/document extraction may contain errors and must be verified against the original hospital bill.

`GET /api/v1/documents/{document_id}` returns the extracted summary; there is no endpoint to retrieve the stored original file. Only the random ID, MIME type, timestamps/status, and extracted non-name fields are stored in SQLite. Retention defaults to 7 days and can be configured with `DOCUMENT_RETENTION_DAYS` (1–3650). Cleanup is manual: run `python scripts/cleanup_documents.py` from the project root to delete expired files and metadata. The frontend can copy a reviewed extracted total into the INR insurance form; it does not automatically treat the entire bill as eligible coverage. The USD ML estimator and INR CGHS/insurance paths remain separate.

## Role based Sign ID/password authentication

Login selects either Patient or Insurance Agent. The backend verifies the selected role's account using salted scrypt password hashes and stores an eight-hour session in an HttpOnly cookie. The local in-memory session store clears on restart and is intended for this single-process development setup, not multi-worker production. Use HTTPS and set `AUTH_COOKIE_SECURE=true` outside local HTTP development.

Local demo accounts (for development only):

- Patient Sign ID: `carecost-patient`; password: `PatientCare!2026`.
- Insurance Agent Sign ID: `carecost-agent`; password: `AgentCare!2026`.

Copy `backend/.env.example` to `backend/.env` when setting up a fresh checkout. It contains only these demo accounts' scrypt hashes; there are no plaintext passwords in the backend configuration. Replace the accounts before deployment. Run `..\.venv\Scripts\python.exe -m app.auth.seed_account` from `backend`; choose a role when prompted and enter the account Sign ID and password. Only the salted hash is saved.

Start FastAPI from the project root:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
   ```
Open the login page at [http://localhost:5173/](http://localhost:5173/). The patient dashboard is [http://localhost:5173/#overview](http://localhost:5173/#overview); the insurance-agent dashboard is [http://localhost:5173/#agent](http://localhost:5173/#agent). The role comes from the server session, so changing the hash does not grant a different role.

Authentication endpoints are `POST /api/v1/auth/login` (JSON `role`, `sign_id`, `password`), `POST /api/v1/auth/logout`, and `GET /api/v1/auth/me`. Role dashboards are `GET /api/v1/patient/overview`, `GET /api/v1/agent/overview`, `GET /api/v1/agent/policyholders`, `GET /api/v1/agent/policyholders/{sign_id}`, and `PATCH /api/v1/agent/claims/{claim_id}?status=...`. Agent management endpoints are restricted to the insurance-agent role. Estimator, CGHS, and insurance calculation endpoints require a signed-in patient or agent. Bill uploads and summaries require a patient session. Invalid credentials return one generic authentication error; API responses never include password hashes.

Agent policyholders and patient dashboard summary values are fabricated local demo data, clearly illustrative, and do not come from the supplied patient CSVs. Agent list/detail responses are restricted to the three assigned demo policyholders. Claim status updates are held in memory and reset when the backend restarts. Do not use this demo session store or sample records for production identity, claims, or patient data.
