"""Small, persistent Seattle dispatch simulator for the control panel."""

import math
import random
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from threading import RLock

import requests
import storage_manager


WAREHOUSES = [
    {"id": "sodo", "name": "SODO DISTRIBUTION HUB", "lat": 47.5805, "lng": -122.3317},
    {"id": "northgate", "name": "NORTHGATE LOGISTICS HUB", "lat": 47.7065, "lng": -122.3260},
]

DESTINATIONS = [
    {"id": "ballard", "name": "Ballard", "lat": 47.6687, "lng": -122.3860},
    {"id": "fremont", "name": "Fremont", "lat": 47.6503, "lng": -122.3500},
    {"id": "seattle-center", "name": "Seattle Center", "lat": 47.6219, "lng": -122.3500},
    {"id": "pike-place", "name": "Pike Place Market", "lat": 47.6094, "lng": -122.3420},
    {"id": "capitol-hill", "name": "Capitol Hill", "lat": 47.6233, "lng": -122.3210},
    {"id": "university-district", "name": "University District", "lat": 47.6613, "lng": -122.3130},
    {"id": "green-lake", "name": "Green Lake", "lat": 47.6803, "lng": -122.3270},
    {"id": "west-seattle", "name": "West Seattle", "lat": 47.5601, "lng": -122.3860},
    {"id": "georgetown", "name": "Georgetown", "lat": 47.5447, "lng": -122.3210},
    {"id": "rainier-valley", "name": "Rainier Valley", "lat": 47.5630, "lng": -122.2910},
    {"id": "queen-anne", "name": "Queen Anne", "lat": 47.6376, "lng": -122.3570},
    {"id": "magnolia", "name": "Magnolia", "lat": 47.6482, "lng": -122.3990},
    {"id": "beacon-hill", "name": "Beacon Hill", "lat": 47.5780, "lng": -122.3100},
    {"id": "columbia-city", "name": "Columbia City", "lat": 47.5572, "lng": -122.2850},
    {"id": "northgate", "name": "Northgate", "lat": 47.7087, "lng": -122.3240},
    {"id": "lake-city", "name": "Lake City", "lat": 47.7194, "lng": -122.2950},
    {"id": "wallingford", "name": "Wallingford", "lat": 47.6612, "lng": -122.3360},
    {"id": "pioneer-square", "name": "Pioneer Square", "lat": 47.6013, "lng": -122.3330},
    {"id": "belltown", "name": "Belltown", "lat": 47.6157, "lng": -122.3470},
    {"id": "roosevelt", "name": "Roosevelt", "lat": 47.6780, "lng": -122.3170},
]

_STATE_KEY = "dispatch_engine"
_LOG_KEY = "engine_logs"
_AUTONOMY_KEY = "dispatch_autonomy"
_NOTICE_KEY = "dispatch_notifications"
_AUTONOMY_LOCK = RLock()
_EARTH_MILES = 3958.8


def _state_locked(function):
    def wrapped(username, *args, **kwargs):
        with _AUTONOMY_LOCK:
            return function(username, *args, **kwargs)
    return wrapped


def _distance_miles(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlng = math.radians(b[1] - a[1])
    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_MILES * math.asin(math.sqrt(haversine))


@lru_cache(maxsize=100)
def _osrm_route(origin_lng, origin_lat, destination_lng, destination_lat):
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{origin_lng},{origin_lat};{destination_lng},{destination_lat}"
    )
    response = requests.get(
        url,
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        headers={"User-Agent": "AegisTwin/1.0"},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise ValueError("No drivable Seattle route was returned.")
    route = payload["routes"][0]
    points = [[lat, lng] for lng, lat in route["geometry"]["coordinates"]]
    return tuple(tuple(point) for point in points), route["distance"] / 1609.344


def _route(origin, destination):
    try:
        points, distance_miles = _osrm_route(
            origin["lng"], origin["lat"], destination["lng"], destination["lat"]
        )
    except requests.RequestException as error:
        raise ValueError("Street routing is unavailable. Try creating the dispatch again.") from error
    return [list(point) for point in points], max(0.5, distance_miles)


def _route_miles(route):
    return max(0.5, sum(_distance_miles(route[i - 1], route[i]) for i in range(1, len(route))) * 1.15)


def _target_speed(route_miles):
    speed = random.choices([50, 90, 120], weights=[60, 30, 10], k=1)[0]
    return 90 if speed == 120 and route_miles < 5 else speed


def _build_dispatch(origin, destination, truck_id, progress=0, demo=False):
    route, miles = _route(origin, destination)
    target_speed = _target_speed(miles) if not demo else random.choice([50, 90])
    eta_minutes = max(3, round(miles / target_speed * 60))
    now = time.time()
    start_time = now - eta_minutes * 60 * progress
    return {
        "id": uuid.uuid4().hex[:10],
        "truck_id": truck_id,
        "origin_id": origin["id"],
        "origin_name": origin["name"],
        "destination_id": destination["id"],
        "destination_name": destination["name"],
        "route": route,
        "route_version": 2,
        "distance_miles": round(miles, 1),
        "progress": progress,
        "target_speed_mph": target_speed,
        "speed_mph": min(10, target_speed),
        "eta_minutes": eta_minutes,
        "expected_duration_minutes": eta_minutes,
        "started_at": start_time,
        "last_tick": now,
        "incident_at": random.uniform(0.22, 0.78) if not demo and random.random() < 0.05 else None,
        "status": "en_route",
        "assistance_requested_at": None,
        "last_log_speed": target_speed,
    }


def _seed_state():
    return {
        "active": [
            _build_dispatch(WAREHOUSES[0], DESTINATIONS[4], "AEGIS-021", 0.28, demo=True),
            _build_dispatch(WAREHOUSES[1], DESTINATIONS[2], "AEGIS-034", 0.55, demo=True),
            _build_dispatch(WAREHOUSES[0], DESTINATIONS[0], "AEGIS-052", 0.39, demo=True),
        ],
        "completed": [],
        "cancelled": [],
    }


def _turn_points(dispatch):
    route = dispatch["route"]
    lengths = [_distance_miles(route[i - 1], route[i]) for i in range(1, len(route))]
    total = sum(lengths) or 1
    turns = []
    traveled = 0
    previous_bearing = None
    last_turn = -1
    for index, segment_length in enumerate(lengths):
        start, end = route[index], route[index + 1]
        lat1, lat2 = math.radians(start[0]), math.radians(end[0])
        delta_lng = math.radians(end[1] - start[1])
        bearing = math.degrees(math.atan2(
            math.sin(delta_lng) * math.cos(lat2),
            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lng),
        ))
        if previous_bearing is not None:
            change = abs((bearing - previous_bearing + 180) % 360 - 180)
            if change >= 35 and traveled - last_turn >= 0.035:
                turns.append((traveled / total, change))
                last_turn = traveled
        previous_bearing = bearing
        traveled += segment_length
    return turns


def _current_speed(dispatch, elapsed):
    if dispatch["status"] in {"needs_assistance", "assistance_requested"}:
        return 0
    nearby_turns = [
        angle for turn, angle in _turn_points(dispatch)
        if abs(dispatch["progress"] - turn) * dispatch["distance_miles"] < 0.06
    ]
    desired = 5 if any(angle >= 60 for angle in nearby_turns) else (
        10 if nearby_turns else dispatch["target_speed_mph"]
    )
    current = dispatch.get("speed_mph", min(10, dispatch["target_speed_mph"]))
    ramp = max(1, elapsed * (30 if desired < current else 4))
    return round(current + max(-ramp, min(ramp, desired - current)), 1)


def _append_logs(username, entries):
    if not entries:
        return
    logs = storage_manager.get_data(username, _LOG_KEY)
    if not isinstance(logs, list):
        logs = []
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    for event, message, dispatch, level in entries:
        logs.append({
            "id": uuid.uuid4().hex,
            "timestamp": stamp,
            "level": level,
            "event": event,
            "message": message,
            "dispatch_id": dispatch.get("id") if dispatch else None,
            "truck_id": dispatch.get("truck_id") if dispatch else None,
            "speed_mph": dispatch.get("speed_mph") if dispatch else None,
            "progress": round(dispatch.get("progress", 0) * 100, 2) if dispatch else None,
        })
    storage_manager.save_data(username, _LOG_KEY, logs[-5000:])


def _load_state(username):
    state = storage_manager.get_data(username, _STATE_KEY)
    if not isinstance(state, dict) or not isinstance(state.get("active"), list):
        state = _seed_state()
    state.setdefault("completed", [])
    state.setdefault("cancelled", [])
    for dispatch in state["active"]:
        if dispatch.get("route_version") == 2:
            continue
        origin = next((item for item in WAREHOUSES if item["id"] == dispatch.get("origin_id")), None)
        destination = next((item for item in DESTINATIONS if item["id"] == dispatch.get("destination_id")), None)
        if origin and destination:
            route, miles = _route(origin, destination)
            dispatch.update({
                "route": route,
                "route_version": 2,
                "distance_miles": round(miles, 1),
            })
    return state


def _advance(username, state):
    now = time.time()
    completed_now = []
    notices = []
    log_entries = []
    remaining = []
    for dispatch in state["active"]:
        old_status = dispatch["status"]
        if dispatch["status"] in {"needs_assistance", "assistance_requested"}:
            dispatch["last_tick"] = now
            remaining.append(dispatch)
            log_entries.append(("ROADSIDE_WAIT", "Truck is holding position for roadside support.", dispatch, "WARN"))
            continue

        elapsed = max(0, min(now - dispatch.get("last_tick", now), 60))
        dispatch["last_tick"] = now
        old_speed = dispatch.get("speed_mph", dispatch["target_speed_mph"])
        dispatch["speed_mph"] = _current_speed(dispatch, elapsed)
        miles_moved = ((old_speed + dispatch["speed_mph"]) / 2) * elapsed / 3600
        dispatch["progress"] = min(1, dispatch["progress"] + miles_moved / dispatch["distance_miles"])

        incident_at = dispatch.get("incident_at")
        if incident_at is not None and dispatch["progress"] >= incident_at:
            dispatch["status"] = "needs_assistance"
            dispatch["speed_mph"] = 0
            dispatch["incident_at"] = None
            remaining.append(dispatch)
            message = f"{dispatch['truck_id']} needs roadside assistance near {dispatch['destination_name']}."
            notices.append({"id": f"incident-{dispatch['id']}", "title": "INCIDENT DETECTED", "message": message, "error": True})
            log_entries.append(("INCIDENT_DETECTED", message, dispatch, "ERROR"))
            continue

        if dispatch["progress"] >= 1:
            duration = max(0, (now - dispatch["started_at"]) / 60)
            variance = duration - dispatch["expected_duration_minutes"]
            timing = "on time" if abs(variance) < 1 else (
                f"{round(abs(variance))} mins {'late' if variance > 0 else 'early'}"
            )
            completed_now.append({
                "id": dispatch["id"],
                "truck_id": dispatch["truck_id"],
                "trailer_id": dispatch.get("trailer_id"),
                "origin_name": dispatch["origin_name"],
                "destination_name": dispatch["destination_name"],
                "duration_minutes": round(duration, 1),
                "eta_minutes": dispatch["expected_duration_minutes"],
                "timing": timing,
                "arrived_at": now,
                "status": "completed",
            })
            _sync_trailer(username, dispatch, "completed", finished=True)
            delivery = completed_now[-1]
            message = f"{dispatch['truck_id']} completed delivery to {dispatch['destination_name']}."
            notices.append({"id": f"complete-{dispatch['id']}", "title": "DELIVERY COMPLETED", "message": message, "error": False})
            log_entries.append(("DELIVERY_COMPLETED", message, delivery | dispatch, "INFO"))
        else:
            dispatch["status"] = "slowed" if dispatch["speed_mph"] < dispatch["target_speed_mph"] else "en_route"
            remaining.append(dispatch)
            if dispatch["status"] == "slowed" and old_status != "slowed":
                message = f"{dispatch['truck_id']} slowed to {dispatch['speed_mph']} mph on a turn."
                notices.append({"id": f"slow-{dispatch['id']}-{int(now)}", "title": "DISPATCH SLOWED", "message": message, "error": False})
                log_entries.append(("TRUCK_SLOWED", message, dispatch, "WARN"))
            elif dispatch["status"] == "en_route" and old_status == "slowed":
                log_entries.append(("TRUCK_SPEED_RECOVERED", "Truck returned to cruise speed.", dispatch, "INFO"))
            log_entries.append(("ENGINE_TICK", f"Progress {dispatch['progress'] * 100:.2f}% at {dispatch['speed_mph']:.1f} mph.", dispatch, "INFO"))

    state["active"] = remaining
    state["completed"] = (completed_now + state["completed"])[:12]
    _append_logs(username, log_entries)
    return notices


def _autonomy_settings(username):
    settings = storage_manager.get_data(username, _AUTONOMY_KEY)
    if not isinstance(settings, dict):
        settings = {}
    try:
        max_trucks = int(settings.get("max_trucks", 6))
    except (TypeError, ValueError):
        max_trucks = 6
    try:
        last_dispatch_at = float(settings.get("last_dispatch_at", 0))
    except (TypeError, ValueError):
        last_dispatch_at = 0
    return {
        "enabled": settings.get("enabled") is True,
        "max_trucks": max(1, min(30, max_trucks)),
        "last_dispatch_at": last_dispatch_at,
    }


def get_autonomy(username):
    settings = _autonomy_settings(username)
    return {"enabled": settings["enabled"], "max_trucks": settings["max_trucks"]}


@_state_locked
def update_autonomy(username, updates):
    settings = _autonomy_settings(username)
    if "enabled" in updates:
        if not isinstance(updates["enabled"], bool):
            raise ValueError("Autonomous mode must be enabled or disabled.")
        if updates["enabled"] and not settings["enabled"]:
            settings["last_dispatch_at"] = time.time()
        settings["enabled"] = updates["enabled"]
    if "max_trucks" in updates:
        try:
            max_trucks = int(updates["max_trucks"])
        except (TypeError, ValueError) as error:
            raise ValueError("Maximum truck capacity must be a whole number.") from error
        if isinstance(updates["max_trucks"], bool) or not 1 <= max_trucks <= 30:
            raise ValueError("Maximum truck capacity must be between 1 and 30.")
        settings["max_trucks"] = max_trucks
    storage_manager.save_data(username, _AUTONOMY_KEY, settings)
    return {"enabled": settings["enabled"], "max_trucks": settings["max_trucks"]}


def _autonomous_tick(username):
    with _AUTONOMY_LOCK:
        return _autonomous_tick_locked(username)


def _autonomous_tick_locked(username):
    settings = _autonomy_settings(username)
    if not settings["enabled"]:
        return []

    notices = []
    now = time.time()
    state = _load_state(username)
    for dispatch in list(state["active"]):
        if dispatch["status"] == "needs_assistance":
            assisted = request_assistance(username, dispatch["id"])
            message = f"Autonomous roadside assistance dispatched for {assisted['truck_id']}."
            notices.append({
                "id": f"auto-roadside-{assisted['id']}",
                "title": "ROADSIDE ASSISTANCE",
                "message": message,
                "error": False,
            })
        elif dispatch["status"] == "assistance_requested":
            requested_at = float(dispatch.get("assistance_requested_at") or now)
            if now - requested_at >= 6:
                resumed = resume_dispatch(username, dispatch["id"])
                message = f"{resumed['truck_id']} is moving again after roadside service."
                notices.append({
                    "id": f"auto-resume-{resumed['id']}",
                    "title": "TRUCK RESUMED",
                    "message": message,
                    "error": False,
                })

    state = _load_state(username)
    if (
        now - settings["last_dispatch_at"] >= 3
        and len(state["active"]) < settings["max_trucks"]
    ):
        settings["last_dispatch_at"] = now
        storage_manager.save_data(username, _AUTONOMY_KEY, settings)
        origin = random.choice(WAREHOUSES)
        destination = random.choice(DESTINATIONS)
        try:
            dispatch = create_dispatch(username, origin["id"], destination["id"])
            message = f"{dispatch['truck_id']} assigned: {origin['name']} to {destination['name']}."
            notices.append({
                "id": f"auto-dispatch-{dispatch['id']}",
                "title": "AUTONOMOUS DISPATCH",
                "message": message,
                "error": False,
            })
        except ValueError as error:
            notices.append({
                "id": f"auto-dispatch-error-{int(now)}",
                "title": "AUTO-DISPATCH PAUSED",
                "message": str(error),
                "error": True,
            })
    return notices


def _record_notices(username, notices):
    if not notices:
        return
    saved = storage_manager.get_data(username, _NOTICE_KEY)
    saved = saved if isinstance(saved, list) else []
    known = {item.get("id") for item in saved if isinstance(item, dict)}
    for item in notices:
        if item.get("id") not in known:
            saved.append(item)
            known.add(item.get("id"))
    storage_manager.save_data(username, _NOTICE_KEY, saved[-200:])


def get_notices_since(username, after_id=None):
    saved = storage_manager.get_data(username, _NOTICE_KEY)
    saved = saved if isinstance(saved, list) else []
    cursor = saved[-1].get("id", "") if saved and isinstance(saved[-1], dict) else ""
    if not after_id:
        return [], cursor
    for index, item in enumerate(saved):
        if isinstance(item, dict) and item.get("id") == after_id:
            return saved[index + 1:], cursor
    if after_id == cursor:
        return [], cursor
    return saved[-20:], cursor


def autonomous_worker_tick(username):
    if _autonomy_settings(username)["enabled"]:
        get_state(username)


@_state_locked
def get_state(username):
    state = _load_state(username)
    for dispatch in state["active"]:
        _assign_trailer(username, dispatch)
    notices = _advance(username, state)
    for dispatch in state["active"]:
        _sync_trailer(username, dispatch, dispatch["status"])
    storage_manager.save_data(username, _STATE_KEY, state)

    auto_notices = _autonomous_tick(username)
    if auto_notices:
        state = _load_state(username)
        for dispatch in state["active"]:
            _assign_trailer(username, dispatch)
            _sync_trailer(username, dispatch, dispatch["status"])
        storage_manager.save_data(username, _STATE_KEY, state)
        notices.extend(auto_notices)
    _record_notices(username, notices)
    return state, notices


def create_dispatch(username, origin_id=None, destination_id=None):
    with _AUTONOMY_LOCK:
        return _create_dispatch_locked(username, origin_id, destination_id)


def _create_dispatch_locked(username, origin_id=None, destination_id=None):
    origin = next((item for item in WAREHOUSES if item["id"] == origin_id), None)
    destination = next((item for item in DESTINATIONS if item["id"] == destination_id), None)
    if origin is None or destination is None:
        raise ValueError("Choose a valid warehouse and Seattle destination.")
    state = _load_state(username)
    capacity = _autonomy_settings(username)["max_trucks"]
    if len(state["active"]) >= capacity:
        raise ValueError(f"Fleet capacity reached ({capacity} active trucks).")
    truck_number = random.randint(100, 999)
    used_trucks = {dispatch["truck_id"] for dispatch in state["active"]}
    while f"AEGIS-{truck_number}" in used_trucks:
        truck_number = random.randint(100, 999)
    dispatch = _build_dispatch(origin, destination, f"AEGIS-{truck_number}")
    _assign_trailer(username, dispatch)
    state["active"].append(dispatch)
    storage_manager.save_data(username, _STATE_KEY, state)
    incident_rate = "5% incident chance assigned." if dispatch["incident_at"] is not None else "No incident assigned."
    _append_logs(username, [
        ("DISPATCH_CREATED", f"{dispatch['truck_id']} assigned from {origin['name']} to {destination['name']}.", dispatch, "INFO"),
        ("INCIDENT_RISK_ROLLED", incident_rate, dispatch, "INFO"),
    ])
    return dispatch


@_state_locked
def request_assistance(username, dispatch_id):
    state = _load_state(username)
    dispatch = next((item for item in state["active"] if item["id"] == dispatch_id), None)
    if dispatch is None:
        raise KeyError("Dispatch not found.")
    if dispatch["status"] != "needs_assistance":
        raise ValueError("Roadside assistance is only available for a disabled truck.")
    dispatch["status"] = "assistance_requested"
    dispatch["assistance_requested_at"] = time.time()
    storage_manager.save_data(username, _STATE_KEY, state)
    _append_logs(username, [("ROADSIDE_REQUESTED", "Operator requested roadside assistance.", dispatch, "WARN")])
    return dispatch


@_state_locked
def resume_dispatch(username, dispatch_id):
    state = _load_state(username)
    dispatch = next((item for item in state["active"] if item["id"] == dispatch_id), None)
    if dispatch is None:
        raise KeyError("Dispatch not found.")
    if dispatch["status"] != "assistance_requested":
        raise ValueError("Request roadside assistance before resuming this truck.")
    dispatch["status"] = "en_route"
    dispatch["incident_at"] = None
    dispatch["last_tick"] = time.time()
    storage_manager.save_data(username, _STATE_KEY, state)
    _append_logs(username, [("DISPATCH_RESUMED", "Roadside issue cleared; truck returned to route.", dispatch, "INFO")])
    return dispatch


@_state_locked
def cancel_dispatch(username, dispatch_id):
    state = _load_state(username)
    dispatch = next((item for item in state["active"] if item["id"] == dispatch_id), None)
    if dispatch is None:
        raise KeyError("Active dispatch not found.")
    dispatch["status"] = "cancelled"
    dispatch["cancelled_at"] = time.time()
    state["active"].remove(dispatch)
    state["cancelled"] = ([dispatch] + state["cancelled"])[:50]
    _sync_trailer(username, dispatch, "cancelled", finished=True)
    storage_manager.save_data(username, _STATE_KEY, state)
    _append_logs(username, [("DISPATCH_CANCELLED", "Operator cancelled the dispatch.", dispatch, "WARN")])
    return dispatch


def get_logs(username, after=None, limit=150):
    logs = storage_manager.get_data(username, _LOG_KEY)
    if not isinstance(logs, list):
        logs = []
    if after:
        index = next((i for i, entry in enumerate(logs) if entry.get("id") == after), None)
        logs = logs[index + 1:] if index is not None else logs[-limit:]
    else:
        logs = logs[-limit:]
    return logs[-limit:]


def _trailers(username):
    trailers = storage_manager.get_data(username, "trailers")
    if isinstance(trailers, list):
        return trailers
    trailers = [
        {"id": "TRL-104", "type": "Dry Van", "hub": "sodo", "status": "available"},
        {"id": "TRL-116", "type": "Refrigerated", "hub": "sodo", "status": "assigned"},
        {"id": "TRL-203", "type": "Dry Van", "hub": "northgate", "status": "available"},
        {"id": "TRL-214", "type": "Flatbed", "hub": "northgate", "status": "maintenance"},
        {"id": "TRL-221", "type": "Refrigerated", "hub": "northgate", "status": "available"},
        {"id": "TRL-308", "type": "Dry Van", "hub": "sodo", "status": "available"},
    ]
    storage_manager.save_data(username, "trailers", trailers)
    return trailers


def _assign_trailer(username, dispatch):
    trailers = _trailers(username)
    assigned = next((item for item in trailers if item.get("dispatch_id") == dispatch["id"]), None)
    if assigned is None:
        assigned = next((item for item in trailers
                         if item.get("status") == "available" and not item.get("dispatch_id")), None)
    if assigned is None:
        used_ids = {item.get("id") for item in trailers}
        suffix = 1
        while f"TRL-AUTO-{suffix:03d}" in used_ids:
            suffix += 1
        assigned = {
            "id": f"TRL-AUTO-{suffix:03d}",
            "type": "Dry Van",
            "hub": dispatch.get("origin_id", "sodo"),
            "status": "available",
            "auto_generated": True,
        }
        trailers.append(assigned)
    desired = {
        "status": "assigned",
        "dispatch_id": dispatch["id"],
        "assigned_truck_id": dispatch["truck_id"],
        "dispatch_status": dispatch.get("status", "en_route"),
    }
    changed = any(assigned.get(key) != value for key, value in desired.items())
    assigned.update(desired)
    if changed:
        storage_manager.save_data(username, "trailers", trailers)
    dispatch["trailer_id"] = assigned["id"]


def _sync_trailer(username, dispatch, status, finished=False):
    trailer_id = dispatch.get("trailer_id")
    if not trailer_id:
        return
    trailers = _trailers(username)
    trailer = next((item for item in trailers if item.get("id") == trailer_id), None)
    if not trailer:
        return
    previous = dict(trailer)
    if finished:
        trailer["last_dispatch_id"] = dispatch["id"]
        trailer["last_dispatch_status"] = status
        trailer["last_truck_id"] = dispatch.get("truck_id")
        trailer["last_destination_name"] = dispatch.get("destination_name")
        trailer.pop("dispatch_id", None)
        trailer.pop("assigned_truck_id", None)
        trailer.pop("dispatch_status", None)
        if trailer.get("status") == "assigned":
            trailer["status"] = "available"
    else:
        trailer["dispatch_id"] = dispatch["id"]
        trailer["assigned_truck_id"] = dispatch.get("truck_id")
        trailer["dispatch_status"] = status
        trailer["status"] = "assigned"
    if trailer != previous:
        storage_manager.save_data(username, "trailers", trailers)


def list_trailers(username):
    state, _ = get_state(username)
    dispatches = {}
    for status, items in (
        ("en_route", state["active"]),
        ("completed", state["completed"]),
        ("cancelled", state["cancelled"]),
    ):
        for dispatch in items:
            dispatches[dispatch.get("id")] = {**dispatch, "status": dispatch.get("status", status)}
    result = []
    for trailer in _trailers(username):
        item = dict(trailer)
        dispatch = dispatches.get(item.get("dispatch_id") or item.get("last_dispatch_id"))
        if dispatch:
            item.update({
                "dispatch_status": dispatch.get("status", item.get("last_dispatch_status")),
                "truck_id": dispatch.get("truck_id", item.get("last_truck_id")),
                "destination_name": dispatch.get("destination_name", item.get("last_destination_name")),
                "speed_mph": dispatch.get("speed_mph", 0),
                "progress": dispatch.get("progress", 1 if dispatch.get("status") == "completed" else 0),
                "started_at": dispatch.get("started_at"),
                "expected_duration_minutes": dispatch.get("expected_duration_minutes", dispatch.get("eta_minutes")),
                "dispatch_active": dispatch in state["active"],
            })
        else:
            item.update({
                "dispatch_status": item.get("last_dispatch_status"),
                "truck_id": item.get("last_truck_id"),
                "destination_name": item.get("last_destination_name"),
                "progress": 1 if item.get("last_dispatch_status") == "completed" else 0,
                "dispatch_active": False,
            })
        result.append(item)
    return result


def add_trailer(username, trailer_id, trailer_type, hub):
    trailer_id = str(trailer_id or "").strip().upper()
    trailer_type = str(trailer_type or "").strip()
    if not trailer_id or not trailer_type or hub not in {item["id"] for item in WAREHOUSES}:
        raise ValueError("Enter a trailer ID and type, then choose a valid hub.")
    trailers = _trailers(username)
    if any(item["id"].casefold() == trailer_id.casefold() for item in trailers):
        raise ValueError("That trailer ID already exists.")
    trailer = {
        "id": trailer_id,
        "type": trailer_type,
        "hub": hub,
        "status": "available",
    }
    trailers.append(trailer)
    storage_manager.save_data(username, "trailers", trailers)
    return trailer


def update_trailer(username, trailer_id, updates):
    trailers = _trailers(username)
    trailer = next((item for item in trailers if item["id"] == trailer_id), None)
    if trailer is None:
        raise KeyError("Trailer not found.")
    if "status" in updates:
        if updates["status"] not in {"available", "assigned", "maintenance"}:
            raise ValueError("Choose available, assigned, or maintenance.")
        trailer["status"] = updates["status"]
    if "hub" in updates:
        if updates["hub"] not in {item["id"] for item in WAREHOUSES}:
            raise ValueError("Choose a valid hub.")
        trailer["hub"] = updates["hub"]
    trailer["last_checked"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    storage_manager.save_data(username, "trailers", trailers)
    return trailer


def delete_trailer(username, trailer_id):
    trailers = _trailers(username)
    remaining = [item for item in trailers if item["id"] != trailer_id]
    if len(remaining) == len(trailers):
        raise KeyError("Trailer not found.")
    storage_manager.save_data(username, "trailers", remaining)


def catalog():
    return {"warehouses": WAREHOUSES, "destinations": DESTINATIONS}
