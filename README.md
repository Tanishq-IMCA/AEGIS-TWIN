<div align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge&logo=appveyor" alt="Project Status" />
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-lightgrey?style=for-the-badge&logo=flask" alt="Flask Framework" />
  <img src="https://img.shields.io/badge/Frontend-HTML%2FCSS%2FJS-orange?style=for-the-badge&logo=html5" alt="Frontend Stack" />
</div>

<br/>

<div align="center">
  <h1>IMCA NEXUS EXPERIENCE</h1>
  <h3>INDIVIDUAL USER SUPPORT</h3>
  <p>A sophisticated, multi-faceted personal dashboard and system integration platform.</p>
</div>

<hr />

## 📖 Overview

The **IMCA Nexus Experience** is a comprehensive personal management and bridge system designed to centralize tasks, scheduling, health tracking, social interactions, and system monitoring into a single, cohesive, futuristic dashboard.

Built with a robust Python/Flask backend and a dynamic frontend, the system supports multi-user profiles, secure data storage, real-time background syncing, and a unique "Relay" architecture for decentralized cloud communication between peers.

---

## ✨ Key Features

*   **Multi-User Authentication & Identity Management**
    *   Secure login with credential hashing and "Social Tag" integration.
    *   Corrupt profile detection and automated restoration protocols.
    *   Dynamic profile customization (avatars, themes, security questions).
*   **Nexus Bridge & Cloud Relay**
    *   Background sync thread for low-impact polling of cloud packets.
    *   Peer-to-peer messaging and data transfer (friend requests, tasks, calendar events).
    *   Fallback legacy direct bridge communication.
*   **System Telemetry**
    *   Real-time monitoring of CPU, RAM, and Disk utilization via `psutil`.
    *   Relay storage capacity and health metrics.
*   **Modular Architecture**
    *   Segmented data storage management (`storage_manager.py`).
    *   Dedicated relay service (`relay_manager.py`).
    *   Pluggable frontend template system.

---

## 🧭 Page Architecture & Modules

The platform is divided into several specialized modules, accessible via the main dashboard:

### 1. Dashboard (`/`)
The central hub. Displays an overview of operational efficiency, system integrity, current user telemetry, and quick access to all subsystems.

### 2. Tasks (`/tasks`)
A comprehensive task operations center. Manage to-dos, track progress, and receive bridged tasks from connected peers.

### 3. Schedule (`/schedule`)
Academic and professional time-blocking. Organize daily routines and recurring events.

### 4. Calendar (`/calendar`)
Temporal logistics. A full-view calendar for tracking long-term events, deadlines, and bridged appointments.

### 5. Health (`/health`)
Health operations tracking. Log metrics, track wellness goals, and maintain physical and mental readiness data.

### 6. Social Matrix (`/social`)
Manage peer connections. Send friend requests via the Nexus Bridge, monitor peer online status, and engage in real-time or asynchronous messaging.

### 7. Finances (`/finances`)
Financial overview and tracking. Monitor budgets, expenses, and financial goals.

### 8. System Config (`/settings`)
Deep customization of the Nexus instance. Update profile data, configure bridge partner URLs, adjust UI themes, and manage security settings.

---

## 🛠️ API & System Endpoints

The system exposes a rich internal API for dynamic frontend updates and bridge communications.

### Authentication & Account Management
*   `POST /api/login`: Standard user authentication.
*   `GET/POST /api/users`: Retrieve user lists or register a new identity.
*   `POST /api/delete_account`: Purge user data (requires password).
*   `POST /api/delete_account_no_pass`: Purge user data (active session required).
*   `POST /api/restore_corrupt`: Emergency protocol to repair missing profile data.

### Bridge & Relay Communications
*   `POST /api/bridge/receive`: Endpoint for receiving legacy direct-bridge packets.
*   `GET/POST /api/bridge/config`: Manage direct bridge partner URLs.
*   `GET /api/bridge/status`: Retrieve bridge and cloud relay connectivity metrics.
*   `GET /api/relay/discovery`: Discover available peers on the active relay network.
*   `POST /api/relay/friend_request`: Push a connection request via cloud relay.

### Social & Messaging
*   `POST /api/friend_request`: Send a standard friend request.
*   `POST /api/friend_request/accept` / `decline`: Manage incoming requests.
*   `GET /api/friends/status`: Poll online status of connected peers.
*   `GET/POST /api/messages/<target_user>`: Retrieve or send direct messages.

### System Data
*   `GET /api/sys_usage`: Hardware telemetry (CPU, RAM, GPU/Disk).
*   `GET /api/relay/storage_status`: Cloud relay storage capacity metrics.
*   `GET/POST /api/storage/<key>`: Generic endpoint for saving/retrieving modular user data.

---

## ⚠️ Error Codes & Anomalies

The Nexus Experience employs a standardized error coding system for precise debugging and support.

| Code | Description | Resolution / Notes |
| :--- | :--- | :--- |
| **NX-101** | Invalid Credentials | Password or username mismatch during login or account deletion. |
| **NX-300** | Missing Credentials | Required fields (username/password) were omitted from the payload. |
| **NX-400** | Security Protocol Violation | Password does not meet minimum length (12 chars) requirements. |
| **NX-401** | Integrity Check Failed | Missing capitals, malformed Social Tag, or duplicate identity detected. |
| **NX-500** | Internal Server Error | Unhandled exception in route execution. Check `data/logs/system.log`. |

*Note: Corrupt identities (missing critical JSON fields) are handled dynamically via the UI and can be restored using the `/api/restore_corrupt` protocol.*

---

## 💻 Tech Stack & Requirements

*   **Backend:** Python 3.x, Flask, Werkzeug
*   **System Telemetry:** `psutil`
*   **Storage:** Local JSON architecture (NoSQL-style document storage)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (Jinja2 Templating)

**Dependencies:** See `requirements.txt` or `pyproject.toml` for exact versioning. (Key packages: `Flask`, `requests`, `psutil`).

---

## 🚀 Installation & Initialization

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd IMCA-NEXUS-EXPERIENCE_INDIVIDUAL-USER-SUPPORT
    ```

2.  **Environment Setup:**
    Ensure you have Python 3 installed. It is recommended to use a virtual environment or `poetry` / `uv` (as indicated by lock files in the root).
    ```bash
    pip install -r requirements.txt
    ```

3.  **Boot Sequence:**
    ```bash
    python app.py
    ```
    The Nexus will initialize on `0.0.0.0:5000`.

4.  **First Run:**
    Navigate to `http://localhost:5000`. You will be redirected to the login/setup page to create your first primary Identity.

---
<div align="center">
  <i>"System Integrity: Nominal."</i>
</div>
