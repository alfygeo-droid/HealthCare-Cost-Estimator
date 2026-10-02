import { useEffect, useState } from 'react';
import { calculateInsurance, estimateCost, getAgentOverview, getCurrentUser, getDemoPolicy, getDocumentSummary, getPatientOverview, getPolicyholder, login, logout, lookupCghs, reviewClaim, searchPolicyholders, uploadBill } from './services/api.js';

const estimateFields = [
  { name: 'Age', label: 'Patient age', type: 'number', min: 0, max: 120, initial: 45 },
  { name: 'Gender', label: 'Gender', options: ['Female', 'Male'] },
  { name: 'Department', label: 'Department', options: ['Cardiology','Dermatology','Emergency','General Surgery','Gynecology','ICU','Neurology','Oncology','Orthopedics','Pediatrics'] },
  { name: 'Diagnosis', label: 'Diagnosis', options: ['Asthma','Cancer','Diabetes','Fracture','Heart Disease','Hypertension','Infection','Kidney Disease','Pneumonia','Stroke'] },
  { name: 'Severity_Level', label: 'Severity', options: ['Low','Medium','High','Critical'] },
  { name: 'Length_of_Stay_Days', label: 'Expected stay (days)', type: 'number', min: 0, max: 365, initial: 3 },
  { name: 'Wait_Time_Minutes', label: 'Wait time (minutes)', type: 'number', min: 0, max: 1440, initial: 45 },
  { name: 'Insurance_Type', label: 'Insurance type', options: ['Employer','Government','Private','Self-Pay'] },
];
const initialEstimate = Object.fromEntries(estimateFields.map(f => [f.name, f.options?.[0] ?? f.initial]));
const initialInsurance = { treatment_cost: '100000', room_cost: '12000', room_days: '3', sum_insured: '500000', deductible: '10000', copay_percentage: '10', previous_claim_amount: '0', room_rent_limit_type: 'per_day', room_rent_limit: '5000', treatment_sub_limit: '' };
const inr = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0));

function LoginScreen({ onLogin, error, loading }) {
  const [role, setRole] = useState('patient');
  const [signId, setSignId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  function submit(event) {
    event.preventDefault();
    onLogin({ role, sign_id: signId.trim(), password });
  }

  return <main className="auth-screen">
    <div className="auth-glow auth-glow-one" aria-hidden="true" />
    <div className="auth-glow auth-glow-two" aria-hidden="true" />
    <header className="auth-header"><a className="brand" href="#login"><span className="brand-mark">✳</span><span>carecost<span className="brand-ai"> AI</span></span></a><span className="auth-security"><span className="status-dot"/>Secure care workspace</span></header>
    <section className="auth-layout">
      <div className="auth-story">
        <span className="eyebrow"><span className="sparkle">✦</span> CARE COSTS, MADE CLEARER</span>
        <h1>Plan for care<br/><em>with confidence.</em></h1>
        <p>Sign in to review cost estimates, insurance scenarios and hospital bill details in one private workspace.</p>
        <div className="auth-assurance"><span className="shield">✓</span> Your account is protected with a private session</div>
        <div className="auth-illustration" aria-hidden="true"><div className="auth-orbit auth-orbit-a"/><div className="auth-orbit auth-orbit-b"/><div className="auth-glass-card"><span className="auth-card-icon">✳</span><span className="auth-card-line auth-card-line-long"/><span className="auth-card-line"/><span className="auth-card-chip">Care, made clearer</span></div><span className="auth-float auth-float-a">₹</span><span className="auth-float auth-float-b">✦</span><span className="auth-float auth-float-c">+</span></div>
      </div>
      <div className="login-card">
        <div className="login-card-heading"><span className="login-mark">↗</span><span className="step-label">WELCOME BACK <span>·</span> SIGN IN</span><h2>Sign in to CarePath</h2><p>Choose your workspace, then enter your credentials.</p></div>
        <div className="role-choice" aria-label="Choose account type"><button type="button" className={role === 'patient' ? 'selected' : ''} onClick={() => setRole('patient')}>Patient</button><button type="button" className={role === 'insurance_agent' ? 'selected' : ''} onClick={() => setRole('insurance_agent')}>Insurance Agent</button></div>
        <form className="login-form" autoComplete="off" onSubmit={submit}>
          <label className="login-field"><span>Sign ID</span><span className="login-input-wrap"><span className="login-input-icon" aria-hidden="true">◉</span><input autoComplete="off" name="carepath_sign_id" type="text" value={signId} onChange={event => setSignId(event.target.value)} placeholder="Enter your Sign ID" required minLength={3} maxLength={64}/></span></label>
          <label className="login-field"><span>Password</span><span className="login-input-wrap"><span className="login-input-icon" aria-hidden="true">⌑</span><input autoComplete="new-password" name="carepath_password" type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password" required maxLength={1024}/><button className="password-toggle" type="button" onClick={() => setShowPassword(current => !current)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>{showPassword ? 'Hide' : 'Show'}</button></span></label>
          {error && <div className="login-error" role="alert"><span aria-hidden="true">!</span>{error}</div>}
          <button className="login-submit" type="submit" disabled={loading || !signId.trim() || !password}>{loading ? <><span className="login-spinner"/>Signing in…</> : <>Sign in <span aria-hidden="true">→</span></>}</button>
        </form>
        <p className="login-privacy"><span aria-hidden="true">◈</span> Passwords are verified securely and never returned by the server.</p>
      </div>
    </section>
    <footer className="auth-footer"><span>CareCost AI <span className="footer-dot">·</span> A clearer view of care costs</span><span>Private sign in <span className="footer-dot">·</span> Secure session</span></footer>
  </main>;
}

function PatientOverview({ currentUser }) {
  const [data, setData] = useState(null);
  useEffect(() => { getPatientOverview().then(setData).catch(() => setData(null)); }, []);
  if (!data) return <section className="patient-summary loading-summary" aria-label="Patient overview loading">Loading your overview…</section>;
  const { profile, policy, metrics } = data;
  return <section className="patient-summary" aria-label="Patient financial overview">
    <div className="summary-profile" id="profile"><span className="profile-avatar">{profile.name.split(' ').map(part => part[0]).join('')}</span><div><small>MY PROFILE</small><strong>{profile.name}</strong><span>Sign ID · {currentUser.sign_id}</span></div><div><small>PHONE</small><strong>{profile.phone}</strong></div><div><small>DATE OF BIRTH</small><strong>{profile.date_of_birth}</strong></div></div>
    <div className="patient-metrics"><article id="policies"><small>ACTIVE POLICY</small><strong>{policy.name}</strong><span>{policy.status} · {inr(policy.coverage)} coverage</span></article><article id="claims"><small>RECENT CLAIM</small><strong>{inr(metrics.recent_claim)}</strong><span>{metrics.recent_claim_status}</span></article><article><small>OUT-OF-POCKET</small><strong>{inr(metrics.out_of_pocket)}</strong><span>Estimated patient responsibility</span></article><article id="exposure"><small>90-DAY EXPOSURE</small><strong>{inr(metrics.exposure_90_day)}</strong><span>Planning estimate · INR</span></article></div>
    <div className="patient-summary-lower"><div><small>INSURANCE PAYABLE ESTIMATE</small><strong>{inr(metrics.insurance_payable)}</strong><p>Illustrative estimate based on demo policy terms. Confirm final amounts with the insurer.</p></div><div id="safeguards"><small>PENDING ACTIONS · CLAIM SAFEGUARDS</small><ul>{data.pending_actions.map(action => <li key={action}>{action}</li>)}</ul></div></div>
    <div className="patient-history" id="claims"><div><h3>Recent claims</h3>{data.claims.map(claim => <p key={claim.id}><b>{claim.id}</b><span>{inr(claim.amount)} · {claim.status}</span></p>)}</div><div><h3>Recent bills</h3>{data.bills.map((bill, index) => <p key={index}><b>{bill.document}</b><span>{inr(bill.total)} · {bill.review_status}</span></p>)}</div></div>
  </section>;
}

function AgentDashboard({ currentUser, onSignOut, logoutError }) {
  const [data, setData] = useState(null);
  const [policyholders, setPolicyholders] = useState([]);
  const [query, setQuery] = useState('');
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState('Overview');
  async function refresh() {
    setBusy(true); setError('');
    try { const [overview, members] = await Promise.all([getAgentOverview(), searchPolicyholders(query)]); setData(overview); setPolicyholders(members); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  useEffect(() => { refresh(); }, []);
  async function openMember(signId) {
    setView('Policyholders'); setError('');
    try { setDetail(await getPolicyholder(signId)); }
    catch (err) { setError(err.message); }
  }
  async function search(event) { event.preventDefault(); setBusy(true); try { setPolicyholders(await searchPolicyholders(query)); } catch (err) { setError(err.message); } finally { setBusy(false); } }
  async function updateClaim(claimId, status) {
    setError('');
    try { await reviewClaim(claimId, status); if (detail) setDetail(await getPolicyholder(detail.sign_id)); await refresh(); }
    catch (err) { setError(err.message); }
  }
  const nav = ['Overview','Policyholders','Claims','Pending Review','Bill Intelligence','Cost Estimator','Claim Safeguards','90-Day Exposure'];
  return <div className="role-shell agent-shell"><aside className="role-sidebar"><a className="sidebar-brand" href="#agent"><span>✳</span><b>CarePath</b></a><small>COST &amp; CLAIM INTELLIGENCE</small><nav aria-label="Insurance agent navigation">{nav.map(item => <button type="button" key={item} className={view === item ? 'active' : ''} onClick={() => { setView(item); setDetail(null); }}>{item}</button>)}</nav><div className="sidebar-role">INSURANCE AGENT<br/><strong>{currentUser.sign_id}</strong></div></aside><main className="agent-content">
    <header className="agent-topbar"><div><span className="eyebrow">INSURANCE AGENT WORKSPACE</span><h1>{view}</h1></div><div className="account-controls"><span className="top-note"><span className="status-dot"/>Signed in as {currentUser.sign_id}</span><button type="button" className="sign-out-button" onClick={onSignOut}>Sign out</button></div></header>
    {logoutError && <div className="error-box">{logoutError}</div>}{error && <div className="error-box" role="alert">{error}</div>}
    {view === 'Overview' && data && <><section className="agent-metrics"><article><small>TOTAL POLICYHOLDERS</small><strong>{data.metrics.total_policyholders}</strong></article><article><small>ACTIVE CLAIMS</small><strong>{data.metrics.active_claims}</strong></article><article><small>PENDING REVIEW</small><strong>{data.metrics.pending_review}</strong></article><article><small>CLAIM EXPOSURE</small><strong>{inr(data.metrics.claim_exposure)}</strong></article></section><section className="agent-panel"><div className="panel-heading"><div><h2>Recent claims</h2><p>Assigned policyholders · demo data</p></div><button className="secondary-button" onClick={() => setView('Claims')}>View all claims</button></div><div className="table-scroll"><table className="agent-table"><thead><tr><th>Claim ID</th><th>Patient</th><th>Policy</th><th>Claim amount</th><th>Est. payable</th><th>Responsibility</th><th>Status</th><th>Action</th></tr></thead><tbody>{data.claims.map(claim => <tr key={claim.id}><td>{claim.id}</td><td><button className="text-link" onClick={() => openMember(claim.sign_id)}>{claim.patient}</button></td><td>{claim.policy}</td><td>{inr(claim.amount)}</td><td>{inr(claim.payable)}</td><td>{inr(claim.responsibility)}</td><td><span className="claim-status">{claim.status}</span></td><td><button className="text-link" onClick={() => openMember(claim.sign_id)}>Review →</button></td></tr>)}</tbody></table></div></section></>}
    {(['Policyholders','Claims','Pending Review','Bill Intelligence','Claim Safeguards','90-Day Exposure'].includes(view)) && !detail && <section className="agent-panel"><div className="panel-heading"><div><h2>{view}</h2><p>Only assigned demo policyholders are shown.</p></div><form className="member-search" onSubmit={search}><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search name or Sign ID"/><button className="secondary-button" disabled={busy}>Search</button></form></div><div className="table-scroll"><table className="agent-table"><thead><tr><th>Policyholder</th><th>Sign ID</th><th>Policy</th><th>Claim</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>{(view === 'Pending Review' ? policyholders.filter(person => ['Pending Review','Needs Information'].includes(person.claim_status.status)) : policyholders).map(person => <tr key={person.sign_id}><td>{person.name}</td><td>{person.sign_id}</td><td>{person.policy}</td><td>{person.claim_status.id}</td><td>{inr(person.claim_amount)}</td><td><span className="claim-status">{person.claim_status.status}</span></td><td><button className="text-link" onClick={() => openMember(person.sign_id)}>Open profile →</button></td></tr>)}</tbody></table>{policyholders.length === 0 && <p className="empty-state">No assigned policyholders match this search.</p>}</div></section>}
    {detail && <section className="agent-panel member-detail"><div className="panel-heading"><div><span className="eyebrow">POLICYHOLDER PROFILE</span><h2>{detail.name}</h2><p>{detail.sign_id} · {detail.phone} · DOB {detail.date_of_birth}</p></div><button className="secondary-button" onClick={() => setDetail(null)}>Back to list</button></div><div className="detail-grid"><article><small>POLICY</small><strong>{detail.policy.plan}</strong><span>{detail.policy.insurer} · {detail.policy.number}</span><span>{inr(detail.policy.coverage)} coverage · {detail.policy.status}</span><span>Deductible {inr(detail.policy.deductible)} · Co-pay {detail.policy.copay_percentage}%</span><span>Room limit {inr(detail.policy.room_limit)} / day</span></article><article><small>FINANCIAL SUMMARY</small><strong>{inr(detail.treatment_estimate)} treatment estimate</strong><span>Estimated insurer payable · {inr(detail.payable)}</span><span>Patient responsibility · {inr(detail.responsibility)}</span><span>90-day exposure · {inr(detail.exposure_90_day)}</span></article></div><h3>Claims</h3><div className="table-scroll"><table className="agent-table"><thead><tr><th>Claim</th><th>Date</th><th>Amount</th><th>Insurer payable</th><th>Patient responsibility</th><th>Status / review</th></tr></thead><tbody>{detail.claims.map(claim => <tr key={claim.id}><td>{claim.id}</td><td>{claim.date}</td><td>{inr(claim.amount)}</td><td>{inr(claim.payable)}</td><td>{inr(claim.responsibility)}</td><td><select value={claim.status} onChange={event => updateClaim(claim.id, event.target.value)}><option>Pending Review</option><option>Under Review</option><option>Approved</option><option>Needs Information</option><option>Closed</option></select></td></tr>)}</tbody></table></div><h3>Bills</h3><div className="table-scroll"><table className="agent-table"><thead><tr><th>Bill / document</th><th>Extraction</th><th>Total</th><th>Review status</th></tr></thead><tbody>{detail.bills.map((bill, index) => <tr key={index}><td>{bill.document}</td><td>{bill.extraction_status}</td><td>{inr(bill.total)}</td><td>{bill.review_status}</td></tr>)}</tbody></table></div></section>}
    {view === 'Cost Estimator' && <AgentCostEstimator/>}
    <footer className="page-footer"><span>CarePath · Insurance Agent</span><span>Local demo records are illustrative.</span></footer>
  </main></div>;
}

function AgentCostEstimator() {
  const [values, setValues] = useState(initialEstimate);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError(''); setResult(null);
    const numeric = ['Age','Length_of_Stay_Days','Wait_Time_Minutes'];
    try { setResult(await estimateCost(Object.fromEntries(Object.entries(values).map(([key,value]) => [key,numeric.includes(key) ? Number(value) : value])))); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }
  return <section className="agent-panel estimator" aria-label="Cost estimator"><div className="form-heading"><div><span className="step-label">COST ESTIMATE · USD</span><h2>Estimate a care scenario</h2><p>Dataset-based ML estimate for planning; not a final hospital bill.</p></div></div><form onSubmit={submit}><div className="form-grid">{estimateFields.map(field => <label className="field" key={field.name}><span>{field.label}</span>{field.options ? <select value={values[field.name]} onChange={event => setValues(current => ({...current,[field.name]:event.target.value}))}>{field.options.map(option => <option key={option}>{option}</option>)}</select> : <input type="number" min={field.min} max={field.max} value={values[field.name]} onChange={event => setValues(current => ({...current,[field.name]:event.target.value}))}/>}</label>)}</div><div className="form-footer"><span className="form-hint">Dataset-based ML estimate in USD.</span><button type="submit" disabled={loading}>{loading ? 'Calculating…' : 'Get estimate'}</button></div></form>{error && <div className="error-box">{error}</div>}{result && <div className="result-card"><div><span className="result-label">ESTIMATED COST · USD</span><strong>{new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(result.estimated_cost)}</strong></div></div>}</section>;
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  const [values, setValues] = useState(initialEstimate);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoPolicy, setDemoPolicy] = useState(null);
  const [insuranceValues, setInsuranceValues] = useState(initialInsurance);
  const [insuranceResult, setInsuranceResult] = useState(null);
  const [insuranceError, setInsuranceError] = useState('');
  const [insuranceLoading, setInsuranceLoading] = useState(false);
  const [policyError, setPolicyError] = useState('');
  const [cghsValues, setCghsValues] = useState({ code: '', tier: 'Tier I', rateType: 'nabh_rate' });
  const [cghsMessage, setCghsMessage] = useState('');
  const [cghsLoading, setCghsLoading] = useState(false);
  const [treatmentSource, setTreatmentSource] = useState('Entered by you');
  const [documentState, setDocumentState] = useState({ loading: false, progress: 0, error: '', upload: null, summary: null });
  const [patientOverview, setPatientOverview] = useState(null);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then(user => { if (active) setCurrentUser(user); })
      .catch(err => { if (active) setLoginError(err.message); })
      .finally(() => { if (active) setCheckingSession(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!currentUser || currentUser.role !== 'patient') return;
    getDemoPolicy().then(data => {
      setDemoPolicy(data.policy);
      setInsuranceValues(current => ({ ...current, sum_insured: String(data.policy.sum_insured), deductible: String(data.policy.deductible), copay_percentage: String(data.policy.copay_percentage), room_rent_limit_type: data.policy.room_rent_limit_type, room_rent_limit: data.policy.room_rent_limit == null ? '' : String(data.policy.room_rent_limit) }));
    }).catch(err => setPolicyError(err.message));
  }, [currentUser]);

  async function submitLogin(credentials) {
    setLoginLoading(true);
    setLoginError('');
    try {
      const result = await login(credentials);
      setCurrentUser(result.user);
      window.history.replaceState(null, '', result.user.role === 'insurance_agent' ? '#agent' : '#patient');
    } catch (err) {
      setLoginError(err.message === 'Invalid Sign ID or password.' ? 'The Sign ID or password is incorrect.' : err.message || 'Unable to sign in. Please try again.');
    } finally {
      setLoginLoading(false);
    }
  }

  async function signOut() {
    setLogoutError('');
    try {
      await logout();
      setCurrentUser(null);
      setResult(null);
      setInsuranceResult(null);
      setDocumentState({ loading: false, progress: 0, error: '', upload: null, summary: null });
      window.history.replaceState(null, '', '#login');
    } catch (err) {
      setLogoutError(err.message || 'Unable to sign out. Please try again.');
    }
  }

  const updateEstimate = (name, value) => setValues(current => ({ ...current, [name]: value }));
  const updateInsurance = (name, value) => {
    setInsuranceValues(current => ({ ...current, [name]: value }));
    setInsuranceResult(null);
    if (name === 'treatment_cost') setTreatmentSource('Entered by you');
  };

  async function submitEstimate(event) {
    event.preventDefault(); setLoading(true); setError(''); setResult(null);
    try {
      const numeric = ['Age','Length_of_Stay_Days','Wait_Time_Minutes'];
      const payload = Object.fromEntries(Object.entries(values).map(([key,value]) => [key,numeric.includes(key) ? Number(value) : value]));
      setResult(await estimateCost(payload));
    } catch (err) { setError(err.message || 'Unable to create an estimate. Please try again.'); }
    finally { setLoading(false); }
  }

  async function useCghsReference(event) {
    event.preventDefault(); setCghsLoading(true); setCghsMessage(''); setInsuranceError('');
    try {
      if (!cghsValues.code.trim()) throw new Error('Enter a CGHS code to look up a reference rate.');
      const matches = await lookupCghs(cghsValues.code.trim());
      const match = matches.find(row => row.tier === cghsValues.tier);
      const rate = match?.rates?.[cghsValues.rateType];
      if (rate == null) throw new Error(`No ${cghsValues.rateType.replaceAll('_', ' ')} is available for this CGHS code and tier.`);
      updateInsurance('treatment_cost', String(rate));
      setTreatmentSource(`CGHS reference rate · ${match.tier}`);
      setCghsMessage(`${match.procedure_name}: ${inr(rate)} · CGHS reference rate, not actual hospital cost.`);
    } catch (err) { setCghsMessage(err.message); }
    finally { setCghsLoading(false); }
  }

  async function submitInsurance(event) {
    event.preventDefault(); setInsuranceLoading(true); setInsuranceError(''); setInsuranceResult(null);
    if (!demoPolicy) { setInsuranceError(policyError || 'The policy configuration is not available.'); setInsuranceLoading(false); return; }
    const noRoomLimit = insuranceValues.room_rent_limit_type === 'none';
    const payload = {
      policy: {
        ...demoPolicy,
        policy_name: 'Demo Policy',
        sum_insured: insuranceValues.sum_insured,
        deductible: insuranceValues.deductible,
        copay_percentage: insuranceValues.copay_percentage,
        room_rent_limit_type: insuranceValues.room_rent_limit_type,
        room_rent_limit: noRoomLimit ? null : insuranceValues.room_rent_limit,
        treatment_sub_limit: null,
      },
      treatment_cost: insuranceValues.treatment_cost,
      room_cost: insuranceValues.room_cost || '0',
      room_days: Number(insuranceValues.room_days || 0),
      previous_claim_amount: insuranceValues.previous_claim_amount || '0',
      treatment_sub_limit: insuranceValues.treatment_sub_limit || null,
    };
    try { setInsuranceResult(await calculateInsurance(payload)); }
    catch (err) { setInsuranceError(err.message || 'Unable to calculate this estimate.'); }
    finally { setInsuranceLoading(false); }
  }

  async function uploadHospitalBill(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setDocumentState({ loading: true, progress: 0, error: '', upload: null, summary: null });
    try {
      const upload = await uploadBill(file, progress => setDocumentState(current => ({ ...current, progress })));
      setDocumentState(current => ({ ...current, upload, progress: 100 }));
      const summary = await getDocumentSummary(upload.document_id);
      setDocumentState(current => ({ ...current, loading: false, summary }));
    } catch (err) {
      setDocumentState({ loading: false, progress: 0, error: err.message || 'Unable to process this bill.', upload: null, summary: null });
    }
  }

  function useExtractedTotal() {
    const amount = documentState.summary?.bill?.total_amount?.value;
    if (amount == null || !Number.isFinite(Number(amount))) return;
    updateInsurance('treatment_cost', String(amount));
    setTreatmentSource('Uploaded bill total · verify before calculating');
    document.getElementById('insurance-title')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const billFields = [
    ['Hospital', 'hospital_name'], ['Bill date', 'bill_date'], ['Admission date', 'admission_date'], ['Discharge date', 'discharge_date'], ['Bill currency', 'currency'],
    ['Total amount', 'total_amount'], ['Room charges', 'room_charges'], ['Doctor charges', 'doctor_charges'],
    ['Procedure charges', 'procedure_charges'], ['Medicine charges', 'medicine_charges'], ['Laboratory charges', 'laboratory_charges'],
    ['Imaging charges', 'imaging_charges'], ['Other charges', 'other_charges'],
  ];
  const billCurrency = documentState.summary?.bill?.currency?.value;
  const formatBillAmount = value => billCurrency === 'INR' ? inr(value) : billCurrency === 'USD' ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value)) : `${Number(value).toLocaleString('en-IN')} · currency needs review`;
  const renderBillValue = (field, key) => field?.value == null ? <span className="bill-muted">{field?.status?.replaceAll('_', ' ') || 'not found'}</span> : ['total_amount','room_charges','doctor_charges','procedure_charges','medicine_charges','laboratory_charges','imaging_charges','other_charges'].includes(key) ? formatBillAmount(field.value) : String(field.value);

  if (checkingSession) return <main className="auth-screen auth-checking"><div className="login-mark">✳</div><p>Checking your secure session…</p></main>;
  if (!currentUser) return <LoginScreen onLogin={submitLogin} error={loginError} loading={loginLoading}/>;

  if (currentUser.role === 'insurance_agent') return <AgentDashboard currentUser={currentUser} onSignOut={signOut} logoutError={logoutError}/>;

  return <div className="role-shell"><aside className="role-sidebar"><a className="sidebar-brand" href="#overview"><span>✳</span><b>CarePath</b></a><small>COST &amp; CLAIM INTELLIGENCE</small><nav aria-label="Patient navigation"><a href="#overview">Overview</a><a href="#profile">My Profile</a><a href="#policies">My Policies</a><a href="#estimate">Cost Estimator</a><a href="#documents">My Bills</a><a href="#insurance-title">Insurance Calculator</a><a href="#claims">Claims</a><a href="#safeguards">Claim Safeguards</a><a href="#exposure">90-Day Exposure</a></nav></aside><main className="page-shell role-content">
    <header className="topbar"><a className="brand" href="#overview"><span className="brand-mark">✳</span><span>carecost<span className="brand-ai"> AI</span></span></a><div className="account-controls"><span className="top-note"><span className="status-dot"/>Signed in as {currentUser.sign_id}</span><button type="button" className="sign-out-button" onClick={signOut}>Sign out</button></div></header>
    <section className="overview-welcome" id="overview"><div><span className="eyebrow"><span className="sparkle">✦</span> PATIENT OVERVIEW</span><h1>Welcome, {currentUser.sign_id}</h1><p>Your care cost workspace is ready. Choose a starting point below.</p></div><div className="overview-access"><span className="shield">✓</span> Private session active</div></section>
    {logoutError && <div className="error-box" role="alert">{logoutError}</div>}
    <PatientOverview currentUser={currentUser}/>
    <nav className="overview-shortcuts" aria-label="Patient overview sections"><a href="#estimate"><span>01</span><strong>Cost estimate</strong><small>Explore a dataset-based care estimate</small><b aria-hidden="true">↗</b></a><a href="#insurance-title"><span>02</span><strong>Insurance overview</strong><small>Review coverage and out-of-pocket</small><b aria-hidden="true">↗</b></a><a href="#documents"><span>03</span><strong>Bill review</strong><small>Extract bill details for review</small><b aria-hidden="true">↗</b></a></nav>
    <section className="hero" id="home"><div className="hero-copy"><span className="eyebrow"><span className="sparkle">✦</span> HEALTHCARE COST ESTIMATOR</span><h1>Plan with a little<br/><em>more clarity.</em></h1><p>Get a quick, data-based estimate for a hospital stay. A helpful starting point for conversations about care and cost.</p><div className="hero-assurance"><span className="shield">✓</span> Private by design <span className="assurance-sep">·</span> No patient records required</div></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="art-cross">+</div><div className="art-card"><span className="art-icon">✳</span><span className="art-line wide"/><span className="art-line"/><span className="art-pill">Care, made clearer</span></div><span className="art-dot dot-a"/><span className="art-dot dot-b"/><span className="art-dot dot-c"/></div></section>
    <section className="estimator" id="estimate" aria-labelledby="form-title"><div className="form-heading"><div><span className="step-label">YOUR ESTIMATE <span>·</span> 01</span><h2 id="form-title">Tell us about the care</h2><p>Use the details you know. You can adjust them anytime.</p></div><div className="form-icon">⌁</div></div>
      <form onSubmit={submitEstimate}><div className="form-grid">{estimateFields.map(field => <label className="field" key={field.name}><span>{field.label}</span>{field.options ? <select value={values[field.name]} onChange={e => updateEstimate(field.name,e.target.value)}>{field.options.map(option => <option key={option}>{option}</option>)}</select> : <input required type="number" min={field.min} max={field.max} value={values[field.name]} onChange={e => updateEstimate(field.name,e.target.value)}/>}</label>)}</div><div className="form-footer"><span className="form-hint"><span className="info-icon">i</span> Dataset-based estimate in USD, from anonymized patterns.</span><button type="submit" disabled={loading}>{loading ? 'Calculating…' : 'Get my estimate'} <span aria-hidden="true">↗</span></button></div></form>
      {error && <div className="error-box" role="alert">{error}</div>}{result && <div className="result-card" aria-live="polite"><div><span className="result-label">ESTIMATED COST</span><strong>{new Intl.NumberFormat('en-US',{style:'currency',currency:result.currency}).format(result.estimated_cost)}</strong><p>Dataset-based ML prediction · USD · {result.source}</p></div><span className="result-check">✓</span><small>{result.disclaimer}</small></div>}
    </section>

    <section className="document-section" id="documents" aria-labelledby="document-title">
      <div className="insurance-intro"><span className="eyebrow"><span className="sparkle">✦</span> AI BILL INTELLIGENCE</span><h2 id="document-title">Review a hospital bill</h2><p>Upload a PDF, JPG, or PNG bill to extract amounts for review. Patient names and identifiers are not extracted or displayed.</p></div>
      <div className="document-card">
        <label className="document-picker"><span className="document-icon">↑</span><strong>Choose a bill to upload</strong><small>PDF, JPG, or PNG · maximum 10 MB</small><input type="file" accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png" onChange={uploadHospitalBill} disabled={documentState.loading}/></label>
        <p className="document-privacy">Files are stored in a private server directory outside the frontend. Retention defaults to 7 days; configure <code>DOCUMENT_RETENTION_DAYS</code> and run the cleanup script to remove expired files. Extracted amounts are informational and must be checked against the original bill.</p>
        {documentState.loading && <div className="document-progress" role="status"><span>Uploading and processing… {documentState.progress}%</span><progress max="100" value={documentState.progress}/></div>}
        {documentState.error && <div className="error-box" role="alert">{documentState.error}</div>}
        {documentState.upload && <p className="document-status" role="status">{documentState.upload.message}</p>}
        {documentState.summary && <div className="bill-summary">
          <div className="bill-summary-heading"><div><span className="result-label">EXTRACTED BILL DETAILS</span><h3>Review before using</h3></div><span className="policy-badge">{documentState.summary.extraction_status.replaceAll('_', ' ')}</span></div>
          <div className="bill-fields">{billFields.map(([label,key]) => <div className="bill-field" key={key}><span>{label}</span><strong>{renderBillValue(documentState.summary.bill[key], key)}</strong><small>{documentState.summary.bill[key]?.status?.replaceAll('_', ' ')}</small></div>)}</div>
          {documentState.summary.bill.total_amount?.value != null && billCurrency === 'INR' && <button type="button" className="secondary-button" onClick={useExtractedTotal}>Use extracted total in Insurance Calculator</button>}
          {documentState.summary.bill.total_amount?.value != null && billCurrency !== 'INR' && <p className="document-status">The bill currency is {billCurrency || 'unconfirmed'}. Confirm an INR amount before entering it into the INR insurance calculator.</p>}
          {billCurrency === 'INR' && <p className="document-status">Extracted information should be verified against the original bill. The amount is copied as the treatment amount in INR. Review it and submit the insurance calculation yourself; bill totals are not automatically treated as eligible coverage.</p>}
          {documentState.summary.bill.bill_items?.length > 0 && <div className="bill-items"><h4>Line items · verify extracted values</h4><div className="bill-items-scroll"><table><thead><tr><th>Description</th><th>Category</th><th>Qty</th><th>Unit price</th><th>Total</th></tr></thead><tbody>{documentState.summary.bill.bill_items.map((item,index)=><tr key={index}><td>{item.description}</td><td>{item.category}</td><td>{item.quantity}</td><td>{formatBillAmount(item.unit_price)}</td><td>{formatBillAmount(item.total_price)}</td></tr>)}</tbody></table></div></div>}
        </div>}
      </div>
    </section>

    <section className="insurance-section" aria-labelledby="insurance-title">
      <div className="insurance-intro"><span className="eyebrow"><span className="sparkle">✦</span> INR POLICY ESTIMATE</span><h2 id="insurance-title">Insurance &amp; Out-of-Pocket Calculator</h2><p>Estimate a possible coverage share from the INR amounts and policy terms you provide.</p><div className="knowledge-tags"><span>KNOWN · entered or referenced</span><span>ESTIMATED · calculated</span><span>UNKNOWN · needs verification</span></div></div>
      <div className="insurance-layout">
        <form className="insurance-form" onSubmit={submitInsurance}>
          <div className="policy-banner"><span className="policy-badge">DEMO POLICY</span><span>{demoPolicy?.policy_name || 'Loading policy…'} · illustrative starting values only</span></div>
          {policyError && <div className="error-box" role="alert">{policyError}</div>}
          <div className="insurance-fields">
            <label className="field"><span>Treatment/reference amount (INR)</span><input required type="number" min="0" step="0.01" value={insuranceValues.treatment_cost} onChange={e=>updateInsurance('treatment_cost',e.target.value)}/><small>Known · {treatmentSource}</small></label>
            <label className="field"><span>Room cost total (INR)</span><input required type="number" min="0" step="0.01" value={insuranceValues.room_cost} onChange={e=>updateInsurance('room_cost',e.target.value)}/></label>
            <label className="field"><span>Hospital days</span><input required type="number" min="0" max="365" step="1" value={insuranceValues.room_days} onChange={e=>updateInsurance('room_days',e.target.value)}/></label>
            <label className="field"><span>Sum insured (INR)</span><input required type="number" min="0.01" step="0.01" value={insuranceValues.sum_insured} onChange={e=>updateInsurance('sum_insured',e.target.value)}/></label>
            <label className="field"><span>Deductible (INR)</span><input required type="number" min="0" step="0.01" value={insuranceValues.deductible} onChange={e=>updateInsurance('deductible',e.target.value)}/></label>
            <label className="field"><span>Co-pay (%)</span><input required type="number" min="0" max="100" step="0.01" value={insuranceValues.copay_percentage} onChange={e=>updateInsurance('copay_percentage',e.target.value)}/></label>
            <label className="field"><span>Previous claims (INR)</span><input required type="number" min="0" step="0.01" value={insuranceValues.previous_claim_amount} onChange={e=>updateInsurance('previous_claim_amount',e.target.value)}/></label>
            <label className="field"><span>Treatment sub-limit (INR, optional)</span><input type="number" min="0" step="0.01" placeholder="No separate limit" value={insuranceValues.treatment_sub_limit} onChange={e=>updateInsurance('treatment_sub_limit',e.target.value)}/></label>
            <label className="field"><span>Room-rent rule</span><select value={insuranceValues.room_rent_limit_type} onChange={e=>{const type=e.target.value;setInsuranceValues(current=>({...current,room_rent_limit_type:type,room_rent_limit:type==='percentage_of_sum_insured'?'1':type==='per_day'?'5000':current.room_rent_limit}));setInsuranceResult(null);}}><option value="per_day">Maximum per day</option><option value="percentage_of_sum_insured">Percent of sum insured per day</option><option value="none">No room limit</option></select></label>
            {insuranceValues.room_rent_limit_type!=='none' && <label className="field"><span>{insuranceValues.room_rent_limit_type==='per_day'?'Maximum room rent per day (INR)':'Room limit (% of sum insured per day)'}</span><input required type="number" min="0" step="0.01" value={insuranceValues.room_rent_limit} onChange={e=>updateInsurance('room_rent_limit',e.target.value)}/></label>}
          </div>
          <div className="cghs-lookup"><div className="cghs-heading"><strong>Optional CGHS reference</strong><span>Reference only · not an actual hospital bill</span></div><div className="cghs-fields"><label className="field"><span>CGHS code</span><input value={cghsValues.code} onChange={e=>setCghsValues(v=>({...v,code:e.target.value}))} placeholder="e.g. CN001"/></label><label className="field"><span>City tier</span><select value={cghsValues.tier} onChange={e=>setCghsValues(v=>({...v,tier:e.target.value}))}><option>Tier I</option><option>Tier II</option><option>Tier III</option></select></label><label className="field"><span>Reference rate type</span><select value={cghsValues.rateType} onChange={e=>setCghsValues(v=>({...v,rateType:e.target.value}))}><option value="nabh_rate">NABH</option><option value="non_nabh_rate">Non-NABH</option><option value="super_speciality_rate">Super-speciality</option></select></label><button className="secondary-button" type="button" onClick={useCghsReference} disabled={cghsLoading}>{cghsLoading?'Looking up…':'Use CGHS reference'}</button></div>{cghsMessage&&<p className="cghs-message" role="status">{cghsMessage}</p>}</div>
          <div className="form-footer"><span className="form-hint"><span className="info-icon">i</span> All insurance calculations are in INR.</span><button type="submit" disabled={insuranceLoading||!demoPolicy}>{insuranceLoading?'Calculating…':'Calculate estimate'} <span aria-hidden="true">↗</span></button></div>
          {insuranceError&&<div className="error-box" role="alert">{insuranceError}</div>}
        </form>

        <div className="insurance-results" aria-live="polite">
          {insuranceResult ? <>
            <div className="coverage-cards"><div className="coverage-card payable"><span>ESTIMATED INSURANCE COVERAGE</span><strong>{inr(insuranceResult.insurer_payable)}</strong><small>Estimated · INR</small></div><div className="coverage-card out-pocket"><span>ESTIMATED OUT-OF-POCKET</span><strong>{inr(insuranceResult.estimated_out_of_pocket)}</strong><small>Estimated · INR</small></div></div>
            <div className="breakdown-card"><h3>Coverage breakdown <span>Estimate · INR</span></h3><div className="breakdown-row"><span>Treatment amount <small>Known · {treatmentSource}</small></span><b>{inr(insuranceResult.treatment_cost)}</b></div><div className="breakdown-row"><span>Room cost <small>Known · entered by you</small></span><b>{inr(insuranceResult.room_cost)}</b></div><div className="breakdown-row"><span>Room limitation impact <small>Amount above configured room limit</small></span><b>− {inr(insuranceResult.room_limitation_impact.amount_over_limit)}</b></div><div className="breakdown-row"><span>Eligible amount <small>After room rule, before treatment sub-limit</small></span><b>{inr(insuranceResult.eligible_amount)}</b></div><div className="breakdown-row"><span>Treatment sub-limit adjustment <small>Above entered/configured sub-limit</small></span><b>− {inr(insuranceResult.treatment_sub_limit_impact.amount_above_sub_limit)}</b></div><div className="breakdown-row"><span>Deductible applied</span><b>− {inr(insuranceResult.deductible_applied)}</b></div><div className="breakdown-row"><span>Co-pay ({insuranceResult.copay_percentage}%)</span><b>− {inr(insuranceResult.copay_amount)}</b></div><div className="breakdown-row"><span>Remaining sum insured <small>After previous claims</small></span><b>{inr(insuranceResult.remaining_sum_insured)}</b></div><div className="breakdown-row"><span>Policy limit adjustment</span><b>− {inr(insuranceResult.policy_limit_impact)}</b></div><div className="breakdown-row total"><span>Estimated insurer payable</span><b>{inr(insuranceResult.insurer_payable)}</b></div><div className="breakdown-row total"><span>Estimated patient pays</span><b>{inr(insuranceResult.estimated_out_of_pocket)}</b></div></div>
            <div className="detail-panels"><div><h3>Assumptions</h3><ul>{insuranceResult.assumptions.map((item,i)=><li key={i}>{item}</li>)}</ul></div><div><h3>Things to verify</h3><ul>{insuranceResult.warnings.map((item,i)=><li key={i}>{item}</li>)}<li>Confirm final amounts and hospital network status with the insurer/hospital.</li></ul></div></div>
            <div className="unknown-note"><strong>Unknown</strong><span>The final hospital bill and insurer's final claim decision are not determined by this estimate.</span></div>
          </> : <div className="empty-result"><span className="empty-icon">₹</span><h3>Your estimate will appear here</h3><p>Known: entered amounts and the Demo Policy configuration.<br/>Estimated: insurer payable and out-of-pocket amount.<br/>Unknown: final bill and claim decision.</p></div>}
        </div>
      </div>
    </section>
    <footer className="page-footer"><span>CareCost AI <span className="footer-dot">·</span> A clearer view of care costs</span><span>Estimates are informational and are not a final hospital bill.</span></footer>
  </main></div>;
}
