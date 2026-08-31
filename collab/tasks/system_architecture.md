# Task: System Architecture Design
**Assigned To:** Tanishq Giri & Aaroh Dharmadhikari
**Deadline:** 04/09/2026

## Objective
Design and document the core decoupled three-tier architecture for the AEGIS-TWIN logistics platform. 

## Requirements
*   **Decoupled Tiers:** Detail the separation between the WebGL Client UI, the Async FastAPI/Redis Telemetry Hub, and the PyTorch/Gymnasium AI Engine[cite: 3].
*   **Telemetry Specifications:** Outline the requirements for the sub-100ms bi-directional WebSocket streaming and the Redis in-memory coordinate hashes[cite: 3].
*   **Integration Points:** Define how the Graph Neural Network (PyG) and Deep Reinforcement Learning (PPO) models will interface with the telemetry hub without causing serialization latency[cite: 3].