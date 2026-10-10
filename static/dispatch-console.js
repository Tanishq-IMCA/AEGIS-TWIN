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
    const routeLayer = map ? L.layerGroup().addTo(map) : null;
    let selectedId = null;
    let activeFilter = 'ongoing';
    let catalog = { warehouses: [], destinations: [] };
    let snapshot = { active: [], completed: [], cancelled: [] };

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
    } else if (mapNode) {
        mapNode.innerHTML = '<div class="empty-state">Map tiles are unavailable. Check the network connection.</div>';
    }

    const statusColor = status => status === 'needs_assistance' || status === 'assistance_requested'
        ? '#d77c83' : status === 'slowed' ? '#d5bf74' : '#65c39a';
    const statusLabel = status => ({
        en_route: 'ONGOING',
        slowed: 'SLOWED',
        needs_assistance: 'NEEDS ASSISTANCE',
        assistance_requested: 'ROADSIDE REQUESTED',
        cancelled: 'CANCELLED'
    }[status] || status.toUpperCase());

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
                return `<article class="success-card">
                    <div class="success-line">SUCCESS | DISPATCHED FROM ${esc(d.origin_name)} TO ${esc(d.destination_name)} AND ARRIVED IN ${esc(d.duration_minutes)} MINS</div>
                    <hr><div>The delivery was ${esc(d.timing)}.</div>
                </article>`;
            }
            const actionButtons = [];
            if (d.status === 'needs_assistance') actionButtons.push(`<button class="dispatch-action help" data-action="assistance" data-id="${esc(d.id)}">SEND ROADSIDE</button>`);
            if (d.status === 'assistance_requested') actionButtons.push(`<button class="dispatch-action resume" data-action="resume" data-id="${esc(d.id)}">MARK REPAIRED & RESUME</button>`);
            if (snapshot.active.some(active => active.id === d.id)) actionButtons.push(`<button class="dispatch-action cancel" data-action="cancel" data-id="${esc(d.id)}">CANCEL</button>`);
            return `<article class="dispatch-card ${esc(d.status)} ${d.id === selectedId ? 'selected' : ''}" data-select="${esc(d.id)}">
                <div class="dispatch-row"><span class="dispatch-truck">${esc(d.truck_id)}</span><span class="dispatch-state">${statusLabel(d.status)}</span></div>
                <div class="dispatch-destination">${esc(d.origin_name || '')} → ${esc(d.destination_name || '')}</div>
                <div class="dispatch-details"><span>${esc(d.speed_mph ?? 0)} MPH · ${Math.round((d.progress || 0) * 100)}%</span><span>${d.status === 'cancelled' ? 'CANCELLED' : d.status === 'assistance_requested' ? 'HELP REQUESTED' : `ETA ${Math.max(0, Math.ceil((d.eta_minutes || 0) * (1 - (d.progress || 0))))} MIN`}</span></div>
                ${actionButtons.length ? `<div class="dispatch-actions">${actionButtons.join('')}</div>` : ''}
            </article>`;
        }).join('') : '<div class="empty-state">No dispatches in this view.</div>';
        document.querySelectorAll('[data-filter]').forEach(button =>
            button.classList.toggle('active', button.dataset.filter === activeFilter));
    }

    function drawRoute(dispatch) {
        if (!map || !routeLayer) return;
        routeLayer.clearLayers();
        if (!dispatch || !Array.isArray(dispatch.route) || dispatch.route.length < 2) return;
        const route = dispatch.route.map(point => L.latLng(point[0], point[1]));
        const segmentLengths = [];
        let total = 0;
        for (let i = 1; i < route.length; i++) {
            const length = route[i - 1].distanceTo(route[i]);
            segmentLengths.push(length);
            total += length;
        }
        let remainingMeters = total * Math.max(0, Math.min(1, dispatch.progress || 0));
        const travelled = [route[0]];
        const future = [];
        for (let i = 0; i < segmentLengths.length; i++) {
            const length = segmentLengths[i];
            if (remainingMeters >= length) {
                travelled.push(route[i + 1]);
                remainingMeters -= length;
            } else {
                const t = length ? remainingMeters / length : 0;
                const point = L.latLng(
                    route[i].lat + (route[i + 1].lat - route[i].lat) * t,
                    route[i].lng + (route[i + 1].lng - route[i].lng) * t
                );
                travelled.push(point);
                future.push(point, ...route.slice(i + 1));
                break;
            }
        }
        if (future.length > 1) L.polyline(future, { color: '#9ba5ad', weight: 2, opacity: .45, dashArray: '3 7' }).addTo(routeLayer);
        if (travelled.length > 1) L.polyline(travelled, { color: '#79a9ce', weight: 3, opacity: .86 }).addTo(routeLayer);
    }

    function positionOnRoute(points, progress) {
        if (!points || points.length < 2) return null;
        const route = points.map(point => L.latLng(point[0], point[1]));
        const segments = [];
        let total = 0;
        for (let i = 1; i < route.length; i++) {
            const length = route[i - 1].distanceTo(route[i]);
            segments.push(length);
            total += length;
        }
        let distance = total * Math.max(0, Math.min(1, progress || 0));
        for (let i = 0; i < segments.length; i++) {
            if (distance <= segments[i] || i === segments.length - 1) {
                const t = segments[i] ? distance / segments[i] : 0;
                return L.latLng(
                    route[i].lat + (route[i + 1].lat - route[i].lat) * t,
                    route[i].lng + (route[i + 1].lng - route[i].lng) * t
                );
            }
            distance -= segments[i];
        }
        return route[route.length - 1];
    }

    function renderMap() {
        if (!map) return;
        const liveIds = new Set(snapshot.active.map(d => d.id));
        for (const [id, marker] of markers) {
            if (!liveIds.has(id)) {
                map.removeLayer(marker.halo);
                map.removeLayer(marker.dot);
                markers.delete(id);
            }
        }
        snapshot.active.forEach(dispatch => {
            const point = positionOnRoute(dispatch.route || [], dispatch.progress);
            if (!point) return;
            const color = statusColor(dispatch.status);
            const tooltip = `<b>${esc(dispatch.truck_id)}</b><br>${esc(dispatch.destination_name)}<br>${esc(dispatch.speed_mph)} mph · ${statusLabel(dispatch.status)}`;
            let pair = markers.get(dispatch.id);
            if (!pair) {
                const halo = L.circleMarker(point, { radius: 16, color, fillColor: color, fillOpacity: .13, weight: 1, opacity: .35 }).addTo(map);
                const dot = L.circleMarker(point, { radius: 10, color: '#e7edf1', fillColor: color, fillOpacity: 1, weight: 2.5 }).addTo(map);
                dot.bindTooltip(tooltip, { sticky: true });
                dot.on('click', () => {
                    selectedId = dispatch.id;
                    renderList();
                    drawRoute(snapshot.active.find(item => item.id === dispatch.id));
                });
                pair = { halo, dot };
                markers.set(dispatch.id, pair);
            } else {
                pair.halo.setLatLng(point).setStyle({ color, fillColor: color });
                pair.dot.setLatLng(point).setStyle({ color: '#e7edf1', fillColor: color }).setTooltipContent(tooltip);
            }
        });
        if (!snapshot.active.some(d => d.id === selectedId)) selectedId = snapshot.active[0]?.id || null;
        drawRoute(snapshot.active.find(d => d.id === selectedId));
    }

    function updateState(state) {
        snapshot = {
            active: state.active || [],
            completed: state.completed || [],
            cancelled: state.cancelled || []
        };
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
        if (live) live.textContent = `${snapshot.active.length} ACTIVE`;
        const caption = document.getElementById('map-caption');
        if (caption && window.CARTO_BASEMAPS_KEY) caption.textContent = snapshot.active.length
            ? 'SEATTLE OPERATIONS · SELECT A TRUCK TO VIEW ITS ROAD ROUTE'
            : 'SEATTLE OPERATIONS · NO ACTIVE DISPATCHES';
        renderList();
        renderMap();

        const seen = new Set(JSON.parse(sessionStorage.getItem('dispatch_notices') || '[]'));
        (state.notices || []).forEach(item => {
            if (seen.has(item.id)) return;
            notice(item.title, item.message, item.error);
            seen.add(item.id);
        });
        sessionStorage.setItem('dispatch_notices', JSON.stringify([...seen].slice(-100)));
    }

    async function refresh() {
        try {
            const response = await fetch('/api/dispatch');
            if (!response.ok) throw new Error('Dispatch API unavailable');
            updateState(await response.json());
        } catch (error) {
            const live = document.getElementById('live-state');
            if (live) live.textContent = 'FLEET OFFLINE';
        }
    }

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
            selectedId = card.dataset.select;
            const selected = snapshot.active.find(item => item.id === selectedId);
            renderList();
            drawRoute(selected);
        }
    });

    if (map) setTimeout(() => map.invalidateSize(), 180);
    refresh();
    setInterval(refresh, 1000);
})();
