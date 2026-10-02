# Model card

## Current approach

The runnable demo uses transparent tariff-based estimation, not an ML cost model. The estimate combines a selected CGHS tariff with declared room and stay assumptions and a visible planning buffer.

## Limits

Tariffs are reference rates, historical/operational data may differ in country and currency, and no estimate is a guarantee. Future ML requires a labelled, representative INR final-cost dataset, holdout evaluation (MAE and R²), and documented feature lineage.
