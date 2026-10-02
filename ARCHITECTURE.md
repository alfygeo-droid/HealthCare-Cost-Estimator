# Architecture

The local prototype uses a browser client (`index.html`, `app.js`, `styles.css`) and a Python REST server (`server.py`). The server reads supplied tariff CSVs, calculates deterministic estimates/insurance and evaluates explainable bill and cross-claim rules. API endpoints are `GET /api/procedures`, `POST /api/estimate`, `POST /api/insurance/calculate`, `POST /api/bills/analyze`, and `POST /api/claims/cross-check`.

The optional production-aligned upgrade is React + Vite frontend, Flask REST API, PostgreSQL/Supabase persistence, and a separately evaluated ML pipeline. Keep deterministic insurance math separate from any explanatory AI.
