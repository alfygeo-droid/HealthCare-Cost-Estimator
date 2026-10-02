# CarePath — Pitch Note

## One-line pitch

CarePath is a healthcare financial decision-support platform for India that helps a patient estimate treatment costs, understand possible insurance coverage, scan and review hospital bills, and plan compliant insurance claims in one connected workflow.

## The problem

Patients often make treatment decisions without a clear view of three things: the likely hospital cost, what their insurance may cover, and whether the final bill or claim allocation needs further verification. Information is scattered between tariff documents, hospital bills, policy documents and insurer processes. This can result in unexpected out-of-pocket spending, confusing bills, and duplicate or excessive claim submissions.

## Our solution

CarePath turns that fragmented journey into a simple sequence:

1. **Estimate before treatment** — Select a procedure, city, hospital type, room type and expected stay.
2. **Understand possible coverage** — Add up to three policies and compare their available cover against the treatment estimate.
3. **Find hospitals** — Search the supplied India hospital directory by state, name and listed specialty.
4. **Scan the final bill** — Upload a PDF, image, CSV or text bill; CarePath extracts readable content and probable line items.
5. **Verify and explain** — Review extracted items, identify unusual patterns, and retain the scanned/verified result in bill history.
6. **Plan safer claims** — Allocate a verified invoice across policies without exceeding the bill, preserving policy and claim history locally.

## What makes it intelligent

CarePath uses a practical combination of AI-enabled extraction and transparent decision rules. This is deliberate: financial and insurance recommendations should be explainable, reviewable and safe.

### 1. Document intelligence and OCR

For uploaded hospital bills, CarePath accepts images, PDFs, CSV and text files. It uses local OCR for image-based documents and PDF text extraction for digital PDFs. The system then identifies likely bill line items, quantities, rates and amounts. The user is always asked to confirm or correct the extracted data before it is used for financial review.

**Why this matters:** it reduces manual entry while keeping the patient in control of sensitive financial information.

### 2. Structured bill reasoning

After confirmation, the bill engine applies explainable consistency checks, such as:

- duplicate line items at the same amount;
- unusually high quantities;
- unusually high unit prices;
- ICU days greater than the stated stay; and
- basic consistency between billed items and the stated treatment.

The output is a review priority, not a fraud accusation. CarePath explicitly frames anomalies as items requiring verification with the hospital or insurer.

### 3. Tariff-backed cost estimation

The estimator uses the supplied CGHS tariff catalogues across city tiers as a traceable baseline. It combines procedure tariff, city, hospital type, room type, expected stay, diagnostics, medicines and consumables to produce a planning range.

**Why this is stronger than a generic estimate:** every result can be traced back to a reference tariff and clearly stated assumptions. It is not presented as a hospital quotation.

### 4. Policy coverage and claim allocation strategy

Users can enter an insurance company and policy number. In the current prototype, policy cover, multi-claim support and optional criteria are retrieved through a labelled local demo lookup. The system can compare up to three policies and:

- select the policy with the highest available cover first;
- use additional eligible policies if the first does not cover the full invoice;
- account for policies that do not support multiple claims;
- cap allocations at the verified invoice value; and
- flag a situation where saved claims already meet or exceed the invoice total.

This is an **insurance decision-support strategy**, not an insurer approval engine. Final eligibility, exclusions, waiting periods, cashless availability and approval must be confirmed by the insurer.

### 5. Local histories and continuity

CarePath stores separate local histories for:

- scanned and verified bill records;
- estimate-coverage policies and planned claims; and
- Claim Safeguards policies and claim recommendations.

This separation is intentional: a patient can explore potential coverage during planning without mixing it with the post-bill claim safeguard workflow.

## Data used in the prototype

- Supplied CGHS tariff CSV files for procedure cost baselines across tiers.
- Supplied India hospital directory CSV for hospital search, location and listed-service filtering.
- User-uploaded hospital bill documents for OCR/extraction and review.
- Local demo policy lookup for coverage terms until verified insurer datasets or APIs are supplied.

## Important trust and safety design choices

- No result is described as a hospital quotation, insurer approval, or fraud verdict.
- OCR output is always reviewable and editable before use.
- Claim allocation is capped to the bill value to prevent over-allocation across insurers.
- Hospital service tiers are derived only from fields supplied in the directory; they are not quality ratings.
- Uploaded bill binaries are not retained in history; the local history keeps structured extracted/verified details and a short text preview.
- The current policy lookup is clearly labelled as demo-derived, not insurer-verified.

## Current prototype capabilities

| Area | What CarePath demonstrates |
| --- | --- |
| Cost estimator | 1,996 tariff procedures across 59 specialties, with city, hospital, room and stay assumptions |
| Hospital search | Search of the supplied India directory by state, hospital name and listed specialty |
| Insurance calculator | Transparent patient-share calculation using sum insured, deductible, co-pay, room excess and non-payables |
| Estimate coverage | Independent, pre-treatment comparison of up to three insurance policies against the estimated treatment amount |
| Bill intelligence | Upload, OCR/text extraction, editable line-item review, consistency checks and local bill history |
| Claim safeguards | Post-bill policy comparison, compliant multi-policy allocation, local policy/claim history and excess-claim flagging |
| 90-day exposure | P10, P50 and P90 post-discharge financial planning scenarios |

## Roadmap: moving from prototype to production

1. Connect verified insurer APIs or supplied policy datasets for real eligibility, sum insured, claim history and policy conditions.
2. Add secure authentication, consent flows, encryption and role-based access before handling real patient data.
3. Improve document extraction using domain-trained invoice models and confidence scores at field level.
4. Add hospital-specific package pricing and network-hospital information when trustworthy data is available.
5. Add human-insurer review workflows for exceptions, missing documents and pre-authorisation.
6. Validate cost and claim recommendations with hospitals, insurers and patient advocates.

## Suggested 45-second pitch

“CarePath helps patients understand the financial journey of treatment before they commit to it. Using traceable CGHS tariffs, it estimates procedure cost based on city, hospital and stay assumptions. Patients can add their insurance policies to see how much of that estimate may be covered. When the hospital bill arrives, they upload it; CarePath extracts line items, highlights values that need verification, and helps allocate the verified invoice across policies without exceeding the bill. The key difference is trust: the system explains every estimate, never claims approval or fraud detection, and keeps the user in control at every step. Today it runs on supplied tariff and hospital data with clearly labelled demo policy lookups; the next step is verified insurer integration.”
