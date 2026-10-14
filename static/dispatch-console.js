(() => {
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    const mapNode = document.getElementById('dispatch-map');
    const map = mapNode && window.L
        ? L.map(mapNode, {
            minZoom: 11, maxZoom: 18,
            maxBounds: [[47.48, -122.48], [47.76, -122.23]],
            maxBoundsViscosity: 0.92
        }).setView([47.6062, -122.3321], 11)
        : null;
    const markers = new Map();
    const routeColors = new Map();
    const routeGeometry = new Map();
    const routeLayers = new Map();
    const routeLayer = map ? L.layerGroup().addTo(map) : null;
    let selectedId = null;
    let followingId = null;
    let activeFilter = 'ongoing';
    let catalog = { warehouses: [], destinations: [] };
    let snapshot = { active: [], completed: [], cancelled: [] };
    const progressAnchors = new Map();
    let autonomy = { enabled: false, max_trucks: 6 };
    let noticeCursor = sessionStorage.getItem('dispatch_notice_cursor') || '';

    if (map) {
        const cartoKey = window.CARTO_BASEMAPS_KEY || '';
        const tileUrl = `https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png${cartoKey ? `?key=${encodeURIComponent(cartoKey)}` : ''}`;
        L.tileLayer(tileUrl, {
            subdomains: 'abcd',
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap &copy; CARTO'
        }).addTo(map);
        if (!cartoKey) {
            const caption = document.getElementById('map-caption');
            if (caption) caption.textContent = 'CARTO KEY REQUIRED · ADD CARTO_BASEMAPS_API_KEY IN REPLIT SECRETS';
        }
        map.on('click', () => {
            if (followingId) {
                markers.get(followingId)?.arrow.closePopup();
                followingId = null;
            }
            map.closePopup();
        });
    } else if (mapNode) {
        mapNode.innerHTML = '<div class="empty-state">Map tiles are unavailable. Check the network connection.</div>';
    }

    const statusLabel = status => ({
        en_route: 'ONGOING',
        slowed: 'SLOWED',
        needs_assistance: 'NEEDS ASSISTANCE',
        assistance_requested: 'ROADSIDE REQUESTED',
        cancelled: 'CANCELLED'
    }[status] || status.toUpperCase());

    function dispatchFinance(dispatch) {
        if (dispatch.financials) return dispatch.financials;
        const progress = dispatch.status === 'completed' ? 1 : Math.max(0, Math.min(1, Number(dispatch.progress) || 0));
        const miles = (Number(dispatch.distance_miles) || 0) * progress;
        const revenue = dispatch.status === 'cancelled' ? 0 : miles * 5.25;
        const fuelCost = miles / 6.5 * 4.25;
        const operatingCost = miles * 1.15;
        return { distance_miles: miles, revenue, fuel_cost: fuelCost, operating_cost: operatingCost, profit: revenue - fuelCost - operatingCost };
    }

    const usd = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value) || 0);
    const number = (value, digits = 1) => (Number(value) || 0).toFixed(digits);

    function routeColor(id) {
        if (routeColors.has(id)) return routeColors.get(id);
        const used = new Set(routeColors.values());
        let hue;
        do { hue = Math.floor(Math.random() * 360); }
        while (used.has(`hsl(${hue} 76% 62%)`));
        const color = `hsl(${hue} 76% 62%)`;
        routeColors.set(id, color);
        return color;
    }

    function arrowIcon(color, bearing) {
        return L.divIcon({
            className: 'truck-arrow-marker',
            html: `<svg class="truck-arrow-svg" viewBox="0 0 26 26" aria-hidden="true" style="transform:rotate(${bearing}deg)">
                <path d="M13 2L23 23L13 18L3 23Z" fill="${color}" stroke="#f4f7f8" stroke-width="1.25" stroke-linejoin="round"/>
            </svg>`,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });
    }

    function notice(title, message, error = false) {
        window.showNotice?.(esc(title), esc(message), 3500, false, error);
    }

    function installCatalog(data) {
        catalog = data;
        const origin = document.getElementById('origin-select');
        const destination = document.getElementById('destination-select');
        if (origin) origin.innerHTML = catalog.warehouses.map(item =>
            `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
        if (destination) destination.innerHTML = catalog.destinations.map(item =>
            `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
        if (map) catalog.warehouses.forEach(hub => {
            L.marker([hub.lat, hub.lng], {
                icon: L.divIcon({ className: '', html: '<span class="warehouse-icon"></span>', iconSize: [12, 12], iconAnchor: [6, 6] }),
                keyboard: false
            }).addTo(map).bindTooltip(esc(hub.name), { direction: 'top', offset: [0, -6] });
        });
    }

    function currentList() {
        if (activeFilter === 'finished') return snapshot.completed.map(d => ({ ...d, status: 'completed' }));
        if (activeFilter === 'cancelled') return snapshot.cancelled;
        if (activeFilter === 'attention') return snapshot.active.filter(d =>
            ['slowed', 'needs_assistance', 'assistance_requested'].includes(d.status));
        return snapshot.active.filter(d => d.status === 'en_route');
    }

    function renderList() {
        const list = document.getElementById('dispatch-list');
        if (!list) return;
        const rows = currentList();
        list.innerHTML = rows.length ? rows.map(d => {
            if (activeFilter === 'finished') {
                const finance = dispatchFinance(d);
                return `<article class="success-card">
                    <div class="success-line">SUCCESS | DISPATCHED FROM ${esc(d.origin_name)} TO ${esc(d.destination_name)} AND ARRIVED IN ${esc(d.duration_minutes)} MINS</div>
                    <hr><div>The delivery was ${esc(d.timing)}.</div>
                    <div class="dispatch-financials">${Number(finance.distance_miles || d.distance_miles || 0).toFixed(1)} MI · REVENUE ${usd(finance.revenue)} · DELIVERY COSTS ${usd((finance.fuel_cost || 0) + (finance.operating_cost || 0))} · NET ${usd(finance.profit)}</div>
                </article>`;
            }
            const finance = dispatchFinance(d);
            const actionButtons = [];
            if (d.status === 'needs_assistance') actionButtons.push(`<button class="dispatch-action help" data-action="assistance" data-id="${esc(d.id)}">SEND ROADSIDE</button>`);
            if (d.status === 'assistance_requested') actionButtons.push(`<button class="dispatch-action resume" data-action="resume" data-id="${esc(d.id)}">MARK REPAIRED & RESUME</button>`);
            if (snapshot.active.some(active => active.id === d.id)) actionButtons.push(`<button class="dispatch-action cancel" data-action="cancel" data-id="${esc(d.id)}">CANCEL</button>`);
            return `<article class="dispatch-card ${esc(d.status)} ${d.id === selectedId ? 'selected' : ''}" data-select="${esc(d.id)}">
                <div class="dispatch-row"><span class="dispatch-truck">${esc(d.truck_id)}</span><span class="dispatch-state">${statusLabel(d.status)}</span></div>
                <div class="dispatch-destination">${esc(d.origin_name || '')} → ${esc(d.destination_name || '')}</div>
                <div class="dispatch-details"><span>${esc(d.speed_mph ?? 0)} MPH · ${Math.round((d.progress || 0) * 100)}%</span><span>${number(finance.distance_miles, 1)} / ${number(d.distance_miles, 1)} MI · ${d.status === 'cancelled' ? 'CANCELLED' : d.status === 'assistance_requested' ? 'HELP REQUESTED' : `ETA ${Math.max(0, Math.ceil((d.eta_minutes || 0) * (1 - (d.progress || 0))))} MIN`}</span></div>
                <div class="dispatch-financials">EARNED ${usd(finance.revenue)} · COSTS ${usd((finance.fuel_cost || 0) + (finance.operating_cost || 0))} · NET ${usd(finance.profit)}</div>
                ${d.trailer_id ? `<div class="dispatch-trailer">TRAILER ${esc(d.trailer_id)}</div>` : ''}
                ${actionButtons.length ? `<div class="dispatch-actions">${actionButtons.join('')}</div>` : ''}
            </article>`;
        }).join('') : '<div class="empty-state">No dispatches in this view.</div>';
        document.querySelectorAll('[data-filter]').forEach(button =>
            button.classList.toggle('active', button.dataset.filter === activeFilter));
    }

    function getRouteGeometry(id, points) {
        if (routeGeometry.has(id)) return routeGeometry.get(id);
        if (!Array.isArray(points) || points.length < 2) return null;
        const route = points.map(point => L.latLng(point[0], point[1]));
        const lengths = [];
        let total = 0;
        for (let i = 1; i < route.length; i++) {
            const length = route[i - 1].distanceTo(route[i]);
            lengths.push(length);
            total += length;
        }
        const geometry = { route, lengths, total };
        routeGeometry.set(id, geometry);
        return geometry;
    }

    function drawRoute(dispatch) {
        if (!map || !routeLayer) return;
        const geometry = getRouteGeometry(dispatch.id, dispatch.route);
        if (!geometry) return;
        const color = routeColor(dispatch.id);
        const progress = Math.max(0, Math.min(1, dispatch.progress || 0));
        let remaining = geometry.total * progress;
        const travelled = [geometry.route[0]];
        const future = [];
        for (let i = 0; i < geometry.lengths.length; i++) {
            const length = geometry.lengths[i];
            if (remaining >= length) {
                travelled.push(geometry.route[i + 1]);
                remaining -= length;
            } else {
                const t = length ? remaining / length : 0;
                const point = L.latLng(
                    geometry.route[i].lat + (geometry.route[i + 1].lat - geometry.route[i].lat) * t,
                    geometry.route[i].lng + (geometry.route[i + 1].lng - geometry.route[i].lng) * t
                );
                travelled.push(point);
                future.push(point, ...geometry.route.slice(i + 1));
                break;
            }
        }
        const layers = routeLayers.get(dispatch.id) || {};
        const setLine = (key, points, style) => {
            if (points.length < 2) {
                if (layers[key]) routeLayer.removeLayer(layers[key]);
                layers[key] = null;
            } else if (layers[key]) {
                layers[key].setLatLngs(points).setStyle({ color });
            } else {
                layers[key] = L.polyline(points, { ...style, color }).addTo(routeLayer);
            }
        };
        setLine('travelled', travelled, { weight: 2.5, opacity: .9, dashArray: '1 6', lineCap: 'round' });
        setLine('future', future, { weight: 2, opacity: .56, dashArray: '1 7', lineCap: 'round' });
        routeLayers.set(dispatch.id, layers);
    }

    function positionOnRoute(id, points, progress) {
        const geometry = getRouteGeometry(id, points);
        if (!geometry) return null;
        let distance = geometry.total * Math.max(0, Math.min(1, progress || 0));
        for (let i = 0; i < geometry.lengths.length; i++) {
            if (distance <= geometry.lengths[i] || i === geometry.lengths.length - 1) {
                const t = geometry.lengths[i] ? distance / geometry.lengths[i] : 0;
                return L.latLng(
                    geometry.route[i].lat + (geometry.route[i + 1].lat - geometry.route[i].lat) * t,
                    geometry.route[i].lng + (geometry.route[i + 1].lng - geometry.route[i].lng) * t
                );
            }
            distance -= geometry.lengths[i];
        }
        return geometry.route[geometry.route.length - 1];
    }

    function bearingOnRoute(id, points, progress) {
        const geometry = getRouteGeometry(id, points);
        if (!geometry) return 0;
        let distance = geometry.total * Math.max(0, Math.min(1, progress || 0));
        let segment = geometry.lengths.length - 1;
        for (let i = 0; i < geometry.lengths.length; i++) {
            if (distance <= geometry.lengths[i]) { segment = i; break; }
            distance -= geometry.lengths[i];
        }
        const start = geometry.route[segment];
        const end = geometry.route[segment + 1];
        return Math.atan2(end.lng - start.lng, end.lat - start.lat) * 180 / Math.PI;
    }

    function liveSpeed(anchor, now) {
        if (['needs_assistance', 'assistance_requested'].includes(anchor.status)) return 0;
        const ramp = Math.min(1, Math.max(0, (now - anchor.at) / 1000));
        return anchor.speedFrom + (anchor.speedTo - anchor.speedFrom) * ramp;
    }

    function liveDispatch(dispatch, now) {
        const anchor = progressAnchors.get(dispatch.id);
        if (!anchor) return dispatch;
        const paused = ['needs_assistance', 'assistance_requested'].includes(anchor.status);
        const elapsed = Math.max(0, (now - anchor.at) / 1000);
        const ramp = Math.min(1, elapsed);
        const currentSpeed = liveSpeed(anchor, now);
        const milesMoved = paused ? 0 : (
            ((anchor.speedFrom + liveSpeed(anchor, anchor.at + ramp * 1000)) / 2) * ramp
            + anchor.speedTo * Math.max(0, elapsed - ramp)
        ) / 3600;
        const distance = Math.max(Number(anchor.distance) || 0, 0.1);
        const progress = paused
            ? anchor.progress
            : Math.min(1, anchor.progress + milesMoved / distance);
        return { ...dispatch, progress, speed_mph: Number(currentSpeed.toFixed(1)) };
    }

    function popupContent(dispatch) {
        const eta = Math.max(0, Math.ceil((dispatch.eta_minutes || 0) * (1 - (dispatch.progress || 0))));
        const finance = dispatchFinance(dispatch);
        return `<div class="truck-popup">
            <strong>${esc(dispatch.truck_id)}</strong>
            <span>${esc(dispatch.destination_name || 'Route')}</span>
            ${dispatch.trailer_id ? `<span>TRAILER ${esc(dispatch.trailer_id)}</span>` : ''}
            <span class="truck-popup-speed">${Number(dispatch.speed_mph ?? 0).toFixed(1)} MPH</span>
            <span>${statusLabel(dispatch.status)}</span>
            <span class="truck-popup-progress">${Math.round((dispatch.progress || 0) * 100)}% · ETA ${eta} MIN</span>
            <span>${number(finance.distance_miles, 1)} / ${number(dispatch.distance_miles, 1)} MI TRAVELLED</span>
            <span>REVENUE ${usd(finance.revenue)} · NET ${usd(finance.profit)}</span>
        </div>`;
    }

    function followDispatch(dispatch) {
        if (!dispatch || !map) return;
        selectedId = dispatch.id;
        followingId = dispatch.id;
        const pair = markers.get(dispatch.id);
        if (pair) {
            pair.arrow.setPopupContent(popupContent(dispatch)).openPopup();
            map.panTo(pair.arrow.getLatLng(), { animate: false });
        }
        renderList();
    }

    function renderMap() {
        if (!map) return;
        const liveIds = new Set(snapshot.active.map(d => d.id));
        for (const [id, marker] of markers) {
            if (!liveIds.has(id)) {
                map.removeLayer(marker.arrow);
                markers.delete(id);
                const layers = routeLayers.get(id);
                if (layers?.travelled) routeLayer.removeLayer(layers.travelled);
                if (layers?.future) routeLayer.removeLayer(layers.future);
                routeLayers.delete(id);
                routeGeometry.delete(id);
                routeColors.delete(id);
            }
        }
        snapshot.active.forEach(dispatch => {
            const current = liveDispatch(dispatch, performance.now());
            const point = positionOnRoute(dispatch.id, current.route || [], current.progress);
            if (!point) return;
            const color = routeColor(dispatch.id);
            const bearing = bearingOnRoute(dispatch.id, current.route || [], current.progress);
            let pair = markers.get(dispatch.id);
            if (!pair) {
                const arrow = L.marker(point, {
                    icon: arrowIcon(color, bearing),
                    keyboard: false,
                    bubblingMouseEvents: false,
                    riseOnHover: true
                }).addTo(map);
                arrow.bindPopup(popupContent(current), { closeButton: false, autoClose: false, closeOnClick: false, className: 'truck-map-popup' });
                arrow.on('click', event => {
                    if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
                    followDispatch(liveDispatch(snapshot.active.find(item => item.id === dispatch.id), performance.now()));
                });
                pair = { arrow, color };
                markers.set(dispatch.id, pair);
            } else {
                pair.arrow.setLatLng(point).setPopupContent(popupContent(current));
                pair.color = color;
            }
            drawRoute(current);
        });
        if (!snapshot.active.some(d => d.id === selectedId)) selectedId = snapshot.active[0]?.id || null;
        if (!snapshot.active.some(d => d.id === followingId)) followingId = null;
    }

    function updateState(state) {
        const receivedAt = performance.now();
        snapshot = {
            active: state.active || [],
            completed: state.completed || [],
            cancelled: state.cancelled || []
        };
        snapshot.active.forEach(dispatch => {
            const previous = progressAnchors.get(dispatch.id);
            progressAnchors.set(dispatch.id, {
                progress: Number(dispatch.progress) || 0,
                at: receivedAt,
                speedFrom: previous ? liveSpeed(previous, receivedAt) : Number(dispatch.speed_mph) || 0,
                speedTo: Number(dispatch.speed_mph) || 0,
                distance: Number(dispatch.distance_miles) || 0.1,
                status: dispatch.status
            });
        });
        const counts = {
            finished: snapshot.completed.length,
            ongoing: snapshot.active.filter(d => d.status === 'en_route').length,
            attention: snapshot.active.filter(d => ['slowed', 'needs_assistance', 'assistance_requested'].includes(d.status)).length,
            cancelled: snapshot.cancelled.length
        };
        Object.entries(counts).forEach(([key, value]) => {
            const node = document.querySelector(`[data-count="${key}"]`);
            if (node) node.textContent = value;
        });
        const live = document.getElementById('live-state');
        if (live) live.textContent = `${snapshot.active.length} / ${autonomy.max_trucks} ACTIVE${autonomy.enabled ? ' · AUTONOMOUS' : ''}`;
        const caption = document.getElementById('map-caption');
        if (caption && window.CARTO_BASEMAPS_KEY) caption.textContent = snapshot.active.length
            ? 'SEATTLE OPERATIONS · LIVE COLOR-CODED ROUTES'
            : 'SEATTLE OPERATIONS · NO ACTIVE DISPATCHES';
        const createButton = document.getElementById('create-dispatch');
        if (createButton) createButton.disabled = snapshot.active.length >= autonomy.max_trucks;
        renderList();
        renderMap();

        const seen = new Set(JSON.parse(sessionStorage.getItem('dispatch_notices') || '[]'));
        (state.notices || []).forEach(item => {
            if (seen.has(item.id)) return;
            notice(item.title, item.message, item.error);
            seen.add(item.id);
        });
        sessionStorage.setItem('dispatch_notices', JSON.stringify([...seen].slice(-100)));
        if (state.notice_cursor) {
            noticeCursor = state.notice_cursor;
            sessionStorage.setItem('dispatch_notice_cursor', noticeCursor);
        }
    }

    async function refresh() {
        try {
            const response = await fetch(`/api/dispatch?notice_after=${encodeURIComponent(noticeCursor)}`);
            if (!response.ok) throw new Error('Dispatch API unavailable');
            updateState(await response.json());
        } catch (error) {
            const live = document.getElementById('live-state');
            if (live) live.textContent = 'FLEET OFFLINE';
        }
    }

    function applyAutonomy(settings) {
        autonomy = {
            enabled: Boolean(settings.enabled),
            max_trucks: Math.max(1, Math.min(30, Number(settings.max_trucks) || 6))
        };
        const button = document.getElementById('autonomy-toggle');
        const capacity = document.getElementById('max-active-trucks');
        if (button) {
            button.classList.toggle('is-on', autonomy.enabled);
            button.textContent = autonomy.enabled ? 'AUTO ON' : 'AUTO OFF';
            button.setAttribute('aria-pressed', String(autonomy.enabled));
        }
        if (capacity && document.activeElement !== capacity) capacity.value = autonomy.max_trucks;
    }

    async function saveAutonomy(updates) {
        const response = await fetch('/api/dispatch/autonomy', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Fleet settings could not be saved.');
        applyAutonomy(data.autonomy);
        return data.autonomy;
    }

    fetch('/api/dispatch/autonomy')
        .then(response => {
            if (!response.ok) throw new Error('Fleet settings unavailable.');
            return response.json();
        })
        .then(data => applyAutonomy(data.autonomy))
        .catch(() => notice('AUTO MODE UNAVAILABLE', 'Fleet settings could not be loaded.', true));

    document.getElementById('autonomy-toggle')?.addEventListener('click', async event => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
            const settings = await saveAutonomy({ enabled: !autonomy.enabled });
            notice(settings.enabled ? 'AUTONOMOUS MODE ON' : 'AUTONOMOUS MODE OFF',
                settings.enabled ? `Dispatching every 3 seconds, up to ${settings.max_trucks} active trucks.` : 'Automatic dispatching has stopped.');
            await refresh();
        } catch (error) {
            notice('AUTO MODE UPDATE FAILED', error.message, true);
        } finally {
            button.disabled = false;
        }
    });

    document.getElementById('max-active-trucks')?.addEventListener('change', async event => {
        const input = event.currentTarget;
        try {
            const settings = await saveAutonomy({ max_trucks: Number(input.value) });
            notice('FLEET CAPACITY UPDATED', `Maximum active trucks: ${settings.max_trucks}.`);
            await refresh();
        } catch (error) {
            input.value = autonomy.max_trucks;
            notice('CAPACITY UPDATE FAILED', error.message, true);
        }
    });

    fetch('/api/dispatch?catalog=1')
        .then(response => {
            if (!response.ok) throw new Error('Catalog unavailable');
            return response.json();
        })
        .then(data => installCatalog(data.catalog))
        .catch(() => notice('MAP UNAVAILABLE', 'Seattle route data could not be loaded.', true));

    document.getElementById('dispatch-form')?.addEventListener('submit', async event => {
        event.preventDefault();
        const submit = event.currentTarget.querySelector('button[type="submit"]');
        if (submit) submit.disabled = true;
        try {
            const response = await fetch('/api/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    origin_id: document.getElementById('origin-select').value,
                    destination_id: document.getElementById('destination-select').value
                })
            });
            const data = await response.json();
            if (!response.ok) return notice('DISPATCH FAILED', data.error || 'Route could not be created.', true);
            activeFilter = 'ongoing';
            selectedId = data.dispatch.id;
            notice('DISPATCH CREATED', `${data.dispatch.truck_id} is en route to ${data.dispatch.destination_name}.`);
            await refresh();
        } catch (error) {
            notice('DISPATCH FAILED', 'The dispatch could not be created.', true);
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
        activeFilter = button.dataset.filter;
        renderList();
    }));

    document.getElementById('dispatch-list')?.addEventListener('click', async event => {
        const action = event.target.closest('button[data-action]');
        if (action) {
            event.stopPropagation();
            if (action.dataset.action === 'cancel'
                && !window.confirm('Cancel this dispatch? It will remain in the cancelled history.')) return;
            try {
                const response = await fetch(`/api/dispatch/${encodeURIComponent(action.dataset.id)}/${action.dataset.action}`, { method: 'POST' });
                const data = await response.json();
                if (!response.ok) return notice('ACTION FAILED', data.error || 'Control action failed.', true);
                const titles = { assistance: 'ROADSIDE REQUESTED', resume: 'DISPATCH RESUMED', cancel: 'DISPATCH CANCELLED' };
                notice(titles[action.dataset.action], `${data.dispatch.truck_id} · ${data.dispatch.destination_name}`);
                await refresh();
            } catch (error) {
                notice('ACTION FAILED', 'The control action could not be completed.', true);
            }
            return;
        }
        const card = event.target.closest('[data-select]');
        if (card) {
            const selected = snapshot.active.find(item => item.id === card.dataset.select);
            if (selected) followDispatch(liveDispatch(selected, performance.now()));
        }
    });

    if (map) setTimeout(() => map.invalidateSize(), 180);
    function animateFrame(now) {
        if (map) {
            snapshot.active.forEach(dispatch => {
                const current = liveDispatch(dispatch, now);
                const point = positionOnRoute(dispatch.id, current.route || [], current.progress);
                const pair = markers.get(dispatch.id);
                if (!point || !pair) return;
                pair.arrow.setLatLng(point);
                const svg = pair.arrow.getElement()?.querySelector('.truck-arrow-svg');
                if (svg) svg.style.transform = `rotate(${bearingOnRoute(dispatch.id, current.route || [], current.progress)}deg)`;
                if (pair.arrow.isPopupOpen()) {
                    const popup = pair.arrow.getPopup();
                    popup.setLatLng(point);
                    const content = popup.getElement();
                    const speed = content?.querySelector('.truck-popup-speed');
                    const progress = content?.querySelector('.truck-popup-progress');
                    if (speed) speed.textContent = `${Number(current.speed_mph || 0).toFixed(1)} MPH`;
                    if (progress) {
                        const eta = Math.max(0, Math.ceil((current.eta_minutes || 0) * (1 - (current.progress || 0))));
                        progress.textContent = `${Math.round((current.progress || 0) * 100)}% · ETA ${eta} MIN`;
                    }
                }
            });
            if (followingId) {
                const dispatch = snapshot.active.find(item => item.id === followingId);
                if (dispatch) {
                    const current = liveDispatch(dispatch, now);
                    const point = positionOnRoute(dispatch.id, current.route || [], current.progress);
                    if (point) {
                        const screenPoint = map.latLngToContainerPoint(point);
                        const screenCenter = map.latLngToContainerPoint(map.getCenter());
                        if (screenPoint.distanceTo(screenCenter) > 0.75) {
                            map.panTo(point, { animate: false, noMoveStart: true });
                        }
                    }
                }
            }
        }
        requestAnimationFrame(animateFrame);
    }
    requestAnimationFrame(animateFrame);
    refresh();
    setInterval(refresh, 1000);
})();
