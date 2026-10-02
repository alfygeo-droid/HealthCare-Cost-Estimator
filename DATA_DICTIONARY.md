# Data dictionary

## CGHS tariff files

`procedure_name` identifies the reference procedure; `non_nabh_rate`, `nabh_rate`, and `super_speciality_rate` give tariff variants; `city_tier`, `source`, and `source_date` provide traceability.

## Supporting supplied datasets

The Synthea-style `encounters`, `procedures`, `patients`, `organizations`, and `payers` files use encounter-linked identifiers. `Hospital_Operations_Dataset.csv` contains operational and treatment-cost fields. Validate currency/geography before using these for INR estimates.

## India hospital directory

`data/hospital_directory.csv` preserves the supplied 30,273-record directory. Fields used in the application include `Hospital_Name`, `State`, `District`, `Hospital_Category`, `Hospital_Care_Type`, `Specialties`, `Facilities`, and contact fields. The source has sparse accreditation, bed-count, and tariff-range values; those data are never invented. Derived service tiers use only the listed care type, specialty, and facility fields.

## Synthetic demo data

The generator produces `hospital_bills.csv` and `multi_claims.csv`, each with a `demo_label` column that identifies controlled scenarios.
