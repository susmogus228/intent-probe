import { useEffect, useRef, useState, type ReactNode } from 'react';
import { DatabaseIcon } from '@phosphor-icons/react/dist/csr/Database';
import { ChartLineUpIcon } from '@phosphor-icons/react/dist/csr/ChartLineUp';
import { ChartBarIcon } from '@phosphor-icons/react/dist/csr/ChartBar';
import { CrosshairIcon } from '@phosphor-icons/react/dist/csr/Crosshair';
import { CubeIcon } from '@phosphor-icons/react/dist/csr/Cube';
import { FileTextIcon } from '@phosphor-icons/react/dist/csr/FileText';
import { ArrowRightIcon } from '@phosphor-icons/react/dist/csr/ArrowRight';
import { PlayIcon } from '@phosphor-icons/react/dist/csr/Play';
import { CopyIcon } from '@phosphor-icons/react/dist/csr/Copy';
import { InfoIcon } from '@phosphor-icons/react/dist/csr/Info';
import { TrashIcon } from '@phosphor-icons/react/dist/csr/Trash';
import { DownloadSimpleIcon } from '@phosphor-icons/react/dist/csr/DownloadSimple';
import { QuestionIcon } from '@phosphor-icons/react/dist/csr/Question';
import { GearIcon } from '@phosphor-icons/react/dist/csr/Gear';
import { CheckIcon } from '@phosphor-icons/react/dist/csr/Check';
import { api } from './api';
import type { Benchmark, Experiment, Metadata, Outcome, PolicyResult, Preview, Question, RankedProject, Session, SessionSummary } from './types';

type View = 'try' | 'workbench';
type Section = 'dataset' | 'train' | 'evaluate' | 'inspect';
const number = (value: number | null | undefined, digits = 3) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
const percent = (value: number | null | undefined) => typeof value === 'number' && Number.isFinite(value) ? `${number(value * 100,1)}%` : 'Not measured';
const isV2 = (model: Metadata['model']) => model.objective === 'constraint_aware';
const date = (value: string) => { const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(); };
const message = (error: unknown) => error instanceof Error ? error.message : 'An unexpected error occurred. Please retry.';
const icon = { size: 21, 'aria-hidden': true as const };

function Panel({title, subtitle, children, className = '', headingIcon, id}: {title?: string; subtitle?: string; children: ReactNode; className?: string; headingIcon?: ReactNode; id?: string}) {
  return <section id={id} className={`panel ${className}`}>{title && <h2>{headingIcon}{title}</h2>}{subtitle && <p className="panel-subtitle">{subtitle}</p>}{children}</section>;
}

export default function App() {
  const [view, setView] = useState<View>('try');
  const [section, setSection] = useState<Section>('train');
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [job, setJob] = useState<Experiment | null>(null);

  async function load() {
    setLoading(true); setError('');
    try {
      const [metadata, saved] = await Promise.all([api.meta(), api.sessions()]);
      setMeta(metadata); setBenchmark(Array.isArray(metadata.benchmark?.policies) ? metadata.benchmark : null); setSessions(saved);
      const stored = localStorage.getItem('intentprobe.session');
      if (stored && saved.some(item => item.id === stored)) setSession(await api.session(stored));
    } catch (e) { setError(message(e)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => { window.scrollTo({top: 0, behavior: 'instant'}); }, [view, section, session?.id]);
  useEffect(() => {
    if (!job || job.status !== 'running') return;
    let ignored = false;
    let polling = false;
    const timer = window.setInterval(() => {
      if (polling) return;
      polling = true;
      void api.job(job.id).then(async result => {
        if (ignored) return;
        if (result.status === 'completed') { const fresh = await api.benchmark(); if (!ignored) { setBenchmark(fresh); setNotice('Benchmark completed. The table and chart show the new run.'); } }
        if (!ignored) {
          setJob(result);
          if (result.status === 'failed') setError(result.error || 'The benchmark failed. The previous results are retained.');
        }
      }).catch(e => { if (!ignored) { setError(message(e)); setJob(null); } }).finally(() => { polling = false; });
    }, 1500);
    return () => { ignored = true; window.clearInterval(timer); };
  }, [job?.id, job?.status]);

  function acceptSession(next: Session) {
    setSession(next); localStorage.setItem('intentprobe.session', next.id);
    if (next.invalidated_answers > 0) setNotice(`Answer revised. ${next.invalidated_answers} later answer${next.invalidated_answers === 1 ? '' : 's'} removed; recommendations recalculated.`);
  }
  async function mutate(action: () => Promise<Session>) {
    if (busy) return false; setBusy(true); setError(''); setNotice('');
    try { acceptSession(await action()); setSessions(await api.sessions()); return true; }
    catch (e) { setError(message(e)); return false; }
    finally { setBusy(false); }
  }
  async function openSession(id: string) { await mutate(() => api.session(id)); setView('try'); }
  async function deleteSession(id: string) {
    if (busy) return; setBusy(true); setError('');
    try { await api.delete(id); setSessions(await api.sessions()); if (session?.id === id) { setSession(null); localStorage.removeItem('intentprobe.session'); } setNotice('Session deleted from local storage.'); }
    catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  function newSession() { setSession(null); localStorage.removeItem('intentprobe.session'); setNotice(''); setError(''); setView('try'); }
  async function runExperiment() {
    setError(''); setBusy(true);
    try { const result = await api.experiment(); setJob(result); if (result.status === 'completed') setBenchmark(await api.benchmark()); }
    catch (e) { setError(message(e)); } finally { setBusy(false); }
  }

  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="topbar">
      <a className="wordmark" href="#" onClick={e => { e.preventDefault(); setView('try'); }}>IntentProbe</a>
      <nav className="top-tabs" aria-label="Application views">
        <button className={view === 'try' ? 'active' : ''} aria-current={view === 'try' ? 'page' : undefined} onClick={() => setView('try')}>Try the model</button>
        <button className={view === 'workbench' ? 'active' : ''} aria-current={view === 'workbench' ? 'page' : undefined} onClick={() => setView('workbench')}>ML workbench</button>
      </nav>
      <span className="top-status"><span className="status-dot" />Local research lab</span>
    </header>
    <div className="app-shell">
      <aside className="sidebar">
        <nav aria-label={view === 'try' ? 'Session navigation' : 'Workbench navigation'}>
          {view === 'workbench' ? <>{([
            ['dataset', 'Dataset', DatabaseIcon], ['train', 'Train', ChartLineUpIcon], ['evaluate', 'Evaluate', ChartBarIcon], ['inspect', 'Inspect', CrosshairIcon],
          ] as const).map(([key, label, Icon]) => <button key={key} className={section === key ? 'selected' : ''} aria-current={section === key ? 'page' : undefined} onClick={() => setSection(key)}><Icon {...icon} />{label}</button>)}</> : <>
            <button className="selected" onClick={() => setView('try')}><QuestionIcon {...icon} />Current session</button>
            <button disabled={busy} onClick={newSession}><FileTextIcon {...icon} />New session</button>
          </>}
        </nav>
        <div className="sidebar-bottom"><p>Local-first · no AI API</p><a href="/docs" target="_blank" rel="noreferrer"><FileTextIcon size={17} aria-hidden />API documentation</a></div>
      </aside>
      <main id="main" tabIndex={-1}>
        {error && <div className="alert error" role="alert"><InfoIcon {...icon} /><div><strong>Something needs attention</strong><p>{error}</p>{!meta && <button onClick={() => void load()} disabled={loading}>Retry connection</button>}</div><button className="dismiss" onClick={() => setError('')} aria-label="Dismiss error">Dismiss</button></div>}
        {notice && <div className="alert success" role="status"><CheckIcon {...icon} /><span>{notice}</span><button className="dismiss" onClick={() => setNotice('')} aria-label="Dismiss notice">Dismiss</button></div>}
        {loading ? <div className="loading-state" role="status"><span className="spinner" />Loading model, dataset and saved sessions…</div> : meta ? <>
          {view === 'try' ? <TryModel meta={meta} session={session} sessions={sessions} busy={busy} mutate={mutate} openSession={openSession} deleteSession={deleteSession} newSession={newSession} /> : <Workbench meta={meta} section={section} benchmark={benchmark} session={session} busy={busy} job={job} runExperiment={runExperiment} openTry={() => setView('try')} setError={setError} />}
          <footer className="scope-footer">Controlled synthetic preferences · Research estimates, not verified human preferences · No automatic learning from your answers. <a href="/docs" target="_blank" rel="noreferrer">API documentation</a></footer>
        </> : <div className="empty-state"><DatabaseIcon size={36} aria-hidden /><h1>The lab is unavailable</h1><p>The Python server and a locally trained artifact are required. Start the server, then retry the connection.</p></div>}
      </main>
    </div>
  </>;
}

interface TryProps { meta: Metadata; session: Session | null; sessions: SessionSummary[]; busy: boolean; mutate: (action: () => Promise<Session>) => Promise<boolean>; openSession: (id: string) => Promise<void>; deleteSession: (id: string) => Promise<void>; newSession: () => void }
function TryModel({meta, session, sessions, busy, mutate, openSession, deleteSession, newSession}: TryProps) {
  const [initial, setInitial] = useState<Record<string, string>>({});
  const [note, setNote] = useState('');
  const [budget, setBudget] = useState(3);
  const primary = meta.questions.find(q => /time|duration|week/.test(q.id)) || meta.questions[0];
  const advanced = meta.questions.filter(q => q.id !== primary?.id);
  return <>
    <div className="page-heading"><div><span className="eyebrow">AN INSPECTABLE ML EXPERIMENT</span><h1>Find a project that fits.</h1><p>Answer a few useful questions. See what changes, and why.</p></div>{session && <button className="secondary" disabled={busy} onClick={newSession}>New session</button>}</div>
    <div className="scope-banner"><InfoIcon {...icon} /><span>A trained model chooses questions for a structured project catalog. This demo uses synthetic preference data.</span></div>
    <div className="try-grid">
      <div className="main-column">
        {!session ? <Panel title="Start with what you know" subtitle="Constraints are explicit. An unanswered field stays unknown.">
          <form onSubmit={e => { e.preventDefault(); void mutate(() => api.create({ initial_request: note, budget, policy: 'learned', facts: Object.fromEntries(Object.entries(initial).filter(([,v]) => v !== '')) })); }}>
            {primary && <FactSelect question={primary} value={initial[primary.id] || ''} onChange={value => setInitial({...initial, [primary.id]: value})} />}
            <details className="advanced"><summary>Optional constraints and preferences</summary><div className="form-grid">{advanced.map(q => <FactSelect key={q.id} question={q} value={initial[q.id] || ''} onChange={value => setInitial({...initial, [q.id]: value})} />)}</div></details>
            <label className="field">Context note <span className="optional">optional</span><textarea value={note} onChange={e => setNote(e.target.value)} placeholder="For example: a practical ML project for my portfolio" maxLength={1000} rows={2} /><span className="helper">Saved as a note only. Free text is not parsed or used by the model.</span></label>
            <label className="field budget-field">Maximum follow-up questions<select value={budget} onChange={e => setBudget(Number(e.target.value))}>{[1,2,3,4,5].map(n => <option key={n} value={n}>{n} question{n === 1 ? '' : 's'}</option>)}</select></label>
            <div className="form-actions"><button className="primary" disabled={busy} type="submit"><PlayIcon size={17} aria-hidden />{busy ? 'Starting…' : 'Start a session'}</button><span className="helper">Saved on this server. Delete any time.</span></div>
          </form>
        </Panel> : <>
          <div className="session-strip"><span className="badge">{session.status === 'active' ? 'Session active' : 'Questioning stopped'}</span><span>{session.questions_used} of {session.budget} follow-ups used</span><a className="export-link" href={`/api/sessions/${session.id}/export`} download><DownloadSimpleIcon size={16} aria-hidden />Export JSON</a></div>
          {session.initial_request && <p className="context-note"><strong>Your note</strong> {session.initial_request}</p>}
          <QuestionCard session={session} busy={busy} mutate={mutate} />
          <FactsPanel meta={meta} session={session} busy={busy} mutate={mutate} />
        </>}
        <SavedSessions sessions={sessions} currentId={session?.id} busy={busy} open={openSession} remove={deleteSession} />
      </div>
      <div className="right-column">
        <Panel id="current-shortlist" title={session ? 'Your current outcome' : 'What you will get'} subtitle={session ? 'Question selection and constraint verification are separate. An unverified candidate is not a confirmed recommendation.' : 'A visible question policy, explicit constraint checks, and an editable answer history.'} headingIcon={<CrosshairIcon {...icon} />}>
          {session ? <><OutcomeSummary outcome={session.outcome} projects={session.ranked_projects} questions={meta.questions} /><Ranking projects={session.ranked_projects} outcome={session.outcome} /></> : <div className="how-it-works">{[['01', 'Set a starting point', 'Tell us your time limit and any constraints you already know.'], ['02', 'Answer with intent', 'The model estimates which question could improve the recommendation.'], ['03', 'Inspect the outcome', 'Get a verified catalog recommendation, no suitable option, or an explicit request for confirmation.']].map(([n,t,d]) => <div key={n}><span className="step-number">{n}</span><div><h3>{t}</h3><p>{d}</p></div></div>)}</div>}
        </Panel>
        <ModelArtifact meta={meta} compact />
      </div>
    </div>
  </>;
}

function FactSelect({question, value, onChange}: {question: Question; value: string; onChange: (v: string) => void}) {
  return <label className="field">{question.title}<select value={value} onChange={e => onChange(e.target.value)}><option value="">Not specified yet</option>{question.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select>{question.description && <span className="helper">{question.description}</span>}</label>;
}

function QuestionCard({session, busy, mutate}: {session: Session; busy: boolean; mutate: TryProps['mutate']}) {
  const q = session.next_question;
  const [selected, setSelected] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const requestVersion = useRef(0);
  useEffect(() => {
    requestVersion.current++;
    setSelected(''); setPreview(null); setPreviewBusy(false); setPreviewError('');
    return () => { requestVersion.current++; };
  }, [session.id, session.revision]);
  async function showPreview() {
    if (!q || !selected) return;
    const version = ++requestVersion.current; setPreviewBusy(true); setPreviewError('');
    try { const result = await api.preview(session.id, {question_id: q.id, value: selected, expected_revision: session.revision}); if (version === requestVersion.current) setPreview(result); }
    catch (e) { if (version === requestVersion.current) setPreviewError(message(e)); }
    finally { if (version === requestVersion.current) setPreviewBusy(false); }
  }
  if (!q || session.status === 'stopped') return <Panel title={session.outcome?.status === 'needs_confirmation' ? 'More information is needed' : session.outcome?.status === 'no_feasible' ? 'No suitable project in this catalog' : 'Your current recommendation'} headingIcon={<InfoIcon {...icon} />}><p className="decision-reason">{session.decision.reason}</p><p className="helper">{session.outcome?.status === 'needs_confirmation' ? 'Review the unchecked limits below. Revise a recorded answer, or start a new session to supply an unasked constraint.' : session.outcome?.status === 'no_feasible' ? 'Review the conflicts below. You can revise a recorded limit; the model keeps your constraints until you change them.' : 'The outcome below separates catalog constraint checks from estimated fit. You can revise a recorded answer to explore alternatives.'}</p><a className="shortlist-jump" href="#current-shortlist">Review the outcome</a></Panel>;
  return <Panel className="question-card">
    <div className="question-top"><span className="eyebrow">NEXT USEFUL QUESTION</span><span className="badge">{session.policy === 'learned' ? 'Learned policy' : `${session.policy.replaceAll('_', ' ')} policy`}</span></div>
    <fieldset disabled={busy}><legend>{q.title}</legend><p className="question-description">{q.description}</p><div className="answer-options">{q.options.map(option => <label key={option.value} className={`answer-option ${selected === option.value ? 'checked' : ''}`}><input type="radio" name="answer" value={option.value} checked={selected === option.value} onChange={() => { requestVersion.current++; setSelected(option.value); setPreview(null); setPreviewBusy(false); setPreviewError(''); }} /><span>{option.label}</span></label>)}</div></fieldset>
    <div className="why-question"><InfoIcon size={18} aria-hidden /><div><strong>Why ask this?</strong><p>{q.reason || session.decision.reason}</p>{typeof q.estimated_gain === 'number' && <p className="helper">Estimated decision value: <strong>{number(q.estimated_gain, 4)}</strong>. A model estimate, not a probability.</p>}</div></div>
    <div className="button-row"><button className="primary" disabled={busy || !selected} onClick={() => void mutate(() => api.answer(session.id, {question_id: q.id, value: selected, skip: false, expected_revision: session.revision}))}>{busy ? 'Applying…' : 'Apply answer'}<ArrowRightIcon size={17} aria-hidden /></button><button className="secondary" disabled={busy || !selected || previewBusy} onClick={() => void showPreview()}>{previewBusy ? 'Calculating…' : 'Preview answer'}</button><button className="text-button" disabled={busy} onClick={() => void mutate(() => api.answer(session.id, {question_id: q.id, value: null, skip: true, expected_revision: session.revision}))}>Skip question</button></div>
    {previewError && <p className="inline-error" role="alert">{previewError}</p>}
    {preview && <div className="preview-panel" aria-live="polite"><span className="badge warning">Hypothetical · not applied</span><h3>If you answer: {q.options.find(o => o.value === selected)?.label}</h3><p className="helper">Your confirmed answers have not changed.</p><OutcomeSummary outcome={preview.outcome} projects={preview.ranked_projects} hypothetical /><Ranking projects={preview.ranked_projects} outcome={preview.outcome} compact /></div>}
    <div className="stop-row"><span>Stop with the information available. Unchecked limits stay unverified.</span><button className="text-button" disabled={busy} onClick={() => void mutate(() => api.stop(session))}>Stop asking</button></div>
  </Panel>;
}

function OutcomeSummary({outcome, projects, questions = [], hypothetical = false}: {outcome?: Outcome; projects: RankedProject[]; questions?: Question[]; hypothetical?: boolean}) {
  const confirmed = outcome?.status === 'recommendation' && projects.some(project => project.id === outcome.project_id && project.constraint_status === 'verified');
  const title = confirmed ? 'Recommendation checked against catalog constraints' : outcome?.status === 'no_feasible' ? 'No suitable project in this catalog' : 'Needs constraint confirmation';
  return <div className={`outcome-summary ${confirmed ? 'verified' : 'pending'}`} role="status">
    <strong>{hypothetical ? 'Hypothetical outcome: ' : ''}{title}</strong>
    <p>{confirmed ? 'This project fits the supported limits in this catalog, including conservative checks for limits you have not specified.' : outcome?.status === 'no_feasible' ? 'No project in this catalog fits the limits you supplied. Review a limit or keep this result.' : 'Some limits are still unknown. Confirm the items below before relying on these candidates.'}</p>
    {outcome && outcome.unchecked_constraints.length > 0 && <div><span className="helper">Unchecked constraints</span><ul>{outcome.unchecked_constraints.map(id => <li key={id}>{questions.find(question => question.id === id)?.title || id}</li>)}</ul></div>}
    {outcome?.guard_applied && <p className="helper">Checked against catalog requirements. Accurate answers matter; this does not guarantee project success.</p>}
    {outcome && <details><summary>Inspect the constraint check</summary><p className="helper">{outcome.reason}</p></details>}
    {!hypothetical && !confirmed && <a href="#known-facts">Review or revise recorded answers</a>}
  </div>;
}

function projectStatus(project: RankedProject, outcome?: Outcome) {
  if (outcome?.status === 'recommendation' && outcome.project_id === project.id && project.constraint_status === 'verified') return 'Confirmed recommendation';
  if (project.constraint_status === 'conflict' || !project.feasible) return 'Constraint conflict';
  if (project.constraint_status === 'verified') return 'Constraints verified · alternative';
  return 'Preliminary candidate · unverified';
}

function Ranking({projects, outcome, compact = false}: {projects: RankedProject[]; outcome?: Outcome; compact?: boolean}) {
  if (!projects.length) return <p className="empty-note">No project estimates are available.</p>;
  return <div className={`ranking ${compact ? 'compact' : ''}`}>
    <p className="score-note">Fit is estimated synthetic utility on a 0–1 scale. It is not a probability of success.</p>
    {projects.slice(0, compact ? 3 : 4).map((project, index) => <article key={project.id} className={`project-card ${!project.feasible ? 'infeasible' : ''}`}><div className="project-title"><span className="rank-number">{String(index + 1).padStart(2,'0')}</span><h3>{project.title}</h3><span className="fit-value">{number(project.fit_score, 2)}<small> fit</small></span></div><p>{project.summary}</p><div className="tags"><span className={`badge ${project.constraint_status === 'verified' ? '' : 'warning'}`}>{projectStatus(project,outcome)}</span>{project.tags.slice(0,3).map(tag => <span key={tag} className="tag">{tag}</span>)}</div>{project.reasons.length > 0 && <ul className="reasons">{project.reasons.map((reason,i) => <li key={i}>{reason}</li>)}</ul>}</article>)}
    {projects.length > (compact ? 3 : 4) && <details className="more-projects"><summary>Inspect all {projects.length} catalog projects</summary>{projects.slice(compact ? 3 : 4).map(project => <article className="remaining-project" key={project.id}><h3>{project.title} <span className="helper">{number(project.fit_score,2)} fit · {projectStatus(project,outcome)}</span></h3><p>{project.summary}</p><ul className="reasons">{project.reasons.map((r,i) => <li key={i}>{r}</li>)}</ul></article>)}</details>}
  </div>;
}

function FactsPanel({meta, session, busy, mutate}: {meta: Metadata; session: Session; busy: boolean; mutate: TryProps['mutate']}) {
  const [editing, setEditing] = useState('');
  const [value, setValue] = useState('');
  const [skip, setSkip] = useState(false);
  useEffect(() => { setEditing(''); setValue(''); setSkip(false); }, [session.id, session.revision]);
  const order = [...Object.keys(session.initial_facts), ...session.answers.map(a => a.question_id)];
  const skipped = new Set(session.answers.filter(a => a.skipped).map(a => a.question_id));
  return <Panel id="known-facts" title="What the model knows" subtitle="An unspecified preference, an explicit “unknown” answer and a skipped question are different states.">
    <div className="facts-list">{meta.questions.map(q => {
      const known = q.id in session.facts; const wasSkipped = skipped.has(q.id); const editable = order.includes(q.id);
      const label = known ? q.options.find(o => o.value === session.facts[q.id])?.label || session.facts[q.id] : wasSkipped ? 'Skipped' : 'Not asked / unspecified';
      return <div className="fact-row" key={q.id}><div><strong>{q.title}</strong><span className={known ? 'fact-value' : 'muted'}>{label}</span></div>{editable && <button className="text-button" disabled={busy} aria-expanded={editing === q.id} onClick={() => { setEditing(editing === q.id ? '' : q.id); setValue(session.facts[q.id] || q.options[0]?.value || ''); setSkip(wasSkipped); }}>Edit</button>}
        {editing === q.id && <form className="edit-answer" onSubmit={e => { e.preventDefault(); void mutate(() => api.revise(session.id, q.id, { value: skip ? null : value, skip, expected_revision: session.revision })).then(success => { if (success) setEditing(''); }); }}><label className="field">Corrected answer<select value={value} disabled={skip || busy} onChange={e => setValue(e.target.value)}>{q.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label><label className="checkbox-label"><input type="checkbox" checked={skip} onChange={e => setSkip(e.target.checked)} disabled={busy || q.id in session.initial_facts} />Mark as skipped</label><p className="helper">Revising this answer removes later follow-up answers and recomputes the decision. Initial constraints stay recorded.</p><div className="button-row"><button type="submit" className="primary" disabled={busy}>Save revision</button><button type="button" className="secondary" onClick={() => setEditing('')}>Cancel</button></div></form>}
      </div>;
    })}</div>
    {session.answers.length > 0 && <details className="answer-history"><summary>Answer history ({session.answers.length})</summary><ol>{session.answers.map((answer,i) => { const q = meta.questions.find(item => item.id === answer.question_id); return <li key={`${answer.question_id}-${i}`}><strong>{q?.title || answer.question_id}</strong><span>{answer.skipped ? 'Skipped' : q?.options.find(o => o.value === answer.value)?.label || answer.value}</span></li>; })}</ol></details>}
  </Panel>;
}

function SavedSessions({sessions,currentId,busy,open,remove}: {sessions: SessionSummary[]; currentId?: string; busy: boolean; open: (id: string) => Promise<void>; remove: (id: string) => Promise<void>}) {
  const [confirmId, setConfirmId] = useState('');
  return <Panel title="Saved on this server" subtitle="No account required. Sessions persist between server restarts."><div className="saved-list">{sessions.length ? sessions.map(item => <div className="saved-row" key={item.id}><button className="saved-open" disabled={busy} onClick={() => void open(item.id)} aria-current={currentId === item.id ? 'true' : undefined}><strong>{item.initial_request || `Session ${item.id.slice(0,8)}`}</strong><span>{date(item.updated_at)} · {item.status}{currentId === item.id ? ' · current' : ''}</span></button><a className="icon-button" href={`/api/sessions/${item.id}/export`} download aria-label={`Export session ${item.id.slice(0,8)}`}><DownloadSimpleIcon size={19} aria-hidden /></a><button className="icon-button" disabled={busy} aria-label={`Delete session ${item.id.slice(0,8)}`} onClick={() => setConfirmId(confirmId === item.id ? '' : item.id)}><TrashIcon size={19} aria-hidden /></button>{confirmId === item.id && <div className="delete-confirm"><span>Delete this saved session permanently?</span><button className="danger" disabled={busy} onClick={() => { void remove(item.id); setConfirmId(''); }}>Delete session</button><button className="secondary" onClick={() => setConfirmId('')}>Cancel</button></div>}</div>) : <p className="empty-note">No sessions yet. Start one above to save your answers locally.</p>}</div></Panel>;
}

function ModelArtifact({meta, compact = false}: {meta: Metadata; compact?: boolean}) {
  return <Panel title="Model artifact" headingIcon={<CubeIcon {...icon} />}><div className="artifact-state"><span className="badge">Trained locally</span><h3>{meta.model.estimator}</h3><p className="mono">{meta.model.version}</p></div><dl className="key-values"><div><dt>Training rows</dt><dd>{meta.model.training_rows.toLocaleString()}</dd></div><div><dt>Validation MAE</dt><dd>{number(meta.model.validation_mae,4)}</dd></div>{!compact && <div><dt>Trained</dt><dd>{date(meta.model.trained_at)}</dd></div>}</dl><details className="provenance"><summary>Artifact provenance</summary><p className="helper">SHA-256</p><code className="hash">{meta.model.artifact_sha256}</code><p className="helper">Features ({meta.model.feature_names.length})</p><p className="mono small-text">{meta.model.feature_names.join(', ')}</p></details><p className="helper">Predicts question value on controlled profiles. Your answers do not retrain this model.</p></Panel>;
}

function Workbench({meta,section,benchmark,session,busy,job,runExperiment,openTry,setError}: {meta: Metadata; section: Section; benchmark: Benchmark | null; session: Session | null; busy: boolean; job: Experiment | null; runExperiment: () => Promise<void>; openTry: () => void; setError: (value:string) => void}) {
  const [copied,setCopied] = useState(false);
  const [protocolOpen,setProtocolOpen] = useState(false);
  const lossAware = isV2(meta.model);
  const command = typeof meta.protocol === 'object' && typeof meta.protocol.training_command === 'string' ? meta.protocol.training_command : meta.model.training_command || (lossAware ? 'python -m intentprobe.ml.train_v2 --output artifacts/v2' : 'python -m intentprobe.ml.train --output artifacts');
  const headings: Record<Section,[string,string]> = {
    train: ['Learn which question is worth asking.', 'Compare a trained question policy with fixed and analytic baselines.'],
    dataset: ['Start with inspectable data.', 'Controlled preference profiles with disjoint training, validation and test splits.'],
    evaluate: ['Measure the value of a question.', 'Held-out synthetic evaluation against simple and strong baselines.'],
    inspect: ['Follow a decision from the inside.', 'Inspect observed facts, predicted question values and the resulting shortlist.'],
  };
  async function copyCommand() { try { await navigator.clipboard.writeText(command); setCopied(true); } catch { setError('Clipboard access is unavailable. Select and copy the training command below.'); } }
  return <>
    <div className="workbench-grid">
      <div className="main-column">
        <div className="page-heading workbench-heading"><div><h1>{headings[section][0]}</h1><p>{headings[section][1]}</p></div></div>
        <div className="scope-banner"><InfoIcon {...icon} /><span>Trained artifact · Measured synthetic benchmark · Human usefulness has not been established</span></div>
        {section === 'train' && <>
          <Panel title="Training pipeline" subtitle="From controlled profiles to a learned estimate of question value."><div className="pipeline">{[[FileTextIcon,'Profiles','Synthetic preferences and constraints'],[QuestionIcon,'Question outcomes','Observed answers and utility changes'],[GearIcon,'Value model','Predict the value of each question'],[ChartBarIcon,'Held-out evaluation',`Compare with ${benchmark?.policies.length || 'available'} question policies`]].map(([Icon,title,description],i) => { const StepIcon = Icon as typeof FileTextIcon; return <div className="pipeline-stage" key={String(title)}><div className="pipeline-card"><StepIcon {...icon} /><h3>{String(title)}</h3><p>{String(description)}</p></div>{i < 3 && <ArrowRightIcon className="pipeline-arrow" size={20} aria-hidden />}</div>; })}</div></Panel>
          <RunConfiguration meta={meta} />
        </>}
        {section === 'dataset' && <><RunConfiguration meta={meta} /><Panel title="Data boundaries" subtitle="What these measurements can and cannot support."><ul className="limitations">{meta.dataset.limitations.map((text,i) => <li key={i}>{text}</li>)}</ul><dl className="key-values"><div><dt>Generator</dt><dd className="mono">{meta.dataset.generator_version}</dd></div><div><dt>Split seed</dt><dd>{meta.dataset.split_seed}</dd></div><div><dt>Profile overlap</dt><dd>{meta.dataset.splits_disjoint ? 'None across splits' : 'Warning: overlap reported'}</dd></div></dl></Panel><Panel title="Versioned question bank" subtitle="Only explicit structured answers are used as model inputs."><div className="question-bank">{meta.questions.map(q => <details key={q.id}><summary>{q.title}</summary><p>{q.description}</p><ul>{q.options.map(o => <li key={o.value}>{o.label} <code>{o.value}</code></li>)}</ul></details>)}</div></Panel></>}
        {section === 'inspect' && <Panel title="Predicted question values" subtitle="Estimates for the current observed state; hidden synthetic preferences are never exposed to the session policy.">{session ? <><p className="decision-reason">{session.decision.reason}</p><div className="table-wrap"><table><caption className="sr-only">Estimated value of each question</caption><thead><tr><th>Question</th><th>Estimated gain</th></tr></thead><tbody>{session.question_values.map(q => <tr key={q.question_id}><th scope="row">{q.title}</th><td className="numeric">{number(q.estimated_gain,5)}</td></tr>)}</tbody></table></div>{session.question_values.length === 0 && <p className="empty-note">No unanswered questions remain in this state.</p>}<p className="helper">Session revision {session.revision} · {session.questions_used} questions used · Policy: {session.policy} · Model: {session.model_version}</p></> : <div className="empty-state compact-empty"><CrosshairIcon size={32} aria-hidden /><h3>No session selected</h3><p>Start or reopen a session in Try the model to inspect its actual state.</p><button className="primary" onClick={openTry}>Try the model</button></div>}</Panel>}
        {(section === 'train' || section === 'evaluate') && <Panel className={section === 'train' ? 'training-comparison' : ''} title="Raw policy comparison" subtitle="Question policy before the separate constraint guard. Lower regret is better; hidden-constraint violations remain visible.">
          {benchmark ? <><p className="benchmark-scope">{benchmark.scope}</p><div className="table-wrap"><table className="comparison-table"><caption className="sr-only">Held-out policy benchmark results</caption><thead><tr><th>Policy</th><th>Mean regret <small>95% interval</small></th><th>Questions</th><th>Constraint violations</th></tr></thead><tbody>{benchmark.policies.map(p => <tr key={p.id} className={p.id === 'learned' ? 'highlight-row' : ''}><th scope="row">{p.label}{p.id === 'learned' && <span className="table-badge">Trained model</span>}</th><td className="numeric">{number(p.mean_regret)}<small>[{number(p.ci_low)}, {number(p.ci_high)}]</small></td><td className="numeric">{number(p.mean_questions,2)}</td><td className="numeric">{number(p.constraint_violation_rate * 100,1)}%</td></tr>)}</tbody></table></div><p className="helper">Run: {date(benchmark.generated_at)} · Model {benchmark.model_version}</p></> : <p className="empty-note">No benchmark report is available yet. Run the frozen experiment to produce real results.</p>}
          <div className="button-row"><button className="primary" disabled={busy || job?.status === 'running'} onClick={() => void runExperiment()}><PlayIcon size={17} aria-hidden />{job?.status === 'running' ? 'Experiment running…' : 'Run experiment'}</button><button className="text-button" onClick={() => setProtocolOpen(!protocolOpen)} aria-expanded={protocolOpen}><FileTextIcon size={18} aria-hidden />{protocolOpen ? 'Hide protocol' : 'View protocol'}</button></div>
          {job && <p className={job.status === 'failed' ? 'inline-error' : 'helper'} role="status">Experiment {job.id.slice(0,8)} · {job.status}{job.error ? ` · ${job.error}` : ''}</p>}
          {protocolOpen && <Protocol protocol={meta.protocol} />}
        </Panel>}
        {(section === 'evaluate' || section === 'train') && benchmark && <RegretChart benchmark={benchmark} />}
        {section === 'evaluate' && benchmark && benchmark.policies.some(policy => typeof policy.mean_total_loss === 'number') && <Panel title="Measured decision loss" subtitle={lossAware ? 'Loss = regret + invalid-recommendation penalty + false-no-feasible penalty + 0.006 × questions.' : 'Loss = recommendation regret + 0.006 × questions asked.'}><p className="helper">Lower is better. V2 loss averages all cases, including profiles with no feasible brief; regret above averages feasible profiles. Penalties and question cost are synthetic assumptions. Compare raw and guarded outcomes separately.</p><LossTable policies={benchmark.policies} caption="Raw policy decision loss" constraintAware={lossAware} />{benchmark.guarded_policies && <><h3>After the constraint guard</h3><LossTable policies={benchmark.guarded_policies} caption="Guarded policy decision loss" constraintAware={lossAware} /></>}</Panel>}
        {section === 'evaluate' && benchmark && <Panel title="Risk and recommendation coverage" subtitle="The learned policy and the separate constraint guard are evaluated independently."><p className="helper">Recommendation risk is the fraction of issued recommendations that violate a full hidden constraint. Feasible coverage is the fraction of truly feasible profiles that receive a valid recommendation. A method can reduce risk by declining to recommend; coverage shows that trade-off.</p><h3>Raw policy outcomes</h3><ReliabilityTable policies={benchmark.policies} caption="Raw policy risk, coverage and feasibility outcomes" />{benchmark.guarded_policies?.length ? <><h3>After the constraint guard</h3><ReliabilityTable policies={benchmark.guarded_policies} caption="Guarded policy risk, coverage and feasibility outcomes" /></> : <p className="helper">No separate guarded evaluation is included in this report.</p>}<p className="helper">No-feasible detection is evaluated only on profiles with no suitable brief; false-no-feasible rate is evaluated on truly feasible profiles. Regret excludes no-feasible profiles. {lossAware ? 'The v2 objective penalizes invalid recommendations and false no-feasible outcomes. Unconfirmed cases remain explicit abstentions; the guard is a rule check, not learned intelligence.' : 'This v1 training target does not independently reward discovering infeasible profiles.'}</p></Panel>}
        {section === 'evaluate' && benchmark && <Panel title="Stress tests" subtitle="Additional controlled conditions, reported separately from the main test.">{benchmark.stress_tests.length ? benchmark.stress_tests.map(test => <details className="stress-test" key={test.name}><summary>{test.name}</summary><p>{test.description}</p><div className="table-wrap"><table><thead><tr><th>Policy</th><th>Mean regret</th></tr></thead><tbody>{test.results.map(result => <tr key={result.policy}><th scope="row">{benchmark.policies.find(p => p.id === result.policy)?.label || result.policy}</th><td className="numeric">{number(result.mean_regret)}</td></tr>)}</tbody></table></div></details>) : <p className="empty-note">No stress-test runs are included in this report. See the benchmark notes for this limitation.</p>}<ul className="limitations">{benchmark.notes.map((note,i) => <li key={i}>{note}</li>)}</ul></Panel>}
      </div>
      <div className="right-column"><Panel title="Inspect a decision" subtitle="A real observed state from your local session." headingIcon={<CrosshairIcon {...icon} />}>
        {session ? <><div className="inspect-request"><span className="helper">Context note · not parsed</span><p>{session.initial_request || 'No context note supplied.'}</p><div className="tags">{Object.entries(session.facts).map(([id,value]) => <span className="badge" key={id}>{meta.questions.find(q => q.id === id)?.options.find(o => o.value === value)?.label || value}</span>)}{Object.keys(session.facts).length === 0 && <span className="badge">No facts specified</span>}</div></div><p className="inspect-label">{session.next_question ? 'Proposed question (from the selected policy)' : 'Decision'}</p><div className="proposed-question">{session.next_question?.title || 'Stop asking'}</div><p>{session.next_question?.reason || session.decision.reason}</p>{session.next_question && <div className="inspect-options">{session.next_question.options.map(o => <div key={o.value}>{o.label}</div>)}</div>}<hr /><h3>Learned estimate: decision value</h3><p className="helper">The model estimates how much asking can reduce the training objective in this state. For v2 this includes decision errors and question cost. The estimate is not a certainty or a success probability.</p><button className="secondary" onClick={openTry}>Open this session<ArrowRightIcon size={17} aria-hidden /></button></> : <div className="empty-state compact-empty"><QuestionIcon size={32} aria-hidden /><h3>Inspect your own session</h3><p>Start a session to see the proposed question, estimated value and confirmed facts here.</p><button className="secondary" onClick={openTry}>Try the model<ArrowRightIcon size={17} aria-hidden /></button></div>}
      </Panel><ModelArtifact meta={meta} /><details className="training-reproduction"><summary>Reproduce training in your terminal</summary><Panel title="Reproduce training" subtitle="Use the versioned generator and fixed split seed."><div className="command"><code>{command}</code><button className="icon-button" aria-label="Copy training command" onClick={() => void copyCommand()}>{copied ? <CheckIcon {...icon} /> : <CopyIcon {...icon} />}</button></div>{copied && <p className="helper" role="status">Command copied.</p>}<p className="helper">Run from the project root in the activated Python environment. Run experiment reruns evaluation only; it does not retrain the model.</p></Panel></details>{section === 'inspect' && session && <Panel title="Current outcome"><OutcomeSummary outcome={session.outcome} projects={session.ranked_projects} questions={meta.questions} /><Ranking projects={session.ranked_projects} outcome={session.outcome} compact /></Panel>}</div>
    </div>
  </>;
}

function LossTable({policies,caption,constraintAware}: {policies: PolicyResult[]; caption: string; constraintAware: boolean}) {
  return <div className="table-wrap"><table><caption className="sr-only">{caption}</caption><thead><tr><th>Policy</th><th>Mean loss<small>{constraintAware ? 'All cases' : 'Feasible cases'}</small></th><th>95% interval</th></tr></thead><tbody>{policies.map(policy => {
    const mean = constraintAware ? policy.mean_objective_with_cost : policy.mean_total_loss;
    const low = constraintAware ? policy.objective_ci_low : policy.total_loss_ci_low;
    const high = constraintAware ? policy.objective_ci_high : policy.total_loss_ci_high;
    return <tr key={policy.id} className={policy.id === 'learned' ? 'highlight-row' : ''}><th scope="row">{policy.label}</th><td className="numeric">{number(mean,4)}</td><td className="numeric">{typeof low === 'number' && typeof high === 'number' ? `[${number(low,4)}, ${number(high,4)}]` : 'Not measured'}</td></tr>;
  })}</tbody></table></div>;
}

function ReliabilityTable({policies,caption}: {policies: PolicyResult[]; caption: string}) {
  const selective = policies.some(policy => 'recommendation_risk' in policy || 'feasible_coverage' in policy);
  return <div className="table-wrap"><table className="comparison-table"><caption className="sr-only">{caption}</caption><thead><tr><th>Policy</th>{selective && <><th>Recommendation risk<small>Among recommendations</small></th><th>Feasible coverage<small>Valid / feasible profiles</small></th><th>Recommendation rate<small>Among all profiles</small></th><th>False no-feasible<small>Among feasible profiles</small></th></>}<th>Hidden violations<small>Among all profiles</small></th><th>No-feasible detection<small>Among infeasible profiles</small></th></tr></thead><tbody>{policies.map(policy => <tr key={policy.id} className={policy.id === 'learned' ? 'highlight-row' : ''}><th scope="row">{policy.label}</th>{selective && <><td className="numeric">{policy.recommendation_risk === null ? 'No recommendations' : percent(policy.recommendation_risk)}</td><td className="numeric">{percent(policy.feasible_coverage)}</td><td className="numeric">{percent(policy.recommendation_rate)}</td><td className="numeric">{percent(policy.false_no_feasible_rate)}</td></>}<td className="numeric">{percent(policy.constraint_violation_rate)}</td><td className="numeric">{percent(policy.no_feasible_detection_rate)}</td></tr>)}</tbody></table></div>;
}

function RunConfiguration({meta}: {meta: Metadata}) {
  return <Panel title="Run configuration"><div className="run-config"><dl className="configuration-list"><div><DatabaseIcon {...icon} /><dt>Data</dt><dd>Controlled synthetic profiles</dd></div><div><CrosshairIcon {...icon} /><dt>Target</dt><dd>{isV2(meta.model) ? 'Reduction in decision loss, including constraint errors' : 'Reduction in recommendation regret'}</dd></div><div><CubeIcon {...icon} /><dt>Model</dt><dd>{meta.model.estimator}</dd></div><div><GearIcon {...icon} /><dt>Split seed</dt><dd>{meta.dataset.split_seed}</dd></div></dl><div className="split-panel"><h3>Data split · profiles</h3><div className="split-blocks"><div><strong>{meta.dataset.train_profiles.toLocaleString()}</strong><span>Train</span></div><div><strong>{meta.dataset.validation_profiles.toLocaleString()}</strong><span>Validation</span></div><div><strong>{meta.dataset.test_profiles.toLocaleString()}</strong><span>{isV2(meta.model) ? 'Final audit' : 'Test'}</span></div></div><p className="helper">All states from one profile stay in the same split.{typeof meta.dataset.development_profiles === 'number' && ` The ${meta.dataset.development_profiles} historical test profiles now serve as diagnostics; they are separate from this final audit.`}</p></div></div></Panel>;
}

function Protocol({protocol}: {protocol: Metadata['protocol']}) {
  const render = (value: unknown): ReactNode => {
    if (typeof value === 'string') return /^https?:\/\//.test(value) ? <a href={value} target="_blank" rel="noreferrer">{value}</a> : value;
    if (Array.isArray(value)) return <ul>{value.map((item,i) => <li key={i}>{render(item)}</li>)}</ul>;
    if (value && typeof value === 'object') return <dl>{Object.entries(value).map(([key,item]) => <div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{render(item)}</dd></div>)}</dl>;
    return String(value ?? 'Not specified');
  };
  return <div className="protocol-content"><h3>Evaluation protocol</h3>{render(protocol)}</div>;
}

function RegretChart({benchmark}: {benchmark: Benchmark}) {
  const curves = benchmark.curves.filter(point => Number.isFinite(point.mean_regret) && Number.isFinite(point.budget));
  const ids = [...new Set(curves.map(point => point.policy))];
  const colors = ['#0755ee','#697890','#9b6500','#087f73','#7a4eb1','#b24d57'];
  const maxBudget = Math.max(1,...curves.map(point => point.budget));
  const maxRegret = Math.max(0.01,...curves.map(point => point.mean_regret)) * 1.1;
  const x = (budget: number) => 58 + budget / maxBudget * 604;
  const y = (regret: number) => 238 - regret / maxRegret * 202;
  return <Panel title="Regret by question budget" subtitle="A lower curve means a smaller gap to the best project under the held-out synthetic profile.">
    {curves.length ? <><svg className="regret-chart" viewBox="0 0 700 285" role="img" aria-labelledby="regret-title regret-description"><title id="regret-title">Held-out regret by maximum question budget</title><desc id="regret-description">{ids.map(id => `${benchmark.policies.find(p => p.id === id)?.label || id}: ${curves.filter(p => p.policy === id).map(p => `budget ${p.budget}, regret ${number(p.mean_regret)}`).join('; ')}`).join('. ')}</desc>{[0,1,2,3,4].map(i => { const val = maxRegret*i/4; return <g key={i}><line x1="58" x2="662" y1={y(val)} y2={y(val)} className="chart-grid" /><text x="46" y={y(val)+4} textAnchor="end">{number(val,2)}</text></g>; })}{Array.from({length: maxBudget+1},(_,budget) => <text key={budget} x={x(budget)} y="259" textAnchor="middle">{budget}</text>)}{ids.map((id,index) => { const values = curves.filter(p => p.policy === id).sort((a,b) => a.budget-b.budget); return <g key={id}><polyline points={values.map(p => `${x(p.budget)},${y(p.mean_regret)}`).join(' ')} fill="none" stroke={colors[index % colors.length]} strokeWidth={id === 'learned' ? 3 : 2} strokeDasharray={index > 2 ? '5 4' : undefined} />{values.map(p => <circle key={p.budget} cx={x(p.budget)} cy={y(p.mean_regret)} r="3" fill={colors[index % colors.length]} />)}</g>; })}<text x="360" y="282" textAnchor="middle">Maximum follow-up questions</text></svg><div className="chart-legend">{ids.map((id,index) => <span key={id}><span className="legend-swatch" style={{backgroundColor:colors[index % colors.length]}} />{benchmark.policies.find(p => p.id === id)?.label || id}</span>)}</div><details className="chart-data"><summary>View chart values as a table</summary><div className="table-wrap"><table><thead><tr><th>Policy</th><th>Budget</th><th>Mean regret</th></tr></thead><tbody>{curves.map(p => <tr key={`${p.policy}-${p.budget}`}><th scope="row">{benchmark.policies.find(item => item.id === p.policy)?.label || p.policy}</th><td>{p.budget}</td><td>{number(p.mean_regret,4)}</td></tr>)}</tbody></table></div></details></> : <p className="empty-note">No budget-curve measurements are available for this run.</p>}
  </Panel>;
}
