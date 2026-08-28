# AEGIS-TWIN: Interactive Supply Chain Resilience Digital Twin

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

## Architecture & Feature Explanation

## Contents

- [Executive Summary & Vision](#1-executive-summary-vision)
- [Technology & Rendering Stack](#2-the-technology-rendering-stack)
- [Core AI Architecture & Synthetic Data](#3-core-ai-architecture-synthetic-data)
- [Dual Visualization & Triage Engine](#4-dual-visualization-the-triage-engine)
- [Notifications & Manual Override](#5-notifications-manual-override)

---

## 1. EXECUTIVE SUMMARY & VISION
AegisTwin is a state-of-the-art, high-stakes logistics simulation and management platform. It bridges the gap between advanced deep learning (GNNs and RL) and human-in-the-loop operational oversight. By simulating a live, breathing supply chain network using synthetic data, the system allows an autonomous Reinforcement Learning agent to manage complex routing, dispatch, and load balancing across a Graph Neural Network-represented spatial map.

However, unlike standard passive dashboards, this system is a highly interactive, gamified "triage" center. The core philosophy is "Autonomous Operations, Human Crisis Management." The RL model handles 95% of the daily operational load—grouping orders, dispatching trailers, routing around minor traffic—while a meticulously engineered Disruption Simulator injects 3–5% critical anomalies (e.g., severe weather, vehicle breakdowns, sudden infrastructure failures). When these critical anomalies occur, the system mandates rapid human intervention via a dual-view UI structure. Failure to act within realistic temporal deadlines results in cascading network failures, directly impacting live efficiency metrics.

---

## 2. THE TECHNOLOGY & RENDERING STACK

To achieve a real-time reactive interface paired with heavy computational machine learning, the architecture is decoupled into a high-performance frontend, a highly concurrent backend, and a dedicated ML inference engine.

### 2.1 Hardware-Accelerated Rendering (Bypassing API Lag)
Tracing hundreds of active logistical units on traditional web mapping APIs (such as Google Maps or standard Leaflet) results in severe DOM bottlenecking and excessive API costs. AegisTwin bypasses this entirely using WebGL.
*   **The Macro Map Base:** Mapbox GL JS provides a static, dark-mode visual layer used purely for geographical and aesthetic background context. 
*   **Mathematical Tracing (Deck.gl):** We utilize Deck.gl's `TripsLayer`. The Graph Neural Network defines the node coordinates (Warehouses). Deck.gl calculates the mathematical vectors and arc interpolations locally on the client GPU. It glides the truck icons smoothly at 60 FPS using timestamped coordinate deltas calculated by the backend physics engine, rendering it completely independent of external, rate-limited routing APIs.

### 2.2 Backend State & Telemetry
*   **FastAPI & WebSockets:** Python's `asyncio` framework drives the FastAPI backend, streaming synthetic simulation states, vehicle coordinates, and disruption triggers at a strict 100ms tick rate.
*   **Redis:** Acts as the ultra-fast in-memory state store. Traditional SQL databases are too slow for tick-based telemetry; Redis stores active coordinate hashes, node capacities, and ticking order countdown timers in memory for instant retrieval and broadcasting.

---

## 3. CORE AI ARCHITECTURE & SYNTHETIC DATA

### 3.1 Synthetic Data Generation (Gymnasium)
Rather than relying on static, historical real-world data, AegisTwin generates highly complex synthetic data via a **Python Gymnasium** environment. 
*   **Organic Order Spawner:** To simulate realistic business activity, orders are generated via a Non-Homogeneous Poisson Process (NHPP). This produces organic order arrival surges (rush hours) and quiet lulls, fundamentally testing the RL agent's capacity to scale its queue management dynamically.
*   **The Chaos Engine:** A Monte Carlo algorithm continually runs in the background, rolling probabilities to inject chaotic, non-linear disruptions into the training environment, ensuring the models are trained for maximum resilience.

### 3.2 Dual Machine Learning Models
AegisTwin operates on two interconnected models:

*   **Model 1: Graph Neural Network (PyTorch Geometric - GNN)**
    The supply chain is modeled as an attributed graph. The GNN processes the spatial network topology. It ingests data on traffic, weather hazards, and node congestion, outputting high-dimensional graph embeddings that represent the overall "health" of the road grid.
    $$h_i^{(l+1)} = \sigma \left( W^{(l)} h_i^{(l)} + \sum_{j \in \mathcal{N}(i)} e_{ij} \cdot \Theta^{(l)} h_j^{(l)} \right)$$

*   **Model 2: Reinforcement Learning Policy (Stable-Baselines3 - RL)**
    Acts as the autonomous dispatcher. It observes the GNN embeddings, the live task pool, and fleet state. It then predicts the optimal action: selecting 2 to 8 compatible orders, assigning them to a trailer, and pushing the dispatch command. It learns via a rigorous multi-objective reward function:
    $$R_t = \alpha(D_{success}) - \beta(T_{delay}) - \gamma(C_{penalty})$$
    The agent receives positive rewards for timely deliveries while taking massive penalties for missed deadlines or routing through hazardous edges.

---

## 4. DUAL VISUALIZATION & THE TRIAGE ENGINE

The core operational differentiator of AegisTwin is the separation of macro-level visual data and micro-level interactive data, ensuring the operator does not experience cognitive overload.

### 4.1 Macro vs. Micro Tracking
*   **Macro View (The Command Map):** Occupies the center of the screen. Provides the big picture. Users watch glowing paths and chevron icons navigate the spatial grid.
*   **Micro View (The Live Task Pool):** Occupies the right side-panel. Dispatched orders are represented as sleek **Progress Bars**. As the truck mathematically traverses the WebGL map, the corresponding progress bar steadily fills. This allows the user to monitor exact delivery health without visually hunting for specific pixels on the chaotic map.

### 4.2 The 3-5% Critical Anomaly Triage
When the Monte Carlo disruption engine rolls a critical failure (e.g., a blown engine or severe weather blockage), routine operations halt:
1.  **Macro Focus Lock:** The background WebGL map applies `backdrop-filter: blur(10px)`. A pulsing red radar wave rings the stranded truck, forcing visual attention to the point of failure.
2.  **Micro Inline Action Cards:** The side-panel progress bar for the affected order halts, turns flashing red, and physically expands into a **Triage Action Card**.
3.  **Active Countdowns & Choices:** The expanded card displays a ticking red deadline timer alongside inline, actionable triage buttons:
    *   `[DISPATCH TOW]` (High monetary cost, medium delay)
    *   `[REROUTE BACKUP]` (Low direct cost, high logistical overhead)
    *   `[ABANDON CARGO]` (Total loss, frees immediate resources)

### 4.3 Realistic Decay (The Graveyard Metric)
If the operator ignores the inline triage card and the countdown expires, the delivery definitively fails. The progress bar dissolves, the truck icon disappears from the map (simulating a permanent breakdown or recall), and the order is permanently logged into the **Graveyard Panel**—visibly tanking the live operational efficiency score and demonstrating the cost of human negligence.

---

## 5. NOTIFICATIONS & MANUAL OVERRIDE

### 5.1 Stratified Windows-Style Toasts
System telemetry is communicated via slide-in notifications in the bottom right corner, utilizing smooth Framer Motion easing physics:
*   **Green (Routine):** "Batch 904 Delivered Successfully." Fades out automatically after 3 seconds.
*   **Yellow (Alerts):** "RL Agent rerouting around Node 4 congestion."
*   **Red (Critical):** Persists infinitely until manually addressed via the Inline Triage Cards.
*   **Global Controls:** A precise live timestamp (`HH:MM:SS`) is attached to all toasts, alongside a global "Dismiss All Routine" button to clear screen clutter instantly.

### 5.2 The "God Mode" Kill Switch
A heavily styled, hardware-inspired toggle switch labeled `[AUTONOMOUS OPERATIONS: ON]`. 
Flipping this switch to `OFF` instantly overrides and pauses the RL agent's commands. While the physics engine and map remain live, the system accepts no automated dispatching. The operator can manually drag-and-drop VIP orders to specific trailers or right-click active units on the WebGL map to execute forced `[HALT]` or `[REROUTE]` commands, providing total, uncompromising human authority over the AI.

