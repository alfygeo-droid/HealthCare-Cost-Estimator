"""Local API for the Healthcare Cost Estimator demo.

Uses only the Python standard library so the demo works without a package install.
Run: python server.py   then visit http://127.0.0.1:8000
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import base64, csv, json, math, io, re
from datetime import datetime

ROOT = Path(__file__).parent
POLICY_STORE = ROOT / 'data' / 'policy_history.json'
ESTIMATE_POLICY_STORE = ROOT / 'data' / 'estimate_policy_history.json'
BILL_HISTORY_STORE = ROOT / 'data' / 'bill_history.json'
PATIENT_PROFILE_STORE = ROOT / 'data' / 'patient_profiles.json'
POLICY_SCHEMA_FILE = ROOT / 'CareCost_AI' / 'health_insurance_with_policy_product_and_company.csv'
CEP_HOSPITAL_FILE = ROOT / 'data' / 'external' / 'cep_empanelled_hospitals.csv'

def money(value): return int(round(float(value)))
def read_tariffs(tier):
    path = ROOT / f"tariffs_tier{tier}.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

TARIFFS = {str(i): read_tariffs(i) for i in (1, 2, 3)}
POLICY_SCHEMAS = []
if POLICY_SCHEMA_FILE.exists():
    with POLICY_SCHEMA_FILE.open(encoding='utf-8-sig', newline='') as f:
        POLICY_SCHEMAS = list(csv.DictReader(f))

def policy_schema_catalog():
    return [{
        'id': text(row.get('Policy_ID')),
        'company': text(row.get('Company')),
        'schema': text(row.get('Policy_Product')),
        'max_claimable': money(row.get('Coverage_Amount') or 0),
        'premium': money(row.get('Annual_Premium') or 0),
        'claim_settlement_ratio': text(row.get('Claim_Settlement_Ratio (%)')),
        'cashless': text(row.get('Cashless_Available')),
        'pre_existing': text(row.get('Pre_Existing_Disease_Cover')),
        'entry_age': f"{text(row.get('Min_Entry_Age'))}–{text(row.get('Max_Entry_Age'))} years",
    } for row in POLICY_SCHEMAS]

HOSPITAL_FILE = ROOT / 'data' / 'hospital_directory.csv'

def text(value):
    return (value or '').strip()

def usable(value):
    return bool(text(value) and text(value) != '0')

def hospital_tier(row):
    """Classify service scope only from fields present in the source directory."""
    if usable(row.get('Hospital_Tier')): return text(row.get('Hospital_Tier'))
    care = text(row.get('Hospital_Care_Type')).lower()
    category = text(row.get('Hospital_Category'))
    specialty = text(row.get('Specialties'))
    facilities = text(row.get('Facilities'))
    if 'medical college' in care or ('hospital' in care and (usable(specialty) or usable(facilities))):
        return 'Tier A: Hospital with listed services'
    if 'hospital' in care or 'nursing home' in care:
        return 'Tier B: Hospital / nursing facility'
    if category in ('Private', 'Public/ Government') or care not in ('', '0'):
        return 'Tier C: Listed care facility'
    return 'Unclassified: Limited source detail'

def hospital_records():
    if not HOSPITAL_FILE.exists(): return []
    with HOSPITAL_FILE.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

HOSPITALS = hospital_records()
if CEP_HOSPITAL_FILE.exists():
    with CEP_HOSPITAL_FILE.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            specialties = ', '.join(name for name in ('Cardiology','Oncology','Ophthalmology','Maternal_Health_OBGY','Neonatology') if text(row.get(name)).lower() == 'yes')
            HOSPITALS.append({'Hospital_Name':text(row.get('Hospital_Name')), 'State':text(row.get('State')), 'District':text(row.get('City_cleaned') or row.get('City_as_entered')), 'Hospital_Category':'Empanelled', 'Hospital_Care_Type':'Empanelled hospital', 'Specialties':specialties or 'Not listed', 'Facilities':'', 'Telephone':'', 'Hospital_Tier':text(row.get('Tier')), 'Source':'CEP empanelled hospital dashboard'})

PATIENT_FILE = ROOT / 'patients.csv'
ENCOUNTER_FILE = ROOT / 'encounters.csv'
PAYER_FILE = ROOT / 'payers.csv'
ORGANIZATION_FILE = ROOT / 'organizations.csv'

def patient_profile(sign_id=''):
    """Return one source-backed patient profile for the local demo workspace."""
    saved = next((p for p in load_patient_profiles() if p.get('sign_id') == text(sign_id)), None) if text(sign_id) else None
    if saved:
        return {'source':'saved patient profile','patient':{'id':saved.get('sign_id'),'name':saved.get('name'),'phone':saved.get('phone'),'age':saved.get('age'),'gender':saved.get('gender'),'birthdate':'Not provided','location':'Not provided'},'policies':[{'name':saved.get('policy_company'),'schema':saved.get('policy_schema'),'member_id':saved.get('sign_id'),'phone':'Not provided','max_claimable':saved.get('max_claimable'),'status':'Saved profile'}],'care_summary':{'encounters':0,'latest_type':'Not provided','latest_description':'Not provided','latest_facility':'Not provided','latest_date':'Not provided'},'claim_amount':saved.get('claim_amount'),'duration':saved.get('duration')}
    patients = list(csv.DictReader(PATIENT_FILE.open(encoding='utf-8-sig', newline=''))) if PATIENT_FILE.exists() else []
    encounters = list(csv.DictReader(ENCOUNTER_FILE.open(encoding='utf-8-sig', newline=''))) if ENCOUNTER_FILE.exists() else []
    payers = {row.get('Id'): row for row in csv.DictReader(PAYER_FILE.open(encoding='utf-8-sig', newline=''))} if PAYER_FILE.exists() else {}
    organizations = {row.get('Id'): row for row in csv.DictReader(ORGANIZATION_FILE.open(encoding='utf-8-sig', newline=''))} if ORGANIZATION_FILE.exists() else {}
    encounter_by_patient = {}
    for row in encounters:
        encounter_by_patient.setdefault(row.get('PATIENT'), []).append(row)
    patient = next((row for row in patients if row.get('Id') in encounter_by_patient), patients[0] if patients else {})
    patient_encounters = encounter_by_patient.get(patient.get('Id'), [])
    latest = patient_encounters[-1] if patient_encounters else {}
    payer = payers.get(latest.get('PAYER'), {})
    organization = organizations.get(latest.get('ORGANIZATION'), {})
    schema = policy_schema_catalog()[0] if POLICY_SCHEMAS else {}
    birthdate = patient.get('BIRTHDATE', '')
    try:
        born = datetime.strptime(birthdate, '%Y-%m-%d').date()
        today = datetime.now().date()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        age = None
    return {
        'source': 'patients.csv, encounters.csv, payers.csv and organizations.csv',
        'patient': {
            'id': patient.get('Id', ''),
            'name': ' '.join(x for x in [patient.get('PREFIX'), patient.get('FIRST'), patient.get('LAST'), patient.get('SUFFIX')] if text(x)),
            'phone': 'Not provided in patients.csv',
            'age': age,
            'gender': patient.get('GENDER') or 'Not stated',
            'birthdate': birthdate or 'Not stated',
            'location': ', '.join(x for x in [patient.get('CITY'), patient.get('STATE'), patient.get('ZIP')] if text(x)),
        },
        'policies': [{
            'name': schema.get('company') or payer.get('NAME') or 'Not stated',
            'schema': schema.get('schema') or 'Not provided',
            'member_id': payer.get('Id') or 'Not stated',
            'phone': payer.get('PHONE') or 'Not provided',
            'max_claimable': schema.get('max_claimable') or 0,
            'status': 'Source record',
        }],
        'care_summary': {
            'encounters': len(patient_encounters),
            'latest_type': latest.get('ENCOUNTERCLASS') or 'Not stated',
            'latest_description': latest.get('DESCRIPTION') or 'Not stated',
            'latest_facility': organization.get('NAME') or 'Not stated',
            'latest_date': (latest.get('START') or '')[:10] or 'Not stated',
        },
    }

def load_patient_profiles():
    if not PATIENT_PROFILE_STORE.exists(): return []
    try: return json.loads(PATIENT_PROFILE_STORE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError): return []

def save_patient_profiles(profiles):
    PATIENT_PROFILE_STORE.parent.mkdir(exist_ok=True)
    PATIENT_PROFILE_STORE.write_text(json.dumps(profiles, indent=2), encoding='utf-8')

def patient_login(payload):
    sign_id=text(payload.get('sign_id')); password=text(payload.get('password'))
    if sign_id == 'carecost-patient' and password == 'PatientCare!2026': return {'sign_id': sign_id, 'name': 'CarePath demo patient'}
    for profile in load_patient_profiles():
        if profile.get('sign_id') == sign_id and profile.get('password') == password:
            return {'sign_id': sign_id, 'name': profile.get('name', sign_id)}
    raise ValueError('Invalid patient credentials.')

def save_patient_profile(payload):
    required = ['sign_id', 'password', 'name', 'age', 'gender', 'policy_schema', 'claim_amount']
    if any(not text(payload.get(field)) for field in required if field != 'age'): raise ValueError('Complete the profile, credentials, policy schema and claim amount.')
    try:
        age = int(text(payload.get('age')))
    except (TypeError, ValueError):
        raise ValueError('Age must be a whole number from 1 to 150.')
    if not 1 <= age <= 150: raise ValueError('Age must be between 1 and 150.')
    profiles=load_patient_profiles()
    if any(p.get('sign_id','').lower()==text(payload.get('sign_id')).lower() for p in profiles): raise ValueError('That Sign ID is already saved.')
    schema=next((x for x in policy_schema_catalog() if x['schema']==text(payload.get('policy_schema'))), None)
    if not schema: raise ValueError('Choose a policy schema from the supplied policy dataset.')
    profile={
        'sign_id': text(payload.get('sign_id')), 'password': text(payload.get('password')), 'name': text(payload.get('name')),
        'phone': text(payload.get('phone')) or 'Not provided', 'age': age, 'gender': text(payload.get('gender')),
        'policy_schema': schema['schema'], 'policy_company': schema['company'], 'max_claimable': schema['max_claimable'],
        'claim_amount': money(payload.get('claim_amount')), 'duration': text(payload.get('duration')) or 'Not provided',
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    profiles.append(profile); save_patient_profiles(profiles)
    return {'profile': {k:v for k,v in profile.items() if k != 'password'}, 'count': len(profiles)}

def public_hospital(row):
    return {
        'name': text(row.get('Hospital_Name')),
        'state': text(row.get('State')),
        'district': text(row.get('District')),
        'category': text(row.get('Hospital_Category')) if usable(row.get('Hospital_Category')) else 'Not stated',
        'care_type': text(row.get('Hospital_Care_Type')) if usable(row.get('Hospital_Care_Type')) else 'Not stated',
        'specialties': text(row.get('Specialties')) if usable(row.get('Specialties')) else 'Not listed',
        'tier': hospital_tier(row),
        'telephone': text(row.get('Telephone')) if usable(row.get('Telephone')) else '',
        'source': text(row.get('Source')) or 'India hospital directory',
    }

def find_tariff(query, tier):
    q = (query or "").lower().strip()
    rows = TARIFFS.get(str(tier), TARIFFS['1'])
    matches = [r for r in rows if q in r['procedure_name'].lower()]
    if not matches:
        # Prefer a known meaningful result instead of claiming a non-existent tariff.
        matches = [r for r in rows if 'cataract' in r['procedure_name'].lower()] or rows[:1]
    return max(matches, key=lambda r: float(r.get('super_speciality_rate') or r.get('nabh_rate') or 0))

def estimate(payload):
    city = payload.get('city', 'Delhi')
    city_tiers = {'Delhi':'1','Mumbai':'1','Bengaluru':'1','Chennai':'1','Hyderabad':'1','Kolkata':'1','Pune':'1','Ahmedabad':'1','Kochi':'2','Jaipur':'2','Lucknow':'2','Chandigarh':'2','Coimbatore':'2','Thiruvananthapuram':'2','Mysuru':'3','Kozhikode':'3','Indore':'3','Bhopal':'3','Visakhapatnam':'3','Other city':'3'}
    tier = city_tiers.get(city, '3')
    stay = max(1, int(payload.get('stay', 3)))
    room = payload.get('room', 'Private')
    hospital_type = payload.get('hospital_type', 'Private hospital')
    tariff = find_tariff(payload.get('procedure'), tier)
    base = float(tariff.get('super_speciality_rate') or tariff.get('nabh_rate') or 0)
    room_daily = {'General': 1600, 'Semi-private': 3000, 'Private': 5500, 'Suite': 9500}.get(room, 5500)
    tier_factor = {'1': 1.18, '2': 1.08, '3': 1.0}[tier]
    type_factor = {'Government hospital':.88, 'Private hospital':1.0, 'Super-speciality hospital':1.18, 'Trust / charitable hospital':.93}.get(hospital_type, 1.0)
    procedure_cost = base * tier_factor * type_factor
    room_cost = room_daily * stay
    diagnostics = max(2500, procedure_cost * .08)
    medicines = max(1800, procedure_cost * .07)
    consumables = max(1200, procedure_cost * .05)
    midpoint = money(procedure_cost + room_cost + diagnostics + medicines + consumables)
    spread = .13
    return {
      'procedure': tariff['procedure_name'], 'tariff': money(base), 'midpoint': midpoint,
      'low': money(midpoint*(1-spread)), 'high': money(midpoint*(1+spread)),
      'breakdown': [{'name':'Procedure', 'value':money(procedure_cost)}, {'name':'Room & stay', 'value':money(room_cost)}, {'name':'Diagnostics', 'value':money(diagnostics)}, {'name':'Medicines', 'value':money(medicines)}, {'name':'Consumables', 'value':money(consumables)}],
      'source': tariff['source'], 'source_date': tariff['source_date'], 'tier': tariff['city_tier'],
      'assumptions': [f'{city} maps to CGHS {tariff["city_tier"]}', f'{hospital_type}; {room} room for {stay} day(s)', 'CGHS reference tariff is used as a baseline', 'Range reflects a transparent 13% planning buffer'],
      'confidence': 'Medium — tariff-backed baseline; not a hospital quotation.'
    }

def insurance(payload):
    total = float(payload.get('total', 210000)); insured = float(payload.get('sum_insured', 500000))
    deductible = float(payload.get('deductible', 0)); copay = float(payload.get('copay', 10))/100
    nonpay = float(payload.get('non_payable', 12000)); room_excess = float(payload.get('room_excess', 0))
    eligible = max(0, total - nonpay - room_excess)
    after_deductible = max(0, eligible - deductible)
    contribution = min(insured, after_deductible * (1-copay))
    patient = total - contribution
    return {'estimated_cost':money(total), 'eligible':money(eligible), 'contribution':money(contribution), 'patient_share':money(patient), 'lines':[{'label':'Estimated hospital cost','value':money(total)},{'label':'Less non-payable expenses','value':-money(nonpay)},{'label':'Eligible expense','value':money(eligible)},{'label':'Less deductible','value':-money(deductible)},{'label':f'Co-pay ({copay*100:.0f}%)','value':-money(after_deductible*copay)},{'label':'Insurance contribution','value':money(contribution)}]}

def analyze_bill(payload):
    items = payload.get('items') or []
    procedure = payload.get('procedure') or 'Not stated on bill'
    try: stated_stay = max(1, int(payload.get('stay') or 4))
    except (TypeError, ValueError): stated_stay = 4
    total = sum(float(i.get('total',0)) for i in items)
    flags=[]; seen={}; consistent=[]
    for item in items:
        name=item.get('name','Item').strip().lower(); key=(name, str(item.get('total', '')))
        if key in seen: flags.append({'level':'Review', 'title':'Potential duplicate charge', 'detail':f"{item.get('name')} appears more than once at the same amount. Verify with the billing desk."})
        seen[key]=1
        qty=float(item.get('quantity',1)); unit=float(item.get('unit_price',0))
        if qty > 25: flags.append({'level':'Review', 'title':'Unusual quantity', 'detail':f"{item.get('name')} has quantity {qty:g}. Check the clinical and billing record."})
        if unit > 15000: flags.append({'level':'Review', 'title':'High line-item price', 'detail':f"{item.get('name')} is ₹{money(unit):,} per unit. Compare this against the hospital's rate card."})
        if 'icu' in name and qty > stated_stay:
            flags.append({'level':'Review', 'title':'Treatment-bill consistency check', 'detail':f"ICU stay is billed for {qty:g} day(s), while the stated stay is {stated_stay} day(s). Verify the discharge summary and bill."})
        if any(term in name for term in ('implant', 'surgeon', 'room', 'medicine', 'diagnostic')) and not (('icu' in name) and qty > stated_stay):
            consistent.append(item.get('name'))
    risk = 'HIGH' if len(flags)>=3 else 'MEDIUM' if flags else 'LOW'
    return {'total':money(total), 'flags':flags, 'risk':risk, 'consistent_items':consistent, 'procedure':procedure, 'stated_stay':stated_stay, 'message':'Potential anomalies identify items for verification; they do not establish fraud.'}

def load_policy_store(path=POLICY_STORE):
    if path.exists():
        try:
            store=json.loads(path.read_text(encoding='utf-8'))
            store.setdefault('policies',[]); store.setdefault('claims',[])
            store.setdefault('policy_history',[dict(p) for p in store['policies']])
            return store
        except json.JSONDecodeError: pass
    return {'policies':[],'claims':[],'policy_history':[]}

def save_policy_store(store, path=POLICY_STORE):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(store,indent=2),encoding='utf-8')

def lookup_policy(payload, path=POLICY_STORE):
    """Deterministic local stand-in for an insurer eligibility lookup."""
    number=text(payload.get('policy_number')); company=text(payload.get('company'))
    if not number or not company: raise ValueError('Enter both policy number and insurance company.')
    existing=next((p for p in load_policy_store(path)['policies'] if p['policy_number'].lower()==number.lower() and p['company'].lower()==company.lower()),None)
    if existing: return {**existing,'lookup_source':'Saved local policy record'}
    schema=next((x for x in policy_schema_catalog() if x['schema'].lower()==number.lower()), None)
    if schema:
        return {'policy_number':schema['id'] or number,'schema':schema['schema'],'company':schema['company'],'sum_insured':schema['max_claimable'],'remaining_cover':schema['max_claimable'],'max_claimable':schema['max_claimable'],'supports_multiple_claims':True,'criteria':f"Cashless: {schema['cashless']} · Pre-existing disease cover: {schema['pre_existing']} · Entry age: {schema['entry_age']}",'lookup_source':'CareCost AI policy schema dataset'}
    seed=sum(ord(ch) for ch in (company+number).lower())
    cover=(seed % 5 + 2)*100000
    multi=seed % 3 != 0
    return {'policy_number':number,'schema':number,'company':company,'sum_insured':cover,'remaining_cover':cover,'max_claimable':cover,'supports_multiple_claims':multi,'criteria':'Cashless/network eligibility, waiting periods and exclusions must be confirmed with the insurer.' if seed%2 else 'No policy criteria supplied in this demo lookup. Confirm exclusions and pre-authorisation with the insurer.','lookup_source':'Local demo lookup — not insurer-verified'}

def save_policy(payload, path=POLICY_STORE):
    number=text(payload.get('policy_number'))
    company=text(payload.get('company'))
    if not number or not company: raise ValueError('Enter both policy number and insurance company.')
    store=load_policy_store(path); policies=store['policies']
    existing=next((p for p in policies if p['policy_number'].lower()==number.lower()),None)
    policy={'policy_number':number,'schema':text(payload.get('schema')) or number,'company':company,'sum_insured':max(0,money(payload.get('sum_insured',0))),'remaining_cover':max(0,money(payload.get('remaining_cover',payload.get('sum_insured',0)))),'max_claimable':max(0,money(payload.get('max_claimable',payload.get('sum_insured',0)))),'supports_multiple_claims':bool(payload.get('supports_multiple_claims',True)),'criteria':text(payload.get('criteria')),'lookup_source':text(payload.get('lookup_source')) or 'Saved local policy record'}
    if existing: existing.update(policy)
    else: policies.append(policy)
    history_entry={**policy,'saved_at':datetime.now().strftime('%d %b %Y, %I:%M %p')}
    store.setdefault('policy_history',[]).insert(0,history_entry)
    save_policy_store(store, path)
    return {'policies':policies,'claims':store['claims'],'policy_history':store['policy_history']}

def recommend_claims(payload, path=POLICY_STORE):
    invoice=text(payload.get('invoice')) or 'Uploaded invoice'
    bill=max(0,money(payload.get('bill_total',0)))
    if not bill: raise ValueError('Verify a bill total before generating claim recommendations.')
    store=load_policy_store(path)
    already_claimed=sum(money(c.get('claimed_amount',0)) for c in store['claims'] if c.get('invoice')==invoice)
    if already_claimed >= bill:
        return {'invoice':invoice,'bill_total':bill,'allocations':[],'remaining':max(0,bill-already_claimed),'claimed_total':already_claimed,'status':'REQUIRES VERIFICATION','notes':['Saved claims for this invoice already meet or exceed the bill total. Multiple insurance claims cannot be approved above the invoice amount.']}
    remaining=bill-already_claimed; allocations=[]; notes=[]
    policies=sorted(store['policies'],key=lambda p:p['remaining_cover'],reverse=True)
    for policy in policies:
        if remaining <= 0: break
        if not policy['supports_multiple_claims'] and allocations:
            notes.append(f"{policy['company']} has a single-claim profile, so it is not used after another policy. Choose it first, or use a policy that supports multiple claims for the remaining amount.")
            continue
        amount=min(remaining,policy['remaining_cover'])
        if amount:
            allocations.append({'policy_number':policy['policy_number'],'company':policy['company'],'amount':amount})
            remaining-=amount
    total=sum(x['amount'] for x in allocations)
    primary=next((p for p in store['policies'] if allocations and p['policy_number']==allocations[0]['policy_number']), {})
    if allocations and not primary.get('supports_multiple_claims', True) and len(allocations)>1:
        notes.insert(0, 'A single-claim policy is included first; the remaining amount is allocated only to policies that support multiple claims.')
    return {'invoice':invoice,'bill_total':bill,'allocations':allocations,'remaining':remaining,'claimed_total':already_claimed+total,'status':'REQUIRES VERIFICATION' if already_claimed+total>bill else 'RECOMMENDED ALLOCATION','notes':notes or ['Allocation is capped at the verified invoice total. Claims above that amount are not eligible for approval. Confirm policy terms and insurer approval.']}

def save_claims(payload, path=POLICY_STORE):
    result=recommend_claims(payload, path)
    total=sum(x['amount'] for x in result['allocations'])
    if total > result['bill_total']: raise ValueError('Claim amount exceeds the bill amount. Multiple insurance claims cannot be approved for the excess amount.')
    store=load_policy_store(path)
    for item in result['allocations']:
        store['claims'].append({'policy_number':item['policy_number'],'company':item['company'],'invoice':result['invoice'],'claimed_amount':item['amount'],'status':'recommended'})
        policy=next(p for p in store['policies'] if p['policy_number']==item['policy_number']); policy['remaining_cover']=max(0,policy['remaining_cover']-item['amount'])
    save_policy_store(store, path)
    return {**result,'saved':True}

def estimate_policy_lookup(payload): return lookup_policy(payload, ESTIMATE_POLICY_STORE)
def estimate_policy_save(payload): return save_policy(payload, ESTIMATE_POLICY_STORE)
def estimate_policy_recommend(payload): return recommend_claims(payload, ESTIMATE_POLICY_STORE)
def estimate_policy_claims(payload): return save_claims(payload, ESTIMATE_POLICY_STORE)

def cross_check(payload):
    claims=payload.get('claims') or []; bill=float(payload.get('bill_total',200000)); claimed=sum(float(c.get('amount',0)) for c in claims)
    invoices={}; flags=[]
    for c in claims:
        invoice=c.get('invoice','').strip()
        if invoice and invoice in invoices: flags.append('The same invoice number appears in multiple claims. Verify allocation across policies.')
        invoices[invoice]=1
    if claimed > bill: flags.append('Combined claimed amount is greater than the stated hospital bill.')
    priority = 'HIGH' if len(flags) > 1 else 'MEDIUM' if flags else 'LOW'
    return {'bill_total':money(bill),'claimed_total':money(claimed),'remaining':money(max(0,bill-claimed)),'status':'REQUIRES VERIFICATION' if flags else 'CONSISTENT','priority':priority,'flags':flags or ['Combined claims do not exceed the bill and no duplicate invoice was supplied.'], 'review_note':'A human reviewer makes the approval, document-request, or escalation decision.'}

def scan_bill(payload):
    """Turn user-provided CSV/text bill content into reviewable structured line items.
    Image/PDF OCR deliberately remains a configured capability rather than a guessed result.
    """
    content = str(payload.get('content','')).strip()
    filename = str(payload.get('filename','bill')).lower()
    if not content: return {'items':[], 'confidence':'No extractable text', 'message':'No text was supplied for scanning.'}
    items=[]
    if filename.endswith('.csv'):
        for row in csv.DictReader(io.StringIO(content)):
            normal={str(k).strip().lower().replace(' ','_'):str(v).strip() for k,v in row.items() if k}
            name=normal.get('item') or normal.get('item_name') or normal.get('description') or normal.get('service')
            quantity=normal.get('quantity') or normal.get('qty') or '1'
            unit=normal.get('unit_price') or normal.get('rate') or normal.get('price')
            total=normal.get('total') or normal.get('total_price') or normal.get('amount')
            if name and (unit or total):
                q=float(re.sub(r'[^0-9.]','',quantity) or 1); u=float(re.sub(r'[^0-9.]','',unit or '0') or 0); t=float(re.sub(r'[^0-9.]','',total or '0') or 0)
                if not t: t=q*u
                if not u and q: u=t/q
                items.append({'name':name,'quantity':q,'unit_price':u,'total':t})
        confidence='High — structured CSV fields matched.'
    else:
        # Prefer the compact provisional-bill table. Unlike a generic OCR sweep, it
        # excludes registration numbers, contact numbers, dates and addresses.
        lines=[line.strip() for line in content.splitlines() if line.strip()]
        start=next((i for i,line in enumerate(lines) if 'provisional' in line.lower() and 'bill' in line.lower()), -1)
        end=next((i for i,line in enumerate(lines[start+1:],start+1) if 'detailed' in line.lower() and 'break' in line.lower()), len(lines))
        summary=lines[start+1:end] if start >= 0 else []
        money_re=re.compile(r'^\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d{1,2}))?\s*$')
        code_re=re.compile(r'^\d{5,8}$')
        skip_words=('total bill','amount payable','amount paid','balance','primary code','particular','amount')
        i=0
        while i < len(summary):
            if code_re.match(summary[i]) and i+2 < len(summary):
                label=summary[i+1]
                match=money_re.match(summary[i+2].replace('₹','').replace('Rs.','').strip())
                if match and not any(word in label.lower() for word in skip_words):
                    amount=float(match.group(1).replace(',','')+'.'+(match.group(2) or '0'))
                    if 0 < amount <= 10_000_000:
                        items.append({'name':label[:120],'quantity':1,'unit_price':amount,'total':amount})
                        i += 3; continue
            i += 1
        if items:
            confidence='High — provisional-bill table rows were extracted; IDs, dates and contact fields were excluded.'
        else:
            # Conservative fallback: accept only explicitly billed healthcare labels.
            bill_terms=('charge','charges','fee','fees','bed','room','nursing','medicine','drug','test','scan','procedure','surgery','consult')
            for line in lines:
                normalized=line.lower()
                match=re.search(r'(?:₹|rs\.?\s*)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$',line,re.I)
                label=line[:match.start()].strip(' :-\t') if match else ''
                if match and label and any(term in normalized for term in bill_terms) and not any(term in normalized for term in ('phone','contact','address','date','registration','reg.no')):
                    amount=float(match.group(1).replace(',',''))
                    if 0 < amount <= 10_000_000: items.append({'name':label[:120],'quantity':1,'unit_price':amount,'total':amount})
            confidence='Low — only conservative healthcare charge lines were matched. Confirm each item.'
    lower=content.lower()
    procedure=''
    matches=[row['procedure_name'] for row in TARIFFS['1'] if len(row['procedure_name']) > 8 and row['procedure_name'].lower() in lower]
    if matches: procedure=max(matches, key=len)
    stay_match=re.search(r'(?:length\s*of\s*stay|hospital\s*stay|stay|days?)\D{0,14}(\d{1,2})\s*(?:day|days)', lower)
    stay=int(stay_match.group(1)) if stay_match else None
    return {'items':items[:100], 'confidence':confidence, 'procedure':procedure, 'stay':stay, 'message':f'Found {len(items)} possible bill line item(s). Review the extracted values before analysing.'}

def ocr_image_bytes(data):
    try:
        import cv2, numpy as np
        from rapidocr_onnxruntime import RapidOCR
        image=cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError('The image could not be decoded.')
        result, _ = RapidOCR()(image)
        return '\n'.join(str(line[1]) for line in (result or []) if len(line) > 1)
    except Exception as error:
        raise ValueError(f'OCR could not read this image: {error}')

def scan_uploaded_bill(payload):
    filename=str(payload.get('filename','hospital-bill')).lower()
    raw=str(payload.get('data',''))
    if not raw: raise ValueError('No upload data was received.')
    if ',' in raw and raw.startswith('data:'): raw=raw.split(',',1)[1]
    data=base64.b64decode(raw)
    if len(data) > 12*1024*1024: raise ValueError('Use a bill file under 12 MB.')
    source=''
    if filename.endswith(('.csv','.txt')):
        source=data.decode('utf-8-sig',errors='replace')
    elif filename.endswith('.pdf'):
        try:
            import fitz
            pdf=fitz.open(stream=data,filetype='pdf')
            source='\n'.join(page.get_text() for page in pdf)
            if len(source.strip()) < 30:
                images=[]
                for page in pdf[:5]:
                    pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                    images.append(ocr_image_bytes(pix.tobytes('png')))
                source='\n'.join(images)
        except Exception as error: raise ValueError(f'PDF extraction failed: {error}')
    elif filename.endswith(('.png','.jpg','.jpeg','.webp','.bmp','.tiff')):
        source=ocr_image_bytes(data)
    else: raise ValueError('Upload a PDF, image, CSV, or text bill.')
    result=scan_bill({'filename':filename if filename.endswith('.csv') else 'bill.txt','content':source})
    result['extracted_text_preview']=source[:1000]
    result['message']=f"{result['message']} Extracted from {filename}; verify every value against the original bill."
    return result

def load_bill_history():
    if BILL_HISTORY_STORE.exists():
        try: return json.loads(BILL_HISTORY_STORE.read_text(encoding='utf-8'))
        except json.JSONDecodeError: pass
    return []

def save_bill_history(payload):
    history=load_bill_history(); record_id=text(payload.get('id'))
    record={'id':record_id or str(int(datetime.now().timestamp()*1000)),'filename':text(payload.get('filename')) or 'Hospital bill','procedure':text(payload.get('procedure')) or 'Not stated','stay':payload.get('stay') or 'Not stated','items':payload.get('items') or [],'text_preview':text(payload.get('text_preview'))[:1000],'total':money(payload.get('total',0)),'risk':text(payload.get('risk')) or 'Extracted — awaiting verification','saved_at':datetime.now().strftime('%d %b %Y, %I:%M %p')}
    index=next((i for i,x in enumerate(history) if x.get('id')==record['id']),None)
    if index is None: history.insert(0,record)
    else: history[index]={**history[index],**record}
    BILL_HISTORY_STORE.parent.mkdir(exist_ok=True); BILL_HISTORY_STORE.write_text(json.dumps(history,indent=2),encoding='utf-8')
    return {'record':record,'history':history}

def clear_policy_history(payload=None, path=POLICY_STORE):
    store=load_policy_store(path); store['claims']=[]; store['policy_history']=[]
    save_policy_store(store,path)
    return store

def reset_active_policies(payload=None, path=POLICY_STORE):
    store=load_policy_store(path); store['policies']=[]
    save_policy_store(store,path)
    return store

def clear_bill_history(payload=None):
    BILL_HISTORY_STORE.parent.mkdir(exist_ok=True); BILL_HISTORY_STORE.write_text('[]',encoding='utf-8')
    return {'history':[]}

def clear_estimate_policy_history(payload=None): return clear_policy_history(path=ESTIMATE_POLICY_STORE)
def reset_active_estimate_policies(payload=None): return reset_active_policies(path=ESTIMATE_POLICY_STORE)

def exposure(payload):
    base=float(payload.get('base_cost', 15000)); visits=max(0,int(payload.get('followups',2))); medicine=float(payload.get('medicines',5000)); therapy=float(payload.get('therapy',5000));
    midpoint=money(base + visits*750 + medicine + therapy)
    return {'p10':money(midpoint*.55),'p50':midpoint,'p90':money(midpoint*1.8),'assumptions':[f'{visits} planned follow-up visit(s)', 'User-entered medicines and therapy budgets', 'Scenarios are financial planning ranges, not clinical predictions']}

class Handler(SimpleHTTPRequestHandler):
    def _json(self, payload, status=200):
        body={'success':status < 400,'data':payload} if status < 400 else {'success':False,'error':payload.get('error','Request failed')}
        raw=json.dumps(body, ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path == '/api/policy-schemas': return self._json(policy_schema_catalog())
        if path == '/api/patient-profile': return self._json(patient_profile(parse_qs(urlparse(self.path).query).get('sign_id', [''])[0]))
        if path == '/api/procedures':
            values=[]; seen=set()
            for row in TARIFFS['1']:
                n=row['procedure_name']
                if n not in seen:
                    values.append({'name':n, 'speciality':text(row.get('speciality'))})
                    seen.add(n)
            return self._json(values)
        if path == '/api/procedure-categories':
            categories=sorted({text(row.get('speciality')) for row in TARIFFS['1'] if usable(row.get('speciality'))})
            return self._json(categories)
        if path == '/api/hospitals':
            query = parse_qs(urlparse(self.path).query)
            term = query.get('q', [''])[0].lower().strip()
            state = query.get('state', [''])[0].lower().strip()
            procedure = query.get('procedure', [''])[0].lower().strip()
            matches=[]
            for row in HOSPITALS:
                name=text(row.get('Hospital_Name'))
                if not name: continue
                blob=' '.join([name, text(row.get('State')), text(row.get('District')), text(row.get('Specialties')), text(row.get('Hospital_Care_Type'))]).lower()
                if term and term not in blob: continue
                if state and state != text(row.get('State')).lower(): continue
                if procedure and procedure not in blob and not any(word in blob for word in procedure.split() if len(word)>4): continue
                matches.append(public_hospital(row))
                if len(matches) == 100: break
            states=sorted({text(r.get('State')) for r in HOSPITALS if usable(r.get('State'))})
            return self._json({'records':matches,'states':states,'total_directory_records':len(HOSPITALS), 'tier_note':'Service tiers are derived from listed care type, specialty, and facility fields. They are not quality ratings.'})
        if path == '/api/health': return self._json({'status':'ok','tariff_rows':sum(map(len,TARIFFS.values())), 'hospital_records':len(HOSPITALS)})
        if path == '/api/policies': return self._json(load_policy_store())
        if path == '/api/estimate-policies': return self._json(load_policy_store(ESTIMATE_POLICY_STORE))
        if path == '/api/bills/history': return self._json({'history':load_bill_history()})
        return super().do_GET()
    def do_POST(self):
        try: payload=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0)) or 0) or '{}')
        except json.JSONDecodeError: return self._json({'error':'Invalid JSON'},400)
        path=urlparse(self.path).path
        routes={'/api/auth/patient-login':patient_login,'/api/patient-profiles':save_patient_profile,'/api/estimate':estimate,'/api/insurance/calculate':insurance,'/api/bills/analyze':analyze_bill,'/api/bills/scan':scan_bill,'/api/bills/scan-upload':scan_uploaded_bill,'/api/bills/history/save':save_bill_history,'/api/bills/history/clear':clear_bill_history,'/api/policies/lookup':lookup_policy,'/api/policies/save':save_policy,'/api/policies/clear':clear_policy_history,'/api/policies/reset-active':reset_active_policies,'/api/claims/recommend':recommend_claims,'/api/claims/save':save_claims,'/api/estimate-policies/lookup':estimate_policy_lookup,'/api/estimate-policies/save':estimate_policy_save,'/api/estimate-policies/clear':clear_estimate_policy_history,'/api/estimate-policies/reset-active':reset_active_estimate_policies,'/api/estimate-policies/recommend':estimate_policy_recommend,'/api/estimate-policies/claims':estimate_policy_claims,'/api/claims/cross-check':cross_check,'/api/exposure/90-day':exposure}
        if path in routes:
            try: return self._json(routes[path](payload))
            except (ValueError, OSError) as error: return self._json({'error':str(error)},400)
        self.send_error(404,'API route not found')

if __name__ == '__main__':
    import os
    os.chdir(ROOT)
    print('Healthcare Cost Estimator at http://127.0.0.1:8000')
    ThreadingHTTPServer(('127.0.0.1',8000), Handler).serve_forever()
