<div align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=appveyor" alt="Project Status" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask Framework" />
  <img src="https://img.shields.io/badge/Frontend-HTML5%2FCSS3%2FJS-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="Frontend Stack" />
  <img src="https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white" alt="Leaflet" />
  <img src="https://img.shields.io/badge/CARTO-Basemaps-13A538?style=for-the-badge&logo=carto&logoColor=white" alt="CARTO" />
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
</div>

<br/>

> [!CAUTION]
> **PROPRIETARY & CONFIDENTIAL — AEGIS-TWIN FLEET OPERATIONS PLATFORM**  
> This specification, system architecture, and codebase constitute the proprietary intellectual property of **IMCA / AEGIS-TWIN Development Team**.  
> Unauthorized copying, distribution, alteration, reverse engineering, or commercial dissemination is strictly prohibited without explicit written authorization. All rights reserved.

<br/>

<div align="center">
  <h1>AEGIS-TWIN</h1>
  <h3>Interactive Supply Chain Resilience & Fleet Operations Digital Twin</h3>
  <p>Real-time geospatial fleet telemetry, autonomous routing, chaos injection triage, trailer readiness, and operational analytics.</p>
</div>

<hr />

## 📖 Overview

**AEGIS-TWIN** is a cybernetic fleet operations and supply chain resilience digital twin platform. It provides operations dispatchers and logistics analysts with real-time geospatial tracking, dynamic road-following routing across the Seattle metropolitan corridor, autonomous and manual dispatch workflows, stochastic incident triage, trailer readiness management, and live financial telemetry.

The platform follows an **"Autonomous Operations, Human Crisis Management"** operational model: autonomous background engines manage routine transit and progression, while providing operators with rich situational awareness and fast incident-response triage for simulated breakdowns, slowdowns, and overspeed events.

---

## ✨ Key System Features

*   **Geospatial Seattle Fleet Digital Twin**
    *   70/30 split-view layout prioritizing the high-resolution Seattle map.
    *   Dark vector/raster tiles powered by Leaflet and the CARTO Basemaps API with strict metropolitan boundary locking.
    *   Turn-by-turn road geometry interpolation using Open Source Routing Machine (OSRM).
    *   Dynamic vehicle telemetry markers with status indicators:
        *   🟢 **Active / Nominal Transit** (`#4ADE80`)
        *   🟡 **Slowed / Bend Deceleration / Overspeed Advisory** (`#FACC15`)
        *   🔴 **Incident / Breakdown / Assistance Required** (`#EF4444`)
    *   Full road path inspection showing past travelled path and remaining route.
    *   Interactive hover telemetry: real-time speed in mph, cargo payload, origin hub, destination, and calculated ETA.

*   **Dispatch Control Panel & Incident Triage**
    *   Origin hub selection (**Hub Alpha - North Seattle** and **Hub Beta - South Seattle**) to 20 city destination nodes.
    *   Autonomous Dispatch Mode (`dispatch_autonomy.json`) with automatic fleet task assignment.
    *   5% stochastic incident injection model triggering roadside breakdown alerts.
    *   One-click operator actions: **[Request Roadside Assistance]** and **[Resume Route]**.
    *   Instant trip cancellation with status preservation.

*   **Trailer Availability & Readiness Board**
    *   Real-time inventory and availability tracking across Hub Alpha and Hub Beta.
    *   Operational status segregation: `Available`, `Assigned`, and `Maintenance`.
    *   Instant status toggles with "Last Checked" UTC timestamp tracking.

*   **Cargo Manifest & Task Management Queue**
    *   Complete shipment lifecycle: `Queued`, `Assigned`, `Loaded`, and `Delivered`.
    *   Direct linking between manifest cargo items, active dispatch IDs, destinations, and scheduled deadlines.

*   **Temporal Logistics & Calendar**
    *   Visual scheduling for pickup windows, target delivery deadlines, and truck maintenance downtime.
    *   Entity association between calendar items, truck IDs, and cargo manifests.

*   **Fleet Financials & Operational Analytics**
    *   Rolling real-time financial charts with separate scales for revenue, fuel cost, and operating overhead.
    *   Punctuality tracking and time-saved metrics from optimal routing and overspeed events.
    *   RFC-4180 compliant CSV export (`/analytics.csv?download=1`) for offline analysis and auditing.

*   **Millisecond-Precision Engine Logs Feed**
    *   Continuous high-frequency event stream with ISO UTC millisecond timestamps (`YYYY-MM-DDTHH:MM:SS.mmmZ`).
    *   Taxonomy covering dispatches, movement updates, speed changes, overspeed alerts, incidents, assistance, and completions.
    *   Real-time client-side search, log level filtering, and stream pause capability.

*   **Robust Multi-Tenant Security & Storage**
    *   SQLite database (`data/local_auth.sqlite3`) with hashed credentials for authentication.
    *   Strict password policy enforcing a minimum of 12 characters and uppercase letter requirements.
    *   Partitioned per-user JSON storage under `data/user_data/<user>/preferences/`.
    *   Automated profile self-healing protocol (`/api/restore_corrupt`) to repair missing entities without data loss.

---

## 🧭 Page Architecture & Modules

The platform is organized into 8 interconnected modules accessible from the sidebar navigation:

| Module | Route | Primary Objective & Capabilities |
| :--- | :--- | :--- |
| **Operations Dashboard** | `/` | 70/30 split view with Seattle fleet map, active truck telemetry, status counts, and completed delivery glass cards. |
| **Control Panel** | `/control_panel` | Dispatch creation console, manual route launches, autonomy toggle, and roadside incident triage. |
| **Manifest** | `/tasks` | Work queue for cargo manifests, status progression, due dates, and dispatch assignments. |
| **Trailers** | `/trailers` | Fleet trailer readiness board with hub inventories and maintenance status controls. |
| **Calendar** | `/calendar` | Time-blocked scheduling of pickup/arrival windows and vehicle service intervals. |
| **Fleet Analytics** | `/analytics` (`/finances`) | Real-time financial curves, cost breakdown, fuel consumption, and CSV export engine. |
| **Engine Logs** | `/engine_logs` | High-frequency telemetry log stream with millisecond UTC timestamps and search filters. |
| **Settings & Security** | `/settings` | Profile customization, password updates, theme accents, and cloud bridge sync settings. |

---

## 🛠️ API & Telemetry Endpoints

### Dispatch & Simulation Engine
*   `GET /api/dispatch/overview`: Full operational snapshot of active dispatches, hubs, and truck positions.
*   `POST /api/dispatch/create`: Create a new dispatch with origin, destination, and trailer assignment.
*   `POST /api/dispatch/cancel`: Cancel an active dispatch route.
*   `POST /api/dispatch/roadside`: Request roadside assistance for an incident-flagged vehicle.
*   `POST /api/dispatch/resume`: Resume transit for a repaired vehicle.
*   `GET/POST /api/dispatch/autonomy`: Retrieve or toggle autonomous dispatching mode.

### Trailer & Manifest Operations
*   `GET/POST /api/trailers`: Retrieve trailer readiness inventory or update status.
*   `GET/POST /api/tasks`: Retrieve or create cargo manifest items.

### Analytics, Logs & System Metrics
*   `GET /api/analytics`: Rolling financial, fuel, and time-recovery metrics.
*   `GET /analytics.csv`: RFC-4180 CSV export of trip performance records.
*   `GET /api/engine_logs`: Retrieve recent engine event log entries.
*   `GET /api/sys_usage`: Real-time hardware telemetry (CPU, RAM, Disk utilization via `psutil`).

### Authentication & Account Governance
*   `POST /api/login`: User authentication and session creation.
*   `GET/POST /api/users`: List available identities or register new user.
*   `POST /api/restore_corrupt`: Self-repair protocol for corrupted user profile data.
*   `POST /api/delete_account`: Secure user account purge protocol.

---

## 💻 Technology Stack

*   **Backend Runtime:** Python 3.11+
*   **Web Framework:** Flask, Werkzeug, Jinja2
*   **Geospatial & Cartography:** Leaflet.js, CARTO Basemaps API (Dark Vector/Raster)
*   **Routing Service:** OSRM (Open Source Routing Machine - Seattle arterial grid)
*   **System Telemetry:** `psutil`
*   **Storage & Persistence:** SQLite (`local_auth.sqlite3`), Partitioned JSON NoSQL document store
*   **Frontend Technologies:** HTML5, CSS3 (Glassmorphism & animations), Vanilla JavaScript (ES6+)

---

## 🚀 Installation & Setup

### 1. Prerequisites
*   Python 3.11 or higher installed on your system.
*   Git (optional, for cloning).

### 2. Clone or Open the Repository
```bash
git clone <repository_url>
cd AEGIS-TWIN
```

### 3. Install Dependencies
Using pip or your preferred environment manager:
```bash
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create or verify the `.env` file in the project root:
```env
CARTO_BASEMAPS_API_KEY=cb1_4gic_1_853ee5bf53c4c8baaa95eba8
HOST=0.0.0.0
PORT=5000
FLASK_DEBUG=0
```
*(The CARTO Basemaps API key is loaded automatically from `.env` or application defaults).*

### 5. Launch the Server
*   **Via PyCharm:** Open the project in PyCharm, right-click `main.py`, and choose **Run 'main'**.
*   **Via Terminal / PowerShell:**
    ```powershell
    python main.py
    ```

### 6. Access the Application
Open your browser and navigate to:
```
http://localhost:5000
```
Log in with your credentials or register a new identity to enter the AEGIS-TWIN operations center.

---

## ⚠️ Anomaly & Error Codes

| Code | Categorization | Description & Resolution Protocol |
| :--- | :--- | :--- |
| **NX-101** | Invalid Credentials | Username or password mismatch during authentication or account deletion. |
| **NX-300** | Missing Payload Parameters | Required fields (username, password, truck ID) were omitted from request. |
| **NX-400** | Security Policy Violation | Password fails to meet the minimum 12-character or uppercase letter standard. |
| **NX-401** | Profile Integrity Exception | Corrupted or missing profile attributes detected; resolved via `/api/restore_corrupt`. |
| **NX-404** | Entity Not Found | Target vehicle, manifest item, or user record not found. |
| **NX-500** | Internal Server Error | Unhandled server-side exception; stack trace logged to system logs. |

---

## 📚 Project Documentation Directory

*   **[Software Requirements Specification (SRS)](SOFTWARE_REQUIREMENTS.md):** Complete technical, functional, and non-functional specifications.
*   **[Master Development Roadmap](ROADMAP.md):** Completed implementation milestones and future feature roadmap.
*   **[API Testing Guide](API_TESTING.md):** Detailed endpoint specifications and verification testing instructions.
*   **[Presenter Guide](Aegis_Twin_Presenter_Guide.md):** Walkthrough and presentation talking points for system demonstrations.
*   **[Technical Architecture Explanation](EXPLANATION.md):** Deep-dive breakdown of the internal mechanics and simulation engine.
*   **[Team Assigned Tasks](Team_assigned_tasks.md):** Task assignments and collaborative development tracking.

---

<div align="center">
  <i>"AEGIS-TWIN • Autonomous Operations, Human Crisis Management."</i>
</div>
