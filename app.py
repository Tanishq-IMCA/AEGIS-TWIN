from dotenv import load_dotenv

load_dotenv()

import psutil
import os
import csv
import io
import secrets
import requests
import logging
import relay_manager
import threading
import time
import re
from datetime import datetime, timezone
from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for
import storage_manager
import auth_database
import difflib
import dispatch_engine

app = Flask(__name__)
session_secret = os.environ.get('SESSION_SECRET')
if not session_secret:
    if os.environ.get("REPL_ID") or os.environ.get("REPLIT_ENVIRONMENT"):
        raise RuntimeError("SESSION_SECRET must be configured.")
    session_secret = secrets.token_urlsafe(32)
    app.logger.warning("Using a temporary development session secret.")
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # Replit proxy handles SSL
    SESSION_COOKIE_HTTPONLY=True,
    SECRET_KEY=session_secret
)
storage_manager.init_storage()
auth_database.initialize()
storage_manager.migrate_legacy_accounts()
relay_service = relay_manager.RelayService()

# --- RELAY BACKGROUND SYNC ---
def background_sync():
    """Low-impact polling thread for cloud relay packets and presence."""
    while True:
        try:
            identity = storage_manager.get_identity()
            my_nexus_id = identity.get('nexus_id')
            friendly_name = identity.get('friendly_name')
            
            if my_nexus_id and relay_service.active:
                # Announce presence
                relay_service.announce_presence(my_nexus_id, friendly_name)
                
                # Pull packets
                packets = relay_service.pull(my_nexus_id)
                for packet in packets:
                    process_relay_packet(packet)
            
            time.sleep(30)
        except Exception as e:
            logging.error(f"BACKGROUND SYNC ERROR: {e}")
            time.sleep(60)

def autonomous_dispatch_sync():
    """Keep enabled fleets moving even when their dashboard is not open."""
    while True:
        try:
            for username in storage_manager.list_users():
                try:
                    dispatch_engine.autonomous_worker_tick(username)
                except Exception as error:
                    logging.error(f"AUTONOMOUS DISPATCH ERROR for {username}: {error}")
        except Exception as error:
            logging.error(f"AUTONOMOUS DISPATCH WORKER ERROR: {error}")
        time.sleep(1)

def process_relay_packet(packet):
    """Integrates relay packets into local storage."""
    try:
        sender_id = packet.get('source_nexus_id')
        msg_type = packet.get('type')
        payload = packet.get('payload', {})
        
        # We need a local user to map this to. 
        # For now, we'll map to the first available user or a system-wide log if no one is logged in.
        users = storage_manager.list_users()
        if not users:
            return
        
        target_user = users[0] # Default to first user for relay delivery
        
        notifs = storage_manager.get_data(target_user, 'notifications')
        if not isinstance(notifs, list): notifs = []
        
        notifs.append({
            'id': f"relay_{os.urandom(4).hex()}",
            'title': "RELAY PACKET",
            'message': f"Incoming {msg_type} from {sender_id}",
            'timestamp': datetime.now().isoformat(),
            'type': 'bridge',
            'read': False
        })
        storage_manager.save_data(target_user, 'notifications', notifs)
        
        if msg_type == 'message':
            chat_id = "_".join(sorted([target_user.lower(), sender_id.lower()]))
            chat_file = f"chat_{chat_id}"
            msgs = storage_manager.get_data(target_user, chat_file)
            if not isinstance(msgs, list): msgs = []
            msgs.append({
                'sender': sender_id,
                'text': payload.get('text'),
                'timestamp': datetime.now().isoformat(),
                'bridged': True,
                'relay': True
            })
            storage_manager.save_data(target_user, chat_file, msgs)
            
    except Exception as e:
        logging.error(f"PROCESS RELAY PACKET ERROR: {e}")

# Start the background thread
sync_thread = threading.Thread(target=background_sync, daemon=True)
sync_thread.start()
autonomy_thread = threading.Thread(target=autonomous_dispatch_sync, daemon=True)
autonomy_thread.start()

# --- AUTH MIDDLEWARE ---
def get_current_user():
    return session.get('user')

@app.before_request
def require_login():
    allowed_routes = ['login', 'api_users', 'do_login', 'purge_corrupt', 'static', 'heartbeat']
    if request.endpoint not in allowed_routes:
        users = storage_manager.list_users()
        if not users:
            # Failsafe: No users exist, force redirect to login/setup
            session.pop('user', None)
            return redirect(url_for('login'))
        if not get_current_user():
            return redirect(url_for('login'))

# --- ROUTES ---
@app.route('/login')
def login():
    try:
        user_names = storage_manager.list_users()
        users_list = []
        for name in user_names:
            profile = storage_manager.get_profile_data(name)
            if isinstance(profile, dict) and profile:
                # Check for corrupt data (missing critical fields)
                has_password = auth_database.has_account(name)
                has_name = profile.get('name') and len(str(profile.get('name')).strip()) > 0
                is_corrupt = not has_name or not has_password or not profile.get('theme')
                
                user_entry = {
                    'id': name,
                    'name': profile.get('name', name),
                    'profile_pic': profile.get('profile_pic', ''),
                    'corrupt': is_corrupt
                }
                users_list.append(user_entry)
            else:
                users_list.append({
                    'id': name,
                    'name': 'CORRUPT_IDENTITY',
                    'profile_pic': '',
                    'corrupt': True
                })
        return render_template('login.html', users=users_list)
    except Exception as e:
        app.logger.error(f"LOGIN ROUTE ERROR: {e}", exc_info=True)
        return "Critical system failure. Check logs.", 500

@app.route('/api/restore_corrupt', methods=['POST'])
def restore_corrupt():
    try:
        data = request.json
        user_id = data.get('user_id')
        new_password = data.get('new_password')
        
        if not user_id or not new_password:
            return jsonify({"status": "error", "message": "Missing parameters", "code": "NX-401"}), 400
            
        profile = storage_manager.get_profile_data(user_id)
        if not profile:
            profile = {}

        # Reset/Repair the profile with essential data
        profile['name'] = profile.get('name', user_id.capitalize())
        if len(new_password) < 12 or not any(c.isupper() for c in new_password):
            return jsonify({"status": "error", "message": "Password does not meet security requirements", "code": "NX-401"}), 400
        if not auth_database.set_password(user_id, new_password):
            return jsonify({"status": "error", "message": "Identity not found", "code": "NX-404"}), 404
        profile['role'] = profile.get('role', 'Restored User')
        profile['company'] = profile.get('company', 'Nexus Experience')
        profile['theme'] = profile.get('theme') or {
            "primary": "#4ADE80",
            "rgb": "74, 222, 128",
            "wallpaper": "animated"
        }
        profile.pop('password', None)
        storage_manager.save_profile_data(user_id, profile)
        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"INTERNAL SERVER ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal Server Error", "code": "NX-500"}), 500

@app.route('/api/delete_account', methods=['POST'])
def api_delete_account():
    try:
        data = request.json
        user_id = data.get('username')
        password = data.get('password')
        
        if not user_id or not password:
            return jsonify({"status": "error", "message": "Missing credentials", "code": "NX-300"}), 400
            
        if not auth_database.verify_password(user_id, password):
            return jsonify({"status": "error", "message": "Invalid password", "code": "NX-101"}), 401
        
        current_user = session.get('user')
        if current_user and user_id and isinstance(user_id, str) and current_user.lower() == user_id.lower():
            session.pop('user', None)

        # Cleanup local data
        success, code = storage_manager.delete_user(user_id)
        
        # If cloud relay is active, we could notify peer registry, but for now local cleanup is primary
        if success:
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Purge protocol failed", "code": code}), 500
    except Exception as e:
        app.logger.error(f"DELETE ACCOUNT ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal Server Error", "code": "NX-500"}), 500

@app.route('/api/delete_account_no_pass', methods=['POST'])
def delete_account_no_pass():
    try:
        username = get_current_user()
        if not username:
            return jsonify({"status": "error", "message": "Not logged in"}), 401
            
        session.pop('user', None)
        success, code = storage_manager.delete_user(username)
        if success:
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Purge failed", "code": code}), 500
    except Exception as e:
        app.logger.error(f"PURGE NO PASS ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    try:
        if request.method == 'POST':
            data = request.json
            username = data.get('username')
            username = username.strip() if isinstance(username, str) else ''
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,40}', username):
                return jsonify({"status": "error", "message": "Username must be 1–40 letters, numbers, dots, dashes, or underscores.", "code": "NX-401"}), 400
            social_user = data.get('social_user', '').strip()
            social_num = data.get('social_num', '').strip()
            password = data.get('password')
            
            if not username or not social_user or not social_num or not password:
                return jsonify({"status": "error", "message": "Credentials and Social Tag required", "code": "NX-401"}), 400
            
            if not social_user.isalpha():
                return jsonify({"status": "error", "message": "Social Username: Letters only.", "code": "NX-401"}), 400
            
            if not social_num.isdigit() or len(social_num) != 4:
                return jsonify({"status": "error", "message": "Social Number: Must be exactly 4 digits.", "code": "NX-401"}), 400

            social_tag = f"{social_user}#{social_num}"
            
            security_question = data.get('security_question')
            security_answer = data.get('security_answer')
            avatar = data.get('avatar')
            confirm_password = data.get('confirm_password')

            all_users = storage_manager.list_users()
            for u in all_users:
                u_profile = storage_manager.get_profile_data(u)
                if u_profile and u_profile.get('social_tag', '').lower() == social_tag.lower():
                     return jsonify({"status": "error", "message": "Social Tag already taken by another identity.", "code": "NX-401"}), 400

            if not security_question or not security_answer:
                return jsonify({"status": "error", "message": "Security question and answer required.", "code": "NX-401"}), 400

            if len(password) < 12:
                return jsonify({"status": "error", "message": "Security protocol requires minimum 12 characters.", "code": "NX-400"}), 400
            if not any(c.isupper() for c in password):
                return jsonify({"status": "error", "message": "Integrity check failed: At least 1 capital letter required.", "code": "NX-401"}), 400
            
            if password != confirm_password:
                return jsonify({"status": "error", "message": "Passwords do not match", "code": "NX-401"}), 400
            
            if username.lower() in [u.lower() for u in storage_manager.list_users()]:
                return jsonify({"status": "error", "message": "User exists", "code": "NX-401"}), 400

            default_profile = {
                "name": username,
                "social_tag": social_tag,
                "role": "New User",
                "company": "Nexus Experience",
                "email": "",
                "profile_pic": avatar,
                "security_question": security_question,
                "security_answer": security_answer,
                "theme": {
                    "primary": "#4ADE80",
                    "rgb": "74, 222, 128",
                    "wallpaper": "animated"
                }
            }
            if not auth_database.create_account(username, password):
                return jsonify({"status": "error", "message": "User exists", "code": "NX-401"}), 400
            try:
                storage_manager.save_profile_data(username, default_profile)
            except Exception:
                auth_database.delete_account(username)
                raise
            session['user'] = username
            return jsonify({"status": "success"})
        return jsonify(storage_manager.list_users())
    except Exception as e:
        app.logger.error(f"INTERNAL SERVER ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal Server Error", "code": "NX-500"}), 500

@app.route('/api/login', methods=['POST'])
def do_login():
    try:
        data = request.get_json(silent=True) or {}
        username = data.get('username')
        password = data.get('password')

        if auth_database.verify_password(username, password):
            profile = storage_manager.get_profile_data(username)
            session['user'] = profile.get('name', username)
            return jsonify({"status": "success"})
            
        return jsonify({"status": "error", "message": "Invalid credentials", "code": "NX-101"}), 401
    except Exception as e:
        app.logger.error(f"INTERNAL SERVER ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal Server Error", "code": "NX-500"}), 500

@app.route('/api/bridge/receive', methods=['POST'])
def bridge_receive():
    try:
        data = request.json
        target_username = data.get('target_user')
        sender_username = data.get('sender_user')
        sender_tag = data.get('sender_tag')
        payload = data.get('payload', {})
        message_type = data.get('type')

        if not target_username or not message_type:
            return jsonify({"status": "error", "message": "Malformed bridge packet"}), 400

        # Add notification for incoming link/message
        notifs = storage_manager.get_data(target_username, 'notifications')
        if not isinstance(notifs, list): notifs = []
        
        notif_msg = f"Incoming bridge link from {sender_username}"
        if message_type == 'message':
            notif_msg = f"New message from {sender_username} via Bridge"
            
        notifs.append({
            'id': f"br_notif_{os.urandom(4).hex()}",
            'title': "NEXUS BRIDGE",
            'message': notif_msg,
            'timestamp': datetime.now().isoformat(),
            'type': 'bridge',
            'read': False
        })
        storage_manager.save_data(target_username, 'notifications', notifs)

        if message_type == 'message':
            username_lower = target_username.lower() if target_username else ""
            sender_lower = sender_username.lower() if sender_username else ""
            if username_lower and sender_lower:
                chat_id = "_".join(sorted([username_lower, sender_lower]))
                chat_file = f"chat_{chat_id}"
                
                msgs = storage_manager.get_data(target_username, chat_file)
                if not isinstance(msgs, list):
                    msgs = []
                msgs.append({
                    'sender': sender_username,
                    'text': payload.get('text'),
                    'timestamp': datetime.now().isoformat(),
                    'bridged': True
                })
                storage_manager.save_data(target_username, chat_file, msgs)
        
        elif message_type == 'friend_request':
            reqs = storage_manager.get_data(target_username, 'friend_requests')
            if not any(r.get('from') == sender_username for r in reqs):
                reqs.append({
                    'id': f"br_{os.urandom(4).hex()}",
                    'from': sender_username,
                    'from_tag': sender_tag,
                    'timestamp': datetime.now().isoformat(),
                    'bridged': True
                })
                storage_manager.save_data(target_username, 'friend_requests', reqs)

        elif message_type == 'task':
            tasks = storage_manager.get_data(target_username, 'tasks')
            tasks.append({
                'id': f"br_{os.urandom(4).hex()}",
                'title': payload.get('title'),
                'description': payload.get('description'),
                'sender': sender_username,
                'bridged': True
            })
            storage_manager.save_data(target_username, 'tasks', tasks)

        elif message_type == 'calendar':
            events = storage_manager.get_data(target_username, 'calendar_events')
            events.append({
                'id': f"br_{os.urandom(4).hex()}",
                'title': payload.get('title'),
                'date': payload.get('date'),
                'sender': sender_username,
                'bridged': True
            })
            storage_manager.save_data(target_username, 'calendar_events', events)

        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"BRIDGE RECEIVE ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Bridge transmission failed"}), 500

@app.route('/api/bridge/config', methods=['GET', 'POST'])
def bridge_config():
    try:
        username = get_current_user()
        if request.method == 'POST':
            data = request.json
            partner_url = data.get('partner_url', '').strip()
            storage_manager.save_data(username, 'bridge_config', {'partner_url': partner_url})
            return jsonify({"status": "success"})
        
        config = storage_manager.get_data(username, 'bridge_config')
        return jsonify(config or {'partner_url': ''})
    except Exception as e:
        app.logger.error(f"BRIDGE CONFIG ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

def transmit_via_bridge(username, target_user, payload, msg_type):
    try:
        # Priority: Cloud Relay
        if relay_service.active:
            # In Phase 2, we use target_user as the Nexus ID
            success, err = relay_service.push(target_user, storage_manager.get_identity().get('nexus_id'), payload, msg_type)
            if success:
                return True, None
            # If relay fails, it might fall through to legacy direct bridge

        config = storage_manager.get_data(username, 'bridge_config')
        partner_url = config.get('partner_url') if isinstance(config, dict) else None
        
        if not partner_url:
            return False, "Bridge not configured"
        
        profile = storage_manager.get_profile_data(username)
        if not profile:
            profile = {}
        
        if not partner_url.startswith('http'):
            partner_url = f"https://{partner_url}"
        
        endpoint = f"{partner_url.rstrip('/')}/api/bridge/receive"
        resp = requests.post(endpoint, json={
            'target_user': target_user,
            'sender_user': username,
            'sender_tag': profile.get('social_tag'),
            'type': msg_type,
            'payload': payload
        }, timeout=5)
        return resp.status_code == 200, None
    except Exception as e:
        app.logger.error(f"BRIDGE TRANSMIT ERROR: {str(e)}", exc_info=True)
        return False, str(e)

@app.route('/api/bridge/status')
def bridge_status():
    partner_url = None
    try:
        username = get_current_user()
        config = storage_manager.get_data(username, 'bridge_config')
        partner_url = config.get('partner_url') if isinstance(config, dict) else None
        
        status = {
            'internet': True,
            'bridge_active': relay_service.active,
            'partner_online': relay_service.active, # In Relay Mode, if the service is active, we consider the "link" online
            'partner_url_configured': partner_url,
            'relay_mode': relay_service.active
        }
        
        if not relay_service.active and partner_url:
            # Legacy direct bridge check if relay is not active
            try:
                clean_url = partner_url.strip().rstrip('/')
                if not clean_url.startswith('http'):
                    clean_url = f"https://{clean_url}"
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache',
                    'Connection': 'close'
                }
                with requests.Session() as s:
                    resp = s.get(f"{clean_url}/api/heartbeat", timeout=5, headers=headers)
                    if resp.status_code == 200:
                        status['bridge_active'] = True
                        status['partner_online'] = resp.json().get('status') == 'active'
            except Exception as e:
                status['error_msg'] = str(e)
                
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"BRIDGE STATUS ERROR: {str(e)}", exc_info=True)
        return jsonify({
            'internet': True,
            'bridge_active': False,
            'partner_online': False,
            'partner_url_configured': partner_url,
            'error_msg': str(e)
        })

@app.route('/api/heartbeat')
def heartbeat():
    # Adding a log to see if this is being called
    app.logger.info("Heartbeat requested")
    return jsonify({'status': 'active', 'timestamp': datetime.now().isoformat()})

@app.route('/api/friends/status')
def friends_status():
    try:
        username = get_current_user()
        friends = storage_manager.get_data(username, 'friends')
        config = storage_manager.get_data(username, 'bridge_config')
        partner_url = config.get('partner_url') if isinstance(config, dict) else None
        
        friend_statuses = {}
        for friend in (friends or []):
            friend_statuses[friend] = 'offline'
            
        if partner_url:
            try:
                if not partner_url.startswith('http'):
                    partner_url = f"https://{partner_url}"
                resp = requests.get(f"{partner_url.rstrip('/')}/api/heartbeat", timeout=2)
                if resp.status_code == 200:
                    for friend in (friends or []):
                        friend_statuses[friend] = 'online'
            except:
                pass
                
        return jsonify(friend_statuses)
    except Exception as e:
        app.logger.error(f"FRIENDS STATUS ERROR: {str(e)}", exc_info=True)
        return jsonify({}), 500

@app.route('/logout')
def logout():
    try:
        return render_template('logout_confirm.html')
    except Exception as e:
        app.logger.error(f"Logout template error: {e}")
        session.clear()
        return redirect(url_for('login'))

@app.route('/api/friend_request', methods=['POST'])
def send_friend_request():
    try:
        username = get_current_user()
        data = request.json
        target_tag = data.get('target_tag')
        
        if not target_tag:
            return jsonify({"status": "error", "message": "Target tag required"}), 400
            
        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"FRIEND REQUEST ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

@app.route('/api/friend_request/accept', methods=['POST'])
def accept_friend_request():
    return jsonify({"status": "success"})

@app.route('/api/friend_request/decline', methods=['POST'])
def decline_friend_request():
    return jsonify({"status": "success"})

@app.route('/logout/confirm')
def logout_action():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    return render_template(
        'dashboard.html',
        title="IMCA NEXUS DASHBOARD",
        # Keep provider credentials in Replit Secrets or local .env; never hard-code or commit them.
        carto_api_key=os.environ.get("CARTO_BASEMAPS_API_KEY", ""),
    )

@app.route('/api/profile', methods=['GET'])
def get_profile():
    try:
        username = get_current_user()
        profile = storage_manager.get_profile_data(username)
        if 'role' not in profile:
            profile['role'] = 'User'
        return jsonify(profile)
    except Exception as e:
        app.logger.error(f"GET PROFILE ERROR: {e}")
        return jsonify({}), 500

@app.route('/api/profile', methods=['POST'])
def save_profile():
    try:
        username = get_current_user()
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        existing = storage_manager.get_profile_data(username)
        if not isinstance(existing, dict):
            existing = {}
        new_password = data.pop('password', None)
        if new_password:
            if len(new_password) < 12 or not any(c.isupper() for c in new_password):
                return jsonify({"status": "error", "message": "Password does not meet security requirements"}), 400
            if not auth_database.set_password(username, new_password):
                return jsonify({"status": "error", "message": "Account not found"}), 404
        data.pop('password_hash', None)
        if not data.get('security_question') and existing.get('security_question'):
            data['security_question'] = existing['security_question']
        if not data.get('security_answer') and existing.get('security_answer'):
            data['security_answer'] = existing['security_answer']
            
        storage_manager.save_profile_data(username, data)
        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"SAVE PROFILE ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

@app.route('/trailers')
def trailers_page():
    return render_template('trailers.html', title="Trailer Availability")

@app.route('/finances')
def finances():
    return redirect(url_for('analytics_page'))

@app.route('/analytics')
def analytics_page():
    return render_template('finances.html', title="Fleet Analytics")

@app.route('/api/analytics')
def analytics_api():
    try:
        return jsonify(dispatch_engine.get_analytics(get_current_user()))
    except Exception:
        app.logger.exception("ANALYTICS API ERROR")
        return jsonify({"error": "Fleet analytics are temporarily unavailable."}), 500

@app.route('/analytics.csv')
def analytics_csv():
    try:
        data = dispatch_engine.get_analytics(get_current_user())
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([
            "recorded_at_utc", "status", "truck_id", "origin", "destination",
            "distance_miles", "fuel_gallons", "revenue_usd", "fuel_cost_usd",
            "delivery_operating_cost_usd", "net_profit_usd", "time_saved_minutes",
            "overspeed_time_saved_minutes", "overspeed_event",
        ])
        for item in data["records"]:
            try:
                recorded = datetime.fromtimestamp(
                    float(item.get("recorded_at", 0)), timezone.utc
                ).isoformat(timespec="seconds")
            except (TypeError, ValueError, OSError):
                recorded = ""
            writer.writerow([
                recorded, item.get("status", ""), item.get("truck_id", ""),
                item.get("origin", ""), item.get("destination", ""),
                item.get("distance_miles", 0), item.get("fuel_gallons", 0),
                item.get("revenue", 0), item.get("fuel_cost", 0),
                item.get("operating_cost", 0), item.get("profit", 0),
                item.get("time_saved_minutes", 0),
                item.get("overspeed_time_saved_minutes", 0),
                item.get("overspeed_event", False),
            ])
        response = Response(output.getvalue(), mimetype="text/csv")
        disposition = "attachment" if request.args.get("download") == "1" else "inline"
        response.headers["Content-Disposition"] = f'{disposition}; filename="aegis-delivery-analytics.csv"'
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception:
        app.logger.exception("ANALYTICS CSV ERROR")
        return jsonify({"error": "The delivery CSV could not be generated."}), 500

@app.route('/api/relay/storage_status')
def relay_storage_status():
    if not relay_service.active:
        return jsonify({"active": False})
    
    # In a real Supabase/Postgres scenario, we'd query pg_database_size
    # For this dashboard's presentation, we'll show the Relay Cloud capacity
    # Supabase free tier is usually 500MB
    try:
        # Mocking the calculation for UI purposes based on common Supabase limits
        # since we don't want to run heavy admin queries on a free tier
        total_capacity = 500 * 1024 * 1024  # 500MB in bytes
        
        # Estimate usage based on local cache or a simple count if possible
        # For now, providing a realistic "Cloud Relay" storage metric
        used_bytes = 1024 * 450 # placeholder for "active metadata"
        
        return jsonify({
            "active": True,
            "total": total_capacity,
            "used": used_bytes,
            "percent": round((used_bytes / total_capacity) * 100, 2),
            "provider": "Supabase Cloud"
        })
    except Exception as e:
        return jsonify({"active": False, "error": str(e)})

@app.route('/settings')
def settings():
    try:
        username = get_current_user()
        user = storage_manager.get_profile_data(username)
        return render_template('settings.html', title="System Config", user=user)
    except Exception as e:
        app.logger.error(f"SETTINGS ROUTE ERROR: {e}")
        return "Error loading settings.", 500

@app.route('/manifest')
def manifest():
    return render_template('tasks.html', title="Manifest")

@app.route('/tasks')
def tasks():
    return redirect(url_for('manifest'))

@app.route('/calendar')
def calendar():
    return render_template('calendar.html', title="Temporal Logistics")

@app.route('/control-panel')
def control_panel():
    return render_template('control_panel.html', title="Dispatch Control Panel")

@app.route('/logs')
def engine_logs_page():
    return render_template('engine_logs.html', title="Engine Logs")

@app.route('/api/dispatch', methods=['GET', 'POST'])
def dispatch_api():
    username = get_current_user()
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            dispatch = dispatch_engine.create_dispatch(
                username,
                payload.get('origin_id'),
                payload.get('destination_id'),
            )
            return jsonify({"dispatch": dispatch}), 201

        if request.args.get("catalog") == "1":
            return jsonify({"catalog": dispatch_engine.catalog()})
        state, _ = dispatch_engine.get_state(username)
        notices, cursor = dispatch_engine.get_notices_since(
            username, request.args.get("notice_after")
        )
        return jsonify({**state, "notices": notices, "notice_cursor": cursor})
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        app.logger.exception("DISPATCH API ERROR")
        return jsonify({"error": "Dispatch control is temporarily unavailable."}), 500

@app.route('/api/dispatch/autonomy', methods=['GET', 'PATCH'])
def dispatch_autonomy_api():
    username = get_current_user()
    try:
        if request.method == 'PATCH':
            settings = dispatch_engine.update_autonomy(
                username, request.get_json(silent=True) or {}
            )
        else:
            settings = dispatch_engine.get_autonomy(username)
        return jsonify({"autonomy": settings})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("DISPATCH AUTONOMY ERROR")
        return jsonify({"error": "Autonomous dispatch settings are unavailable."}), 500

@app.route('/api/dispatch/<dispatch_id>/assistance', methods=['POST'])
def dispatch_assistance(dispatch_id):
    try:
        dispatch = dispatch_engine.request_assistance(get_current_user(), dispatch_id)
        return jsonify({"dispatch": dispatch})
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("ROADSIDE ASSISTANCE ERROR")
        return jsonify({"error": "Could not request roadside assistance."}), 500

@app.route('/api/dispatch/<dispatch_id>/resume', methods=['POST'])
def resume_dispatch(dispatch_id):
    try:
        dispatch = dispatch_engine.resume_dispatch(get_current_user(), dispatch_id)
        return jsonify({"dispatch": dispatch})
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("DISPATCH RESUME ERROR")
        return jsonify({"error": "Could not resume this dispatch."}), 500

@app.route('/api/dispatch/<dispatch_id>/cancel', methods=['POST'])
def cancel_dispatch(dispatch_id):
    try:
        return jsonify({"dispatch": dispatch_engine.cancel_dispatch(get_current_user(), dispatch_id)})
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("DISPATCH CANCEL ERROR")
        return jsonify({"error": "Could not cancel this dispatch."}), 500

@app.route('/api/engine/logs')
def engine_logs_api():
    try:
        limit = max(1, min(int(request.args.get("limit", 150)), 500))
        entries = dispatch_engine.get_logs(
            get_current_user(), request.args.get("after"), limit
        )
        return jsonify({"entries": entries, "cursor": entries[-1]["id"] if entries else request.args.get("after")})
    except Exception:
        app.logger.exception("ENGINE LOGS ERROR")
        return jsonify({"error": "Engine logs are unavailable."}), 500

@app.route('/api/trailers', methods=['GET', 'POST'])
def trailers_api():
    username = get_current_user()
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            trailer = dispatch_engine.add_trailer(
                username, payload.get("id"), payload.get("type"), payload.get("hub")
            )
            return jsonify({"trailer": trailer}), 201
        return jsonify({
            "trailers": dispatch_engine.list_trailers(username),
            "warehouses": dispatch_engine.catalog()["warehouses"],
        })
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("TRAILER API ERROR")
        return jsonify({"error": "Trailer records are unavailable."}), 500

@app.route('/api/trailers/<trailer_id>', methods=['PATCH', 'DELETE'])
def trailer_api(trailer_id):
    try:
        if request.method == 'DELETE':
            dispatch_engine.delete_trailer(get_current_user(), trailer_id)
            return jsonify({"status": "deleted"})
        trailer = dispatch_engine.update_trailer(
            get_current_user(), trailer_id, request.get_json(silent=True) or {}
        )
        return jsonify({"trailer": trailer})
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        app.logger.exception("TRAILER UPDATE ERROR")
        return jsonify({"error": "Could not update this trailer."}), 500

@app.route('/api/relay/discovery')
def discovery():
    if not relay_service.active:
        return jsonify([])
    peers = relay_service.get_peers()
    # Filter out self
    my_id = storage_manager.get_identity().get('nexus_id')
    available = [p for p in peers if p.get('nexus_id') != my_id]
    return jsonify(available)

@app.route('/api/relay/friend_request', methods=['POST'])
def relay_friend_request():
    try:
        data = request.json
        target_nexus_id = data.get('target_nexus_id')
        my_identity = storage_manager.get_identity()
        
        success, err = relay_service.push(
            target_nexus_id, 
            my_identity.get('nexus_id'), 
            {"friendly_name": my_identity.get('friendly_name')}, 
            'friend_request'
        )
        if success:
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": err}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sys_usage')
def sys_usage():
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        gpu = psutil.disk_usage('/').percent
        return jsonify({'cpu': cpu, 'ram': ram, 'gpu': gpu})
    except Exception as e:
        return jsonify({'cpu': 0, 'ram': 0, 'gpu': 0, 'offline': True})

@app.route('/api/storage/<key>', methods=['GET', 'POST'])
def handle_storage(key):
    try:
        username = get_current_user()
        if request.method == 'POST':
            data = request.json.get('data')
            storage_manager.save_data(username, key, data)
            return jsonify({"status": "success"})
        
        data = storage_manager.get_data(username, key)
        if key == 'notifications' and not data:
            return jsonify([])
        if key == 'friend_requests' and not data:
            return jsonify([])
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"STORAGE ERROR: {str(e)}", exc_info=True)
        return jsonify({}), 500

LOG_DIR = 'data/logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
log_file = os.path.join(LOG_DIR, 'system.log')

if not os.environ.get("WERKZEUG_RUN_MAIN"):
    if os.path.exists(log_file):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.rename(log_file, os.path.join(LOG_DIR, f"system_{timestamp}.log"))
        except Exception as e:
            print(f"Failed to rotate log: {e}")

handler = logging.FileHandler(log_file, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/api/logs', methods=['POST'])
def save_logs():
    try:
        data = request.json
        if not data: return jsonify({"status": "error"}), 400
        msg = data.get('message', '')
        level_str = data.get('type', 'info').upper()
        level = logging.INFO
        if level_str == 'ERROR': level = logging.ERROR
        elif level_str == 'WARN': level = logging.WARNING
        logging.log(level, msg)
        return jsonify({"status": "logged"})
    except:
        return jsonify({"status": "error"}), 500

@app.route('/api/messages/<target_user>', methods=['POST'])
def send_message(target_user):
    try:
        username = get_current_user()
        data = request.json
        text = data.get('message')
        
        username_lower = username.lower()
        target_lower = target_user.lower()
        chat_id = "_".join(sorted([username_lower, target_lower]))
        chat_file = f"chat_{chat_id}"
        
        msgs = storage_manager.get_data(username, chat_file)
        if not isinstance(msgs, list): msgs = []
        
        msgs.append({
            'sender': username,
            'text': text,
            'timestamp': datetime.now().isoformat(),
            'bridged': False
        })
        storage_manager.save_data(username, chat_file, msgs)
        
        # Relay to cloud
        success, error = False, "Relay inactive"
        if relay_service.active:
            success, error = relay_service.push(
                target_user,
                storage_manager.get_identity().get('nexus_id'),
                {"text": text},
                'message'
            )
        
        # Fallback to direct bridge if relay inactive or failed
        if not success:
            success, error = transmit_via_bridge(username, target_user, {'text': text}, 'message')
            
        return jsonify({"status": "success", "bridged": success, "error": error})
    except Exception as e:
        app.logger.error(f"SEND MESSAGE ERROR: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500

@app.route('/api/messages/<target_user>', methods=['GET'])
def get_messages(target_user):
    try:
        username = get_current_user()
        if not username:
            return jsonify([])
        username_lower = username.lower()
        target_lower = target_user.lower()
        chat_id = "_".join(sorted([username_lower, target_lower]))
        chat_file = f"chat_{chat_id}"
        msgs = storage_manager.get_data(username, chat_file)
        return jsonify(msgs or [])
    except Exception as e:
        app.logger.error(f"GET MESSAGES ERROR: {str(e)}", exc_info=True)
        return jsonify([]), 500

if __name__ == '__main__':
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
        use_reloader=False,
    )
