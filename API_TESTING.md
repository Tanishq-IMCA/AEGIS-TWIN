# API Testing Guide

This guide covers running the Flask app and testing its current HTTP API from the PyCharm or VS Code debugger. The API routes below are defined in `app.py`; dispatch and trailer behavior is implemented in `dispatch_engine.py`.

## 1. Start the app

1. Open the project root (the folder containing `app.py`) in PyCharm or VS Code.
2. Install the project dependencies in that Python environment:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the run/debug target as `app.py`, with the project root as its working directory. The app listens on port `5000` by default.
4. Run it under the debugger. In Replit, use the **Start application** workflow and the Preview pane.
5. Use the appropriate base URL:

   ```text
   Local:   http://127.0.0.1:5000
   Replit:  the app's Preview URL
   ```

Replit requires its configured `DATABASE_URL` and `SESSION_SECRET`. Do not put credentials in source files or commit them. Outside Replit, the app can use its local SQLite login database when `DATABASE_URL` is not set.

## 2. Set breakpoints and inspect requests

1. Set a breakpoint inside the route handler you want to test in `app.py` (or the corresponding function in `dispatch_engine.py`).
2. Start `app.py` with **Debug**.
3. Send a request using one of the methods below. The request pauses at the breakpoint in the server process.
4. Inspect `request.method`, `request.path`, `request.args`, `request.get_json(silent=True)`, `session`, and local variables.
5. Step through the handler, then inspect the HTTP status and JSON response in the client.

### PyCharm

Create a **Python** Run/Debug Configuration with:

- Script path: `<project root>/app.py`
- Working directory: `<project root>`
- Parameters: leave blank
- Environment: use the Replit-managed environment when debugging there; never copy secrets into a checked-in run configuration

Click **Debug**. For an external client script, create a second Python configuration for that script and run it while the app remains in Debug.

### VS Code

Install/select the Python extension and interpreter, then create a Python launch configuration (`Run and Debug` → `create a launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Flask app.py",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/app.py",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

Start **Flask app.py** with F5. Send requests from the Thunder Client extension, a `.http` request file, `curl`, or a separate Python client while the debugger is running.

## 3. Send requests and keep the login session

JSON endpoints expect `Content-Type: application/json`; use a client session so the login cookie is reused. The app permits account creation without an existing session. Create a disposable test account once, then reuse the same session:

```python
import requests

base = "http://127.0.0.1:5000"  # replace with the Replit Preview URL when needed
client = requests.Session()

response = client.post(f"{base}/api/users", json={
    "username": "api_test_user",
    "password": "DebuggerTestPass123",
    "confirm_password": "DebuggerTestPass123",
    "social_user": "TestUser",
    "social_num": "4827",
    "security_question": "Test question",
    "security_answer": "test answer"
})
print(response.status_code, response.json())

# Same client retains the session cookie created by account registration.
response = client.get(f"{base}/api/profile")
print(response.status_code, response.json())
```

Choose a new username and unused four-digit social number if registration reports a duplicate. Passwords must be at least 12 characters and include an uppercase letter. Alternatively, log in with an existing test account:

```python
client.post(f"{base}/api/login", json={
    "username": "api_test_user",
    "password": "DebuggerTestPass123"
})
```

`requests.Session()` retains cookies automatically. In an IDE HTTP client, keep the cookie returned by registration/login and send it with later authenticated requests. If an API request unexpectedly returns a login page or redirect, first check that the client retained this cookie.

## 4. API route reference

All paths are relative to the base URL. Unless noted, endpoints other than account registration/login and heartbeat require an authenticated session. Requests with a JSON body should use `json={...}` in Python or **Body → JSON** in an HTTP client.

### Accounts and profile

| Method | Path | Purpose / request body |
| --- | --- | --- |
| `GET` | `/api/users` | List local user names. |
| `POST` | `/api/users` | Register and sign in. JSON: `username`, `password`, `confirm_password`, `social_user` (letters only), `social_num` (four digits), `security_question`, `security_answer`; optional `avatar`. |
| `POST` | `/api/login` | Sign in. JSON: `username`, `password`. |
| `POST` | `/api/restore_corrupt` | Repair an identity. JSON: `user_id`, `new_password` (at least 12 characters and one uppercase letter). |
| `POST` | `/api/delete_account` | Delete account data. JSON: `username`, `password`. **Destructive; use only a disposable test account.** |
| `POST` | `/api/delete_account_no_pass` | Delete the currently signed-in account. **Destructive; use only a disposable test account.** |
| `GET` | `/api/profile` | Read the signed-in user's profile. |
| `POST` | `/api/profile` | Save profile fields as JSON. Optional `password` changes the password and must meet the password rules. |

### Dispatch and fleet

| Method | Path | Purpose / request body |
| --- | --- | --- |
| `GET` | `/api/dispatch?catalog=1` | Read the warehouse and destination catalog used by dispatch requests. |
| `GET` | `/api/dispatch` | Read the signed-in user's dispatch state and notices. |
| `POST` | `/api/dispatch` | Create a dispatch. JSON: `origin_id`, `destination_id`, using IDs from the catalog response. |
| `POST` | `/api/dispatch/<dispatch_id>/assistance` | Request roadside assistance for a dispatch that needs assistance. No body. |
| `POST` | `/api/dispatch/<dispatch_id>/resume` | Resume a dispatch. No body. |
| `POST` | `/api/dispatch/<dispatch_id>/cancel` | Cancel a dispatch. No body. |
| `GET` | `/api/engine/logs?limit=150&after=<cursor>` | Read dispatch logs; `limit` is capped at 500 and `after` is optional. |
| `GET` | `/api/trailers` | List trailers and valid warehouse IDs. |
| `POST` | `/api/trailers` | Add a trailer. JSON: `id`, `type`, `hub` (a warehouse ID from the GET response). |
| `PATCH` | `/api/trailers/<trailer_id>` | Update trailer JSON. Supported fields: `status` (`available`, `assigned`, or `maintenance`) and `hub` (valid warehouse ID). |
| `DELETE` | `/api/trailers/<trailer_id>` | Delete a trailer. **Use only test trailer records.** |

### Bridge, relay, social, and messages

| Method | Path | Purpose / request body |
| --- | --- | --- |
| `POST` | `/api/bridge/receive` | Receive a bridge packet. JSON: `target_user`, `sender_user`, `sender_tag`, `type`, and optional `payload`. |
| `GET` | `/api/bridge/config` | Read the bridge partner URL. |
| `POST` | `/api/bridge/config` | Save JSON: `partner_url`. |
| `GET` | `/api/bridge/status` | Read bridge/relay status; may check a configured partner URL. |
| `GET` | `/api/heartbeat` | Health check; returns active status and a timestamp. |
| `GET` | `/api/friends/status` | Read friend online statuses. |
| `POST` | `/api/friend_request` | Send a friend request. JSON: `target_tag`. |
| `POST` | `/api/friend_request/accept` | Accept a friend request. The current handler returns success without processing a request body. |
| `POST` | `/api/friend_request/decline` | Decline a friend request. The current handler returns success without processing a request body. |
| `GET` | `/api/relay/storage_status` | Read relay storage status; returns inactive when cloud relay is not configured. |
| `GET` | `/api/relay/discovery` | List relay peers; returns an empty list when relay is inactive. |
| `POST` | `/api/relay/friend_request` | Send a relay request. JSON: `target_nexus_id`; requires an active relay service. |
| `GET` | `/api/messages/<target_user>` | Read the conversation with the target user. |
| `POST` | `/api/messages/<target_user>` | Send a message. JSON: `message`; may attempt relay/bridge delivery. |

### Storage, telemetry, and logs

| Method | Path | Purpose / request body |
| --- | --- | --- |
| `GET` | `/api/sys_usage` | Read CPU, RAM, and disk usage. |
| `GET` | `/api/storage/<key>` | Read the signed-in user's JSON data for a key, such as `tasks` or `calendar_events`. |
| `POST` | `/api/storage/<key>` | Save JSON: `data` (the value to store for that key). |
| `POST` | `/api/logs` | Write a log message. JSON: `message`; optional `type` (`info`, `warn`, or `error`). |

## 5. Quick smoke checks

With the app running, these requests check basic availability:

```bash
curl -i http://127.0.0.1:5000/api/heartbeat
curl -i http://127.0.0.1:5000/api/users
```

After registration/login, use the same cookie-aware client for authenticated endpoints:

```python
for path in (
    "/api/profile",
    "/api/dispatch?catalog=1",
    "/api/dispatch",
    "/api/trailers",
    "/api/sys_usage",
):
    response = client.get(base + path)
    print(response.status_code, path, response.text[:300])
```

Check status codes as well as response bodies: validation errors generally return `400`, invalid login returns `401`, successful dispatch/trailer creation returns `201`, and unexpected server errors return `500`. The relay routes depend on optional `RELAY_DB_URL` and `RELAY_DB_KEY`; without them they remain in local/inactive mode.

## 6. Test safely

- Use disposable accounts and test records. Avoid account deletion and trailer deletion against real data.
- Do not use real passwords or expose Replit secrets in debugger screenshots, logs, `.env` files committed to Git, or request examples.
- For a request that changes persisted state, verify the result with its corresponding GET endpoint.
- The dispatch engine simulates truck movement and incidents; these API responses are not live fleet telemetry.
- Record the request method, path, status code, response body, and any relevant server traceback when reporting a failure.
