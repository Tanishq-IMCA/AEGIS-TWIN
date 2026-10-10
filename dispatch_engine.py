"""Small, persistent Seattle dispatch simulator for the control panel."""

import math
import random
import time
import uuid

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
_EARTH_MILES = 3958.8


def _distance_miles(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlng = math.radians(b[1] - a[1])
    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_MILES * math.asin(math.sqrt(haversine))


def _route(origin, destination):
    spine_lng = -122.329
    if destination["id"] == "west-seattle":
        return [
            [origin["lat"], origin["lng"]],
            [47.578, -122.337],
            [47.571, -122.350],
            [47.563, -122.370],
            [destination["lat"], destination["lng"]],
        ]
    return [
        [origin["lat"], origin["lng"]],
        [origin["lat"], spine_lng],
        [destination["lat"], spine_lng],
        [destination["lat"], destination["lng"]],
    ]


def _route_miles(route):
    return max(0.5, sum(_distance_miles(route[i - 1], route[i]) for i in range(1, len(route))) * 1.15)


def _target_speed(route_miles):
    speed = random.choices([50, 90, 120], weights=[60, 30, 10], k=1)[0]
    return 90 if speed == 120 and route_miles < 5 else speed


def _build_dispatch(origin, destination, truck_id, progress=0, demo=False):
    route = _route(origin, destination)
    miles = _route_miles(route)
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
        "distance_miles": round(miles, 1),
        "progress": progress,
        "target_speed_mph": target_speed,
        "speed_mph": target_speed,
        "eta_minutes": eta_minutes,
        "expected_duration_minutes": eta_minutes,
        "started_at": start_time,
        "last_tick": now,
        "incident_at": random.uniform(0.22, 0.78) if not demo and random.random() < 0.05 else None,
        "status": "en_route",
        "assistance_requested_at": None,
    }


def _seed_state():
    return {
        "active": [
            _build_dispatch(WAREHOUSES[0], DESTINATIONS[4], "AEGIS-021", 0.28, demo=True),
            _build_dispatch(WAREHOUSES[1], DESTINATIONS[2], "AEGIS-034", 0.55, demo=True),
            _build_dispatch(WAREHOUSES[0], DESTINATIONS[0], "AEGIS-052", 0.39, demo=True),
        ],
        "completed": [],
    }


def _turn_points(dispatch):
    route = dispatch["route"]
    lengths = [_distance_miles(route[i - 1], route[i]) for i in range(1, len(route))]
    total = sum(lengths) or 1
    turns = []
    traveled = 0
    for segment_length in lengths[:-1]:
        traveled += segment_length
        turns.append(traveled * 1.15 / dispatch["distance_miles"])
    return turns


def _current_speed(dispatch):
    if dispatch["status"] in {"needs_assistance", "assistance_requested"}:
        return 0
    near_turn = any(abs(dispatch["progress"] - turn) * dispatch["distance_miles"] < 0.18
                    for turn in _turn_points(dispatch))
    return round(dispatch["target_speed_mph"] * (0.62 if near_turn else 1), 1)


def _load_state(username):
    state = storage_manager.get_data(username, _STATE_KEY)
    if not isinstance(state, dict) or not isinstance(state.get("active"), list):
        state = _seed_state()
    state.setdefault("completed", [])
    return state


def _advance(state):
    now = time.time()
    completed_now = []
    new_incidents = []
    remaining = []
    for dispatch in state["active"]:
        if dispatch["status"] in {"needs_assistance", "assistance_requested"}:
            dispatch["last_tick"] = now
            remaining.append(dispatch)
            continue

        elapsed = max(0, min(now - dispatch.get("last_tick", now), 60))
        dispatch["last_tick"] = now
        dispatch["speed_mph"] = _current_speed(dispatch)
        miles_moved = dispatch["speed_mph"] * elapsed / 3600
        dispatch["progress"] = min(1, dispatch["progress"] + miles_moved / dispatch["distance_miles"])

        incident_at = dispatch.get("incident_at")
        if incident_at is not None and dispatch["progress"] >= incident_at:
            dispatch["status"] = "needs_assistance"
            dispatch["speed_mph"] = 0
            dispatch["incident_at"] = None
            new_incidents.append(dispatch["id"])
            remaining.append(dispatch)
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
                "origin_name": dispatch["origin_name"],
                "destination_name": dispatch["destination_name"],
                "duration_minutes": round(duration, 1),
                "eta_minutes": dispatch["expected_duration_minutes"],
                "timing": timing,
                "arrived_at": now,
            })
        else:
            dispatch["status"] = "slowed" if dispatch["speed_mph"] < dispatch["target_speed_mph"] else "en_route"
            remaining.append(dispatch)

    state["active"] = remaining
    state["completed"] = (completed_now + state["completed"])[:12]
    return new_incidents


def get_state(username):
    state = _load_state(username)
    new_incidents = _advance(state)
    storage_manager.save_data(username, _STATE_KEY, state)
    return state, new_incidents


def create_dispatch(username, origin_id=None, destination_id=None):
    origin = next((item for item in WAREHOUSES if item["id"] == origin_id), None)
    destination = next((item for item in DESTINATIONS if item["id"] == destination_id), None)
    if origin is None or destination is None:
        raise ValueError("Choose a valid warehouse and Seattle destination.")
    state = _load_state(username)
    truck_number = random.randint(100, 999)
    used_trucks = {dispatch["truck_id"] for dispatch in state["active"]}
    while f"AEGIS-{truck_number}" in used_trucks:
        truck_number = random.randint(100, 999)
    dispatch = _build_dispatch(origin, destination, f"AEGIS-{truck_number}")
    state["active"].append(dispatch)
    storage_manager.save_data(username, _STATE_KEY, state)
    return dispatch


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
    return dispatch


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
    return dispatch


def catalog():
    return {"warehouses": WAREHOUSES, "destinations": DESTINATIONS}
