import type { Benchmark, Experiment, Metadata, Preview, Session, SessionSummary } from './types';

async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch { throw new Error('Cannot reach the local server. Check that IntentProbe is running, then retry.'); }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((x: {msg?: string}) => x.msg).join('; ') : `Request failed (${response.status}).`;
    throw new Error(response.status === 409 ? `${message} Reopen the saved session to refresh its state.` : message);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export const api = {
  meta: () => request<Metadata>('/meta'), benchmark: () => request<Benchmark>('/benchmark'),
  sessions: () => request<SessionSummary[]>('/sessions'), session: (id: string) => request<Session>(`/sessions/${id}`),
  create: (body: unknown) => request<Session>('/sessions', 'POST', body),
  answer: (id: string, body: unknown) => request<Session>(`/sessions/${id}/answers`, 'POST', body),
  revise: (id: string, question: string, body: unknown) => request<Session>(`/sessions/${id}/answers/${question}`, 'PATCH', body),
  preview: (id: string, body: unknown) => request<Preview>(`/sessions/${id}/preview`, 'POST', body),
  stop: (session: Session) => request<Session>(`/sessions/${session.id}/stop`, 'POST', {expected_revision: session.revision}),
  delete: (id: string) => request<void>(`/sessions/${id}`, 'DELETE'),
  experiment: () => request<Experiment>('/experiments', 'POST', {}),
  job: (id: string) => request<Experiment>(`/experiments/${id}`),
};
