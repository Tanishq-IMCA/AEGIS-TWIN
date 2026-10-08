import json
import os
import base64
import shutil
import uuid
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USERS_BASE_DIR = os.path.join(DATA_DIR, 'users')
USER_DATA_ROOT = os.path.join(DATA_DIR, 'user_data')
IDENTITY_FILE = os.path.join(DATA_DIR, 'nexus_identity.json')

def init_storage():
    for d in [DATA_DIR, USERS_BASE_DIR, USER_DATA_ROOT]:
        if not os.path.exists(d):
            os.makedirs(d)
    
    # Instant-Identity Engine
    if not os.path.exists(IDENTITY_FILE):
        adjectives = ["Solar", "Neo", "Void", "Cyber", "Eon", "Quantum"]
        nouns = ["Nexus", "Link", "Core", "Node", "Bridge", "Gate"]
        random_name = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(1000, 9999)}"
        identity = {
            "nexus_id": str(uuid.uuid4()),
            "friendly_name": random_name,
            "created_at": str(random.randint(1730000000, 1740000000)) # Placeholder timestamp
        }
        with open(IDENTITY_FILE, 'w') as f:
            json.dump(identity, f, indent=4)
        print(f"IDENTITY ENGINE: Generated new identity {random_name}")

    # Cleanup legacy data folders if they exist
    for legacy in [os.path.join(DATA_DIR, 'uploads'), os.path.join(DATA_DIR, 'storage')]:
        if os.path.exists(legacy) and os.path.isdir(legacy):
            shutil.rmtree(legacy)

def get_identity():
    if os.path.exists(IDENTITY_FILE):
        with open(IDENTITY_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_user_dir(username):
    user_dir = os.path.join(USER_DATA_ROOT, username.lower())
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        # Category subfolders for sidebar pages
        for folder in ['finance', 'health', 'tasks', 'schedule', 'calendar', 'preferences', 'uploads']:
            os.makedirs(os.path.join(user_dir, folder), exist_ok=True)
    return user_dir

def get_user_path(username):
    # Search for the profile with case-insensitive filename comparison
    username_lower = username.lower()
    if os.path.exists(USERS_BASE_DIR):
        for f in os.listdir(USERS_BASE_DIR):
            if f.lower() == f"{username_lower}.json":
                return os.path.join(USERS_BASE_DIR, f)
    # Default to lowercase if not found
    return os.path.join(USERS_BASE_DIR, f"{username_lower}.json")

def get_profile_data(username=None):
    if not username: return {}
    path = get_user_path(username)
    if not os.path.exists(path): return {}
    with open(path, 'r') as f:
        try: data = json.load(f)
        except: data = {}
    
    # Ensure name is exactly as stored in the profile
    # If missing, it will use the username provided (which might have wrong case)
    if not isinstance(data, dict): data = {"name": username}
    
    user_dir = get_user_dir(username)
    avatar_file = os.path.join(user_dir, 'uploads', 'avatar.png')
    if os.path.exists(avatar_file):
        with open(avatar_file, 'rb') as f:
            data['profile_pic'] = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    else: data['profile_pic'] = ""
    return data

def save_profile_data(username, data):
    avatar_data = data.pop('profile_pic', None)
    user_dir = get_user_dir(username)
    avatar_file = os.path.join(user_dir, 'uploads', 'avatar.png')
    
    if avatar_data:
        if 'base64' in avatar_data or avatar_data.startswith('data:image'):
            try:
                img_data = base64.b64decode(avatar_data.split(',', 1)[1])
                with open(avatar_file, 'wb') as f: f.write(img_data)
                print(f"SAVE_PROFILE: Updated avatar for {username}")
            except Exception as e: print(f"SAVE_PROFILE ERROR: {e}")
    elif avatar_data == "":
        # Explicit deletion requested
        if os.path.exists(avatar_file):
            os.remove(avatar_file)
            print(f"SAVE_PROFILE: Removed avatar for {username}")
    
    # Use existing file path if it exists to preserve case
    path = get_user_path(username)
    
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, 'r') as f: existing = json.load(f)
        except: pass
    
    # Merge data
    existing.update(data)
    
    # Critical Fix: Ensure password and security fields are never overwritten with empty values during partial updates
    for field in ['name', 'password', 'security_question', 'security_answer', 'social_tag']:
        if field in existing and (field not in data or not data[field]):
            pass # Keep existing value if new one is missing or empty
    
    with open(path, 'w') as f: json.dump(existing, f, indent=4)

def list_users():
    if not os.path.exists(USERS_BASE_DIR): return []
    # Only return users that have both a profile and a data directory
    users = []
    for f in os.listdir(USERS_BASE_DIR):
        if f.endswith('.json'):
            # The file contains the actual profile data including 'name'
            with open(os.path.join(USERS_BASE_DIR, f), 'r') as profile_file:
                try:
                    profile = json.load(profile_file)
                    profile_name = profile.get('name', f[:-5])
                    if os.path.exists(os.path.join(USER_DATA_ROOT, profile_name.lower())):
                        users.append(profile_name)
                except:
                    pass
    return users

def delete_user(username):
    if not username: 
        return False, "NX-300"
    
    username_clean = username.lower().strip()
    profile_path = os.path.join(USERS_BASE_DIR, f"{username_clean}.json")
    user_dir = os.path.join(USER_DATA_ROOT, username_clean)
    
    try:
        # 1. Delete the JSON profile
        if os.path.exists(profile_path):
            os.remove(profile_path)
            print(f"DELETE_USER: Removed profile {profile_path}")
            
        # 2. Delete the user data directory
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            print(f"DELETE_USER: Removed directory {user_dir}")
            
        # 3. Clean up any case-insensitive variants just to be safe
        if os.path.exists(USERS_BASE_DIR):
            for f in os.listdir(USERS_BASE_DIR):
                if f.lower() == f"{username_clean}.json":
                    os.remove(os.path.join(USERS_BASE_DIR, f))
        
        # Verify both are gone
        if os.path.exists(profile_path) or os.path.exists(user_dir):
            return False, "NX-302"
            
        return True, None
    except Exception as e:
        print(f"DELETE_USER ERROR: {e}")
        return False, "NX-301"

def get_data_path(username, key):
    user_dir = get_user_dir(username)
    # Map common keys to their respective folders
    category_map = {
        'goals': 'tasks',
        'tasks': 'tasks',
        'finances': 'finance',
        'health_metrics': 'health',
        'schedule_data': 'schedule',
        'calendar_events': 'calendar',
        'settings': 'preferences'
    }
    category = category_map.get(key, 'preferences')
    return os.path.join(user_dir, category, f"{key}.json")

def save_data(username, key, data):
    if not username: return
    path = get_data_path(username, key)
    # Ensure directory exists before writing
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=4)

def get_data(username, key):
    if not username: return []
    path = get_data_path(username, key)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data if data is not None else []
        except Exception as e:
            print(f"Error loading {key} for {username}: {e}")
            return []
    return []
