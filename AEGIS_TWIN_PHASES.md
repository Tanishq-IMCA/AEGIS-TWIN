# AEGIS TWIN — Page-by-page build plan

## Progress checklist

### Phase 1 — Main dashboard
- [x] Rename the landing page to AEGIS TWIN and remove the finance/profile/system-health cards.
- [x] Put the Seattle map on the landing page, with a 70/30 map-to-status-panel layout.
- [x] Use dark, low-clutter tiles, Seattle zoom bounds, pan/zoom, and road-following OSRM routes.
- [x] Make truck markers prominent; show one selected truck's travelled/remaining road path and hover details.
- [x] Add Finished, Ongoing, Needs Attention, and Cancelled status views.
- [x] Support dispatch creation, cancellation, roadside requests, and route resume from the dashboard.
- [x] Use the existing animated notice popup for arrivals, slowdown, and incident updates without blurring the page.
- [x] Simulate a one-time 10% chance of 120 mph overspeeding with yellow alerts and capped time-recovery estimates.

### Phase 2 — Control Panel
- [x] Keep a dedicated no-map dispatch response page with roadside assistance and resume actions.

### Phase 3 — Manifest
- [x] Rename the Tasks navigation entry and page heading to Manifest.
- [ ] Link manifest items to dispatches, destinations, and due times.

### Phase 4 — Trailer Availability
- [x] Replace the finance placeholder with per-hub trailer counts and add/status/remove controls.

### Phase 5 — Calendar
- [ ] Add pickup/arrival windows and maintenance dates linked to manifests or trucks.

### Phase 6 — Settings
- [x] Preserve Settings without changes.

### Phase 7 — Engine Logs
- [x] Add a live, filterable engine feed with UTC timestamps to millisecond precision.
- [x] Log dispatch, movement, slowdown, delivery, roadside, resume, and cancellation events.
- [x] Log simulated overspeed events.

### Phase 8 — Local run
- [x] Allow PyCharm runs to load `.env`, use a local SQLite login store, and honor `HOST`, `PORT`, and `FLASK_DEBUG`.
- [x] Provide a PyCharm `main.py` launcher backed by the project requirements file.

### Phase 9 — Fleet analytics
- [x] Add rolling per-delivery financial trends with two-minute time ticks and clearly separated cost scales.
- [x] Keep a fixed recent-update window, animate incoming samples, and show hover readings.
- [x] Include delivery, mileage, fuel, time-saved, and overspeed details in the CSV export.

## Product direction

AEGIS TWIN is an operations orchestrator: dispatch work, see truck progress, respond to exceptions, and keep delivery and trailer information in one place. Keep the first release small and operator-focused. Do not add a general finance, social, or AI feature unless it directly reduces dispatch work.

## Phase 1 — Dashboard / Operations overview

**Goal:** Make the home page a useful live snapshot rather than a personal finance dashboard.

- Rename the product heading to **AEGIS TWIN**.
- Remove personal balance, payment-card, earnings/expenses, operational-efficiency, and system-integrity widgets from the main view.
- Give the largest area to a Seattle fleet map; show active trucks, their status, and a concise delivery count.
- Add a small completed-deliveries glass panel and a short list of the latest operational alerts.
- Reuse the dispatch engine's data; the dashboard should summarize it, not create a second source of truth.
- Keep account/profile information available in Settings, not on the operations map.

**Acceptance:** The first screen answers “what is moving, what is blocked, and what just arrived?” without scrolling.

## Phase 2 — Control Panel / Dispatch response

**Goal:** Create and monitor a dispatch, then handle a disabled truck.

- Add a Control Panel entry above Settings.
- Show Seattle routes, two warehouse hubs, and twenty selectable city destinations.
- Provide active, slowed, and assistance-needed truck states; show speed and shipment on hover.
- Assign a truck from a selected hub to a destination. Use a weighted cruise-speed profile: 60% at 50 mph, 30% at 90 mph, and 10% at 120 mph on longer/freeway-style routes; slow around route bends.
- Roll the incident chance once for each new dispatch: exactly a 5% per-dispatch chance of a simulated roadside incident. Do not reroll on refresh or on each poll.
- Let an operator request roadside assistance and explicitly resume the route after help is confirmed.
- Keep completed deliveries in glass cards with the dispatch, origin/destination, total time, and early/on-time/late result.
- Emit concise animated notices for dispatch creation, incidents, assistance, and resume actions.

**Acceptance:** A trip is persisted per account, progresses on refresh, produces no more than its one assigned incident, and can be resumed after assistance. OSRM supplies the road geometry; tile and routing availability still depend on their public endpoints.

## Phase 3 — Tasks → Manifest

**Goal:** Make the current task page the dispatch work queue.

- Rename its navigation label and icon to **Manifest**; preserve the existing task editor and storage.
- Add optional links from a manifest item to a dispatch, destination, and due time.
- Keep status simple: queued, assigned, loaded, delivered.
- Add filters for status and due date; retain the existing quick-create flow.
- Do not introduce driver payroll, inventory accounting, or a complex approval workflow.

**Acceptance:** An operator can see unassigned work, create a manifest item, and tell which dispatch owns it.

## Phase 4 — Finances → Trailer Availability

**Goal:** Replace the placeholder financial page with a small trailer-readiness board.

- Rename the page and wallet icon to **Trailers**.
- Track only trailer ID, type, hub, and availability state: available, assigned, or maintenance.
- Add a fast status toggle and a “last checked” timestamp.
- Show simple counts by hub and a short maintenance list.
- Keep pricing, revenue, and financial accounts out of this page.

**Acceptance:** A dispatcher can answer “how many trailers can I assign here?” in one glance.

## Phase 5 — Calendar / Dispatch schedule

**Goal:** Turn the calendar into the next useful planning surface without building a full scheduling suite.

- Show planned pickup/arrival windows and maintenance dates.
- Link each event to its manifest item or truck.
- Keep the existing clear empty state when there are no scheduled items.
- Start with a week view and a compact upcoming list; defer recurring schedules and multi-user conflict resolution.

**Acceptance:** Upcoming pickups and vehicle downtime are visible without duplicating Manifest data.

## Phase 6 — Settings

**Goal:** Preserve the current settings experience.

- Leave existing account, appearance, and bridge controls unchanged.
- Add only operational defaults when needed (preferred hub, alert preferences, units).
- Keep sensitive credentials in the workspace secrets flow, never in page data.

## Phase 7 — Login, local development, and release readiness

**Goal:** Keep Replit preview and local PyCharm startup predictable.

- Replit continues to use its managed `DATABASE_URL` for login accounts only.
- Local runs without Replit environment variables use a private SQLite login database under `data/` and a temporary development session secret.
- Load local `.env` values when present and honor `HOST`, `PORT`, and `FLASK_DEBUG`.
- Continue storing ordinary per-user app data in the existing JSON storage; do not move it to PostgreSQL.
- Before a public rollout, replace simulated route geometry with a maintained routing service, add rate limits and monitoring, and review incident semantics with the intended operator.

## Map provider recommendation

Do not use Uber Maps for this prototype. Use **Leaflet + CARTO dark tiles** with OpenStreetMap attribution and **OSRM** for Seattle road geometry. No Uber key is needed; the map stays inside Seattle bounds. The public routing and tile endpoints are suitable for prototyping, not a production service-level guarantee. Review provider terms and reliability before rollout. The current 5% incident is simulated, not a real accident feed or emergency-service call.

## Small-feature recommendations for otherwise empty pages

| Page | Useful first feature | Deliberately defer |
|---|---|---|
| Dashboard | Fleet snapshot, status counts, latest alert, recent arrivals | Financial KPIs and dense charts |
| Control Panel | Dispatch assignment, live status, roadside request | Automated recovery decisions |
| Manifest | Queued work with dispatch and due-time links | Complex approvals and payroll |
| Trailers | Availability by hub and maintenance toggle | Full parts/inventory accounting |
| Calendar | Pickup/arrival windows and maintenance | Recurrence rules and team scheduling |
| Settings | Existing controls plus a few operational defaults | Reworking account or theme behavior |

## Shared rules

- Treat each trip as the source of truth for its route, status, speed target, ETA, and completion record.
- Store dispatch records in the existing per-user JSON store; PostgreSQL remains limited to login accounts.
- Keep notices brief and actionable; use the current animated notice component.
- Display speeds in mph and show a clear “simulated” label until connected to real vehicle telemetry.
- Never describe a simulated roadside request as a call to an actual assistance provider.
