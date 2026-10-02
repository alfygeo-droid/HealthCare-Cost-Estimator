"""Create labelled synthetic demo records with controlled, explainable anomalies."""
from pathlib import Path
import csv, random
random.seed(42); OUT=Path(__file__).parents[1]/'demo_data'; OUT.mkdir(exist_ok=True)
claims=[
 ['CLM-001','DEMO-01','POL-A','HOSP-01','BILL-001','Knee replacement','2026-09-01',150000,150000,'approved','legitimate two-policy claim'],
 ['CLM-002','DEMO-01','POL-B','HOSP-01','BILL-001','Knee replacement','2026-09-02',50000,50000,'approved','legitimate two-policy claim'],
 ['CLM-003','DEMO-02','POL-A','HOSP-01','BILL-002','Cataract surgery','2026-09-03',80000,0,'review','duplicate invoice scenario'],
 ['CLM-004','DEMO-02','POL-B','HOSP-01','BILL-002','Cataract surgery','2026-09-04',80000,0,'review','duplicate invoice scenario'],
]
with (OUT/'multi_claims.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['claim_id','patient_id','policy_id','hospital_id','bill_id','procedure','claim_date','claimed_amount','approved_amount','status','demo_label']);w.writerows(claims)
with (OUT/'hospital_bills.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['bill_id','patient_id','hospital_id','procedure','item','category','quantity','unit_price','total_price','invoice_number','demo_label']);w.writerows([['BILL-001','DEMO-01','HOSP-01','Knee replacement','Room charge','Room',4,5500,22000,'INV-01','normal'],['BILL-002','DEMO-02','HOSP-01','Cataract surgery','Diagnostic test','Diagnostics',1,3000,3000,'INV-02','duplicate line follows'],['BILL-002','DEMO-02','HOSP-01','Cataract surgery','Diagnostic test','Diagnostics',1,3000,3000,'INV-02','duplicate line']])
print(f'Created labelled demo data in {OUT}')
