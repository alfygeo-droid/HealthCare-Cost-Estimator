"""Create a derived hospital catalogue while preserving the supplied raw directory.

The derived tier is service scope, not a quality, accreditation, or pricing rating.
"""
from pathlib import Path
import csv, sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
from server import hospital_tier, text, usable

source = ROOT / 'data' / 'hospital_directory.csv'
target = ROOT / 'data' / 'hospital_catalog.csv'
with source.open(encoding='utf-8-sig', newline='') as src, target.open('w', encoding='utf-8', newline='') as out:
    fields = ['hospital_name','state','district','hospital_category','care_type','service_tier','specialties','telephone']
    writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader()
    for row in csv.DictReader(src):
        writer.writerow({'hospital_name':text(row.get('Hospital_Name')), 'state':text(row.get('State')), 'district':text(row.get('District')), 'hospital_category':text(row.get('Hospital_Category')) if usable(row.get('Hospital_Category')) else 'Not stated', 'care_type':text(row.get('Hospital_Care_Type')) if usable(row.get('Hospital_Care_Type')) else 'Not stated', 'service_tier':hospital_tier(row), 'specialties':text(row.get('Specialties')) if usable(row.get('Specialties')) else 'Not listed', 'telephone':text(row.get('Telephone')) if usable(row.get('Telephone')) else ''})
print(f'Created {target}')
