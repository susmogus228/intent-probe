# Browser and integration verification inventory

Approved reference: docs/design/approved-workbench.png. Default view: Try the model. Workbench reference state: Train section.

| Surface | Check | Evidence |
|---|---|---|
| Launch | Default Try the model, metadata and actual artifact visible | Desktop screenshot and health/version |
| Initial facts | Time and optional constraints submit explicit values | Session response / browser state |
| Question | Radio selection, preview, apply, skip, finish | Browser flow and saved revision |
| Preview | Hypothetical tag; confirmed ranking/state unchanged until applied | DOM and session revision |
| Revision | Edit earlier answer; later answers invalidated and next question recalculated | Browser notice / API regression |
| Restore | Reload/reopen saved session; actual server persistence | Browser reopen and restart regression |
| Export/delete | JSON attachment contains only observed data; confirm delete removes session | Export API and browser confirmation |
| No feasible brief | Time weekend retains hard constraint and ends explicitly | UI empty outcome screenshot |
| Model absent/server error | Helpful error and retry; no mocked successful result | API missing-model test and browser error state |
| Workbench | Dataset/train/evaluate/inspect navigation and real metadata | Workbench screenshot |
| Benchmark | Real comparison and budget curve; run re-evaluation, running/completed/error | Browser state and live job polling |
| API | OpenAPI schemas and /docs render | Schema check and browser capture |
| Responsive | 1440x1024, 390x844 and compact320 width; no hidden controls/overflow | Screenshots and DOM geometry |
| Accessibility | Labels, radio keyboard, focus visible, details, reduced motion rules | Keyboard/browser checks and source |
| Visual fidelity | Same-state workbench vs selected image, with intentional live-data differences | Combined comparison and design-qa.md |

Exploratory scenarios: edit after STOP; choose unknown and skip; stale revision; initial infeasible constraints; reload while a benchmark is running. Repeated jobs are the same frozen test, not new evidence.
