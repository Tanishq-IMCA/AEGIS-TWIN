---
name: AEGIS TWIN product direction
description: Product constraints and roadmap for the AEGIS TWIN logistics orchestrator.
---

AEGIS TWIN is a dispatch and fleet-operations orchestrator centered on Seattle. Truck movement and roadside incidents are simulations until connected to real telemetry or a provider. A new dispatch has a 5% simulated incident chance; speed targets range from 50–120 mph and should slow at turns. The user prefers small, practical features per page and wants Settings preserved.

**Why:** the user stated these product constraints and asked for a page-by-page implementation plan.

**How to apply:** consult `AEGIS_TWIN_PHASES.md` before extending the dashboard, Control Panel, Manifest, trailer, calendar, or Settings pages.

CARTO's direct basemap tiles require a key; without one, tile requests may return HTTP 200 while displaying a key-required watermark. CARTO's published free monthly limits are 5 million non-commercial and 1 million commercial requests. OSRM routing does not need that key.

**Why:** this behavior was confirmed on 2026-10-11; an HTTP-success check alone can mistake CARTO's watermark image for map tiles.

**How to apply:** keep CARTO keys in Replit Secrets, restrict them to the app domain where possible, and verify visible tile content as well as HTTP status.
