# AEGISTWIN: Interactive Supply Chain Resilience Digital Twin

> [!CAUTION]
> PROPRIETARY AND CONFIDENTIAL
> This project, along with the associated codebase, constitutes the proprietary and strictly confidential intellectual property of IMCA.
> UNAUTHORIZED USE IS STRICTLY PROHIBITED. You may not copy, distribute, transmit, reproduce, publish, modify, or create derivative works from this source material without the explicit, documented authorization of the chief development team.
> Any unauthorized replication, reverse engineering, or dissemination of these proprietary systems will be subject to immediate legal action and aggressive prosecution under applicable intellectual property laws.
> This repository does NOT grant an open-source license. All rights are explicitly reserved.

<p align="center">
<img src="https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next JS">
<img src="https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB" alt="React">
<img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python">
<img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch">
<img src="https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="TailwindCSS">
<img src="https://img.shields.io/badge/Framer%20Motion-black?style=for-the-badge&logo=framer&logoColor=white" alt="Framer Motion">
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
<img src="https://img.shields.io/badge/Celery-37B24D?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
<img src="https://img.shields.io/badge/Deck.gl-000000?style=for-the-badge&logo=uber&logoColor=white" alt="Deck.gl">
</p>

## About This Project

AegisTwin is an AI-powered, real-time logistics resilience platform and digital twin. It is designed to bridge the gap between autonomous deep reinforcement learning orchestration and high-stakes human crisis management. Utilizing Graph Neural Networks (GNNs) for dynamic spatial-temporal network topology representation and Reinforcement Learning (RL) agents for autonomous multi-order batching (2–8 consignments per trailer), the platform operates live supply chain networks entirely via complex synthetic Gymnasium environments and mathematical trajectory rendering.

Unlike passive monitoring dashboards, AegisTwin implements an active human-in-the-loop paradigm. While the RL agent manages 95% of routine operations, an integrated Disruption Simulator injects 3–5% critical anomalies (e.g., vehicle breakdowns, severe weather, bridge closures, inventory bottlenecks). The UI balances a **Macro View** (a WebGL-rendered spatial map) with a **Micro View** (a side panel of active order progress bars). When crises occur, the system mandates rapid human triage via inline action cards and focus-locked modals, forcing the operator to mitigate cascading failures before strict temporal deadlines expire.

## Design Philosophy

**Dual Macro/Micro Command Center:** A dark-mode, high-contrast visual aesthetic inspired by modern air traffic control and telemetry stations. Built with glassmorphism, subtle neon glow indicators, and hardware-accelerated WebGL rendering. It balances the "big picture" macro map with granular, micro-level telemetry progress bars on the side panel to prevent cognitive overload.

**Synthetic Autonomy with Gamified Triage:** Routine operations feel effortless as the RL agent dynamically sweeps, batches, and assigns orders from a live task pool. When critical edge cases occur, the interface executes a "Focus Lock"—blurring the background map and transforming the micro-view progress bar into an urgent, inline Action Card (e.g., `[TOW]`, `[REROUTE]`, `[ABANDON]`) presenting clear trade-offs.

**Zero-Lag Hardware Rendering:** AegisTwin completely bypasses expensive, lag-heavy Google Maps trace routing. Instead, it utilizes `Deck.gl`'s `TripsLayer` to mathematically interpolate high-speed vehicle vectors over a static base map, ensuring silky-smooth 60 FPS animations across hundreds of concurrent autonomous units.

## Technical Architecture

### Frontend Stack
- **Next.js 14+** with React 18+ for high-performance SPA transitions, server components, and responsive layout scaling
- **Deck.gl & Mapbox GL JS** for GPU-accelerated WebGL rendering of dynamic road networks, utilizing `TripsLayer` for mathematical coordinate tracking without third-party API lag
- **Zustand** for ultra-fast, decentralized frontend state management without unnecessary re-renders
- **Framer Motion** for cinematic UI transitions, triage inline action cards, and smooth task pool batching animations
- **Tailwind CSS** with custom glassmorphism design tokens, CSS blur filters, and neon status indicators
- **TypeScript** for robust end-to-end type safety across telemetry payloads and dispatch commands

### Backend Stack
- **FastAPI** (Python 3.10+) utilizing async event loops for high-throughput WebSocket streaming and REST endpoints
- **Redis** as an ultra-fast in-memory state store tracking live vehicle coordinates, node states, and order lifecycles
- **Celery** for background simulation workers and asynchronous disruption event generation
- **WebSockets** for 100ms bi-directional streaming between the simulation engine and frontend clients

### AI & Simulation Engine
- **Synthetic Environment (Gymnasium):** Generates highly complex, non-linear supply chain data, removing the dependency on static real-world historical datasets and allowing for chaotic disruption modeling.
- **Graph Neural Network (PyTorch Geometric):** Ingests spatial node features (warehouses, hubs, processing latencies) and edge weights (traffic density, weather hazards, route distance) to generate dynamic mathematical network embeddings.
- **Reinforcement Learning Agent (Ray RLlib / Stable-Baselines3):** Deep Q-Network / PPO policy trained on simulated supply chain environments to autonomously batch 2–8 orders, select available trailers, and optimize dispatch schedules.
- **Disruption Simulator & Poisson Spawner:** Injects parameterized micro/macro disruptions using a Monte Carlo anomaly engine (3–5% critical anomaly rate) alongside Non-Homogeneous Poisson Process (NHPP) engine generating organic order influxes.

## Operational User Flow

### 1. Command Console Initialization
The operator opens the dashboard. The WebGL command map initializes, displaying the regional node network connected by glowing arterial routes. The UI sets up the Dual View: Macro Map in the center, Micro Task Pool on the right.

### 2. Live Task Ingestion & Organic Spawning
The Organic Spawner begins releasing customer orders based on Poisson distribution. The **Live Task Pool** side panel populates with order cards displaying destination, priority, deadline, and volume.

### 3. Autonomous Batching & Dual Tracking (RL Active)
Under autonomous mode, the RL Auto-Manager observes unassigned tasks and available trailers. 
*   **Macro View:** The UI animates 2–8 order cards highlighting in sync, consolidating into a consignment bundle, and assigning to a trailer. The trailer immediately departs along the GNN-optimized shortest path.
*   **Micro View:** The batched order cards transition into live **Progress Bars** on the side panel, smoothly filling up as the trailer mathematically traverses the map to its destination.

### 4. Windows-Style Notification Stream
As events unfold, timestamped toasts slide in from the bottom-right:
- *Green:* Routine delivery completed, trailer returned to depot. (Auto-dismisses in 3s)
- *Yellow:* Minor congestion detected; GNN dynamically reroutes trailer.
- *Red:* High-urgency alert requiring human input.

### 5. Critical Anomaly Trigger & Inline Triage
When a 3–5% critical disruption strikes (e.g., trailer engine failure carrying perishable cargo):
*   **Macro Focus Lock:** The background map blurs (`backdrop-filter: blur(10px)`). A pulsing red perimeter wraps the immobilized trailer on the map.
*   **Micro Action Card:** The side-panel progress bar snaps to red, halts, and expands into a ticking **Inline Action Card** displaying three actionable buttons:
    1. *[DISPATCH TOW]:* High cost, medium recovery delay.
    2. *[REROUTE BACKUP]:* Low direct cost, requires load transfer.
    3. *[ABANDON CARGO]:* High cargo write-off, frees immediate resources.

### 6. Decay, Cascading Failure, and Graveyard Logging
If the operator ignores the inline triage alert, the countdown timer eventually expires. The consignment permanently fails, the progress bar dissolves, the trailer icon turns grey and dissolves on the map, and the failure is logged into the **Graveyard Analytics** panel, visibly reducing the system efficiency score.

### 7. "God Mode" Kill Switch & Manual Injection
At any moment, the operator can flip the **Autonomous Operations Kill Switch** to assume manual control. The operator can drag-and-drop orders to specific trailers, halt active units with a right-click context menu, or manually trigger custom disruption scenarios.

## Setup & Execution

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- Git
- Redis Server (local or cloud instance)
- CUDA-enabled GPU (optional, for accelerated PyTorch GNN/RL inference)

```bash
WIP
```
