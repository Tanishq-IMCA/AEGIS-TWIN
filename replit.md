# Replit run and data rules

- Run the Flask app from the workspace root with `python app.py`; the preview serves on port 5000.
- The app requires Replit's `DATABASE_URL` and the `SESSION_SECRET` secret.
- PostgreSQL is only for login accounts in `nexus_login_accounts` (username and password hash). Do not add app profile, task, finance, health, chat, or other product data to PostgreSQL.
- Non-login app data continues using the existing local JSON storage in `data/user_data/`.
