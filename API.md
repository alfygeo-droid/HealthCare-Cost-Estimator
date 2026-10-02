# API

All successful routes return `{ "success": true, "data": ... }`.

`POST /api/estimate` accepts `procedure`, `tier`, `room`, and `stay`.

`POST /api/insurance/calculate` accepts `total`, `sum_insured`, `deductible`, `copay`, and `non_payable`.

`POST /api/bills/analyze` accepts `{ "items": [{ "name", "quantity", "unit_price", "total" }] }`.

`POST /api/claims/cross-check` accepts `bill_total` and `claims` with `policy`, `invoice`, and `amount`.
