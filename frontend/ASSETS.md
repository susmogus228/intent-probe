# Frontend resources

- UI icons: `@phosphor-icons/react` 2.1.10, MIT, https://github.com/phosphor-icons/react. Package installation retains upstream license. Verified package metadata and maintained README on 2026-10-22. Icons are local, individual imports; no external image request.
- Fonts: operating-system UI stack and local system monospace. No remote font service.
- Visual target: `../docs/design/approved-workbench.png`, selected by the user. Layout adapted to live API data and responsive viewports.
- Charts: accessible SVG data visualizations computed from benchmark API values, with text description and complete table alternative.

React and Vite APIs were checked against official documentation through Context7 before implementation. The browser and visual acceptance checks are performed by the root integrator against the real backend.
