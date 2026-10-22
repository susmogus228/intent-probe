# IntentProbe design QA

final result: passed

V2 follow-up: retained the approved light/cobalt layout. Root visually checked the real desktop flow and narrow390/320px layouts, verified three outcomes, preserved hypothetical previews, and saved current captures in docs/images/v2/. Fixed session-opening scroll position and reconciled v2 loss fields with the saved benchmark. The original v1 reference comparison below remains historical; no new generated design was substituted for actual ML outputs.

Source: docs/design/approved-workbench.png, the third displayed option accepted by the user,1487x1058 pixels.

Implementation: docs/images/workbench-desktop.png,2974x2116 pixels at1487x1058 CSS viewport. Normalize the2x capture to source size. State: ML workbench, Train. The default app view is Try the model as agreed.

The full comparison is docs/design/comparison-full.png; focused pipeline/configuration comparison is docs/design/comparison-detail.png. Both combine the actual source and rendered application in the same image and were opened for inspection.

## Intentional content differences

The reference shows an untrained concept, four unmeasured rows and a hypothetical hardware question. The implementation shows a trained artifact, six measured policies and the real learned question for an initial four-week session. These data changes lengthen the comparison and change the right-column content. The app does not force illustrative model outcomes to match an image.

## Fix history

| Finding | Fix | Verified outcome |
|---|---|---|
| P2: training command displaced comparison; supporting text too small | Collapsed command moved right; increased pipeline/configuration/table type; tightened comparison | Updated full and focused screenshots |
| P1: old keyed question remained after transition | Stable component with session/revision state reset and cancelled-preview guard | Exactly one question card after answer/skip/revision |
| P1: editor could carry across sessions | Editor reset on identity/revision | Unsaved editor absent after opening another session |
| P2: navigation retained unrelated scroll position | Reset scroll on view/section changes | Train begins at scrollY0 |
| P2: desktop options pushed actions far down | Two-column options on desktop, one on mobile | Browser question flow and viewport checks |

No actionable P0/P1/P2 finding remains in the checked scope.

## Fidelity surfaces

- Typography: system sans,42px desktop heading;13px pipeline headings and12px supporting data text after correction. No overlapping text. Desktop capture is softer than the generated reference; live UI is the better small-type reference.
- Spacing/layout:64px header,174px sidebar, two-column workbench, consistent gaps and reference panel order. Six real policies require more vertical space than four illustrative rows.
- Color/tokens: light neutral surfaces, dark ink, cobalt primary accent, hairline borders,6-7px panel radii; separate semantic warnings.
- Assets: consistent Phosphor library icons. The source has no raster hero or illustration. Pipeline boxes are interface elements; the quantitative regret chart has actual data and a table alternative.
- Copy/content: English; explicit synthetic scope, hypothetical vs applied state, fit vs probability, trusted local model and honest measured outcomes. Notes are not silently parsed.

## Responsive and interaction evidence

390x844 and320x740 viewports show equal document/client widths. Wide tables scroll internally. Navigation remains visible. Controls have labels, keyboard radio selection, visible focus, a skip link and reduced-motion CSS.

Verified creation, preview/application, revision after STOP, skip/unknown, restore after restart, infeasible outcome, deletion-confirmation/cancel, real benchmark completion, workbench sections and offline error/recovery. Normal-flow console-error log was empty. API deletion/export and missing-model paths have automated checks.

P3: further six-policy density tuning and sharper desktop publication captures may improve presentation. No physical handset or Safari run. Interim/rejected captures remain in ignored work/. No publication claim.
