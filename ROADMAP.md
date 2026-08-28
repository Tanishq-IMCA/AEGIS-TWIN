
# AEGISTWIN DEVELOPMENT ROADMAP

> [!CAUTION]
> PROPRIETARY AND CONFIDENTIAL
> This project, along with the associated codebase, constitutes the proprietary and strictly confidential intellectual property of IMCA.
> UNAUTHORIZED USE, REPRODUCTION, DISTRIBUTION, OR MODIFICATION OF THE FRONTEND, BACKEND, DATABASE SCHEMA, OR ANY DERIVATIVE WORK IS STRICTLY PROHIBITED. All rights are explicitly reserved worldwide.

<p align="center">
<img src="https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next JS">
<img src="https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB" alt="React">
<img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python">
<img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch">
<img src="https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="TailwindCSS">
<img src="https://img.shields.io/badge/Framer%20Motion-black?style=for-the-badge&logo=framer&logoColor=white" alt="Framer Motion">
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
<img src="https://img.shields.io/badge/Deck.gl-000000?style=for-the-badge&logo=uber&logoColor=white" alt="Deck.gl">
</p>

## Project Status Overview

| Component | Status | Notes |
| :--- | :--- | :--- |
| **Command Map GUI (Deck.gl/WebGL)** | `COMPLETE` | Dark-mode cyber grid, warehouse node rendering, static basemap |
| **FastAPI WebSocket Streaming** | `COMPLETE` | 100ms bi-directional tick streaming, schema validation via Pydantic |
| **Organic Poisson Spawner (NHPP)**| `COMPLETE` | Non-homogeneous Poisson arrival engine; rush hour curve modeling |
| **Task Pool & Batching Animations** | `IN PROGRESS` | Framer Motion grouping animations active; capacity counters syncing |
| **GNN Topology Encoder (PyG)** | `IN PROGRESS` | Graph Convolutional layers built; dynamic edge weight update in testing |
| **RL Auto-Manager (Gymnasium)** | `IN PROGRESS` | Environment rewards formulated; batching policy currently in active training |
| **Disruption Engine (Monte Carlo)** | `IN PROGRESS` | Anomaly matrix active; tuning 3–5% probability threshold |
| **Focus Lock & Inline Triage** | `IN PROGRESS` | Progress bar transformation to Action Cards active; API routing pending |
| **Decay & Cascading Failure Engine** | `NOT STARTED` | Countdown timer logic designed; graveyard metric sync pending |
| **God Mode Kill Switch** | `NOT STARTED` | UI toggle built; WebSocket pause payload logic pending |
| **Graveyard Analytics Panel** | `NOT STARTED` | Data structures planned; interactive charts pending |

---

## Phase 1: AI & Synthetic Data Engine `DONE`
- [x] Create Python Gymnasium environment for generating chaotic, synthetic supply chain data
- [x] Implement Non-Homogeneous Poisson Process (NHPP) mathematical engine for realistic order generation
- [x] Model cyclical order arrival curves (Morning Peak, Afternoon Flow, Night Lull)
- [x] Parameterize order payloads: SKU volume (1–8 slots), value tier, temporal deadline window
- [x] Build Monte Carlo anomaly generator with adjustable risk coefficients

## Phase 2: Deck.gl Macro Command Map `DONE`
- [x] Integrate Deck.gl WebGL canvas over a static Mapbox dark-mode basemap
- [x] Implement `TripsLayer` for GPU-accelerated mathematical coordinate interpolation (avoiding API lag)
- [x] Render custom SVG 3D trailer chevrons with real-time directional heading calculations
- [x] Add dynamic Glowing Arc layers to visualize active transit routes between nodes
- [x] Implement interactive hover tooltips (Trailer ID, 4/8 Capacity, Cargo ETA)

## Phase 3: WebSocket Streaming & Redis In-Memory State `DONE`
- [x] Build FastAPI asynchronous WebSocket endpoint (`/ws/telemetry`)
- [x] Store trailer coordinates, route steps, and node inventories in Redis hashes
- [x] Broadcast 100ms delta-compressed simulation frames to frontend React state
- [x] Implement auto-reconnect logic with exponential backoff on client side

## Phase 4: GNN & RL Model Training `IN PROGRESS`
- [x] Build PyTorch Geometric (PyG) Graph Convolutional Network (GCN) layer
- [x] Formulate state observation space (GNN embeddings, fleet status, unassigned orders)
- [x] Engineer multi-objective reward function for the RL agent
- [ ] Train Deep Q-Network (DQN) / PPO baseline model on 100,000 simulated Gymnasium episodes
- [ ] Implement dynamic edge weight modulation (traffic density, weather coefficients)
- [ ] Benchmark RL dispatch decisions against standard Greedy Dijkstra heuristic

## Phase 5: Micro-Tracking Task Pool & Progress Bars `IN PROGRESS`
- [x] Build Live Task Pool side panel for incoming order ingestion
- [x] Implement Framer Motion grouping animations (visualizing the RL agent batching 2-8 cards)
- [x] Create dynamic micro-tracking progress bars for active dispatched orders
- [ ] Sync side-panel progress bar fill-rate with WebGL backend trajectory timestamps via WebSocket

## Phase 6: Disruption Matrix & Inline Triage UI `IN PROGRESS`
- [x] Implement Macro Focus Lock (`backdrop-filter: blur(10px)`) and pulsing radar over broken units on the map
- [x] Transform side-panel progress bars into **Inline Action Cards** upon anomaly detection
- [x] Add real-time visual ticking countdowns directly beside inline actions: `[Tow]`, `[Reroute]`, `[Abandon]`
- [ ] Route human triage clicks via WebSocket to instantly reconfigure backend RL routing state
- [ ] Add sound and visual urgency indicators for critical priority events

## Phase 7: Decay Logic, Deadlines & Cascading Failures `NOT STARTED`
- [ ] Attach strict temporal deadlines to all spawned orders (perishable vs. standard goods)
- [ ] Implement cascading failure logic (progress bar reaches zero -> order permanently fails)
- [ ] Implement "Unit Die-Out" visual effect on the WebGL map: grey desaturation and particle dissolve
- [ ] Compute cascading bottleneck propagation to downstream warehouses based on failed deliveries

## Phase 8: "God Mode" Kill Switch & Manual Overrides `NOT STARTED`
- [ ] Build glowing "AUTONOMOUS OPERATIONS: ON/OFF" master toggle switch
- [ ] Disconnect RL auto-dispatch upon toggle off while preserving ongoing physics engine
- [ ] Implement drag-and-drop manual consignment assignment from Task Pool to trailers
- [ ] Add right-click unit context menu: "HALT UNIT", "FORCE RETURN", "PRIORITIZE"
- [ ] Seamless hot-reloading back into RL autonomous mode

## Phase 9: Graveyard Metrics & Notification Hub `NOT STARTED`
- [ ] Build slide-in toast container with Framer Motion spring physics (Routine, Warning, Critical)
- [ ] Add "Dismiss All Routine" action and live precise timestamps (`HH:MM:SS`)
- [ ] Construct Graveyard side panel logging all expired and abandoned consignments
- [ ] Real-time session metrics tracking: On-Time Delivery Rate, Mean Recovery Time, Carbon Index
- [ ] Embed interactive SVG/Canvas loss curves comparing RL performance vs Human interventions

## Phase 10: Production Hardening & Benchmark Deployment `PLANNED`
- [ ] Containerize services via Docker and Docker Compose (FastAPI, Redis, Celery, Frontend)
- [ ] Run 1,000-vehicle stress test at 60 FPS WebGL rendering
- [ ] Deploy frontend to Vercel and simulation backend to dedicated GPU cloud instance
- [ ] Conduct end-to-end chaos tests against sustained 10% disruption storms

---

## Execution Order
Phase 1  ───►  Phase 2  ───►  Phase 3  ───►  Phase 4
│              │              │              │
▼              ▼              ▼              ▼
Phase 5  ───►  Phase 6  ───►  Phase 7  ───►  Phase 8
│              │              │              │
▼              ▼              ▼              ▼
Phase 9  ───► Phase 10 


Each phase is self-contained and must be validated against integration benchmarks before proceeding to subsequent modules.