(() => {
    const statusLists = {
        'in-progress': document.getElementById('list-in-progress'),
        suspended: document.getElementById('list-suspended'),
        done: document.getElementById('list-done'),
        overdue: document.getElementById('list-overdue')
    };
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    let lastState = null;

    function statusFor(dispatch, now) {
        if (dispatch.status === 'completed') return 'done';
        if (dispatch.status === 'cancelled' || ['needs_assistance', 'assistance_requested'].includes(dispatch.status)) return 'suspended';
        const due = Number(dispatch.started_at || 0) + Number(dispatch.expected_duration_minutes || 0) * 60;
        if (dispatch.status === 'slowed' || (due && now > due && dispatch.progress < 1)) return 'overdue';
        return 'in-progress';
    }

    function render() {
        if (!lastState) return;
        Object.values(statusLists).forEach(list => {
            if (list) list.querySelectorAll('.dispatch-manifest-card').forEach(card => card.remove());
        });

        const now = Date.now() / 1000;
        const rows = [
            ...(lastState.active || []),
            ...(lastState.completed || []),
            ...(lastState.cancelled || [])
        ];
        rows.forEach(dispatch => {
            const status = statusFor(dispatch, now);
            const list = statusLists[status];
            if (!list) return;
            const percent = status === 'done' ? 100 : Math.round(Math.max(0, Math.min(1, Number(dispatch.progress) || 0)) * 100);
            const label = status === 'done' ? 'DELIVERED'
                : status === 'suspended' ? (dispatch.status === 'cancelled' ? 'CANCELLED' : 'SUSPENDED')
                : status === 'overdue' ? 'DELAYED' : 'IN TRANSIT';
            const active = (lastState.active || []).some(item => item.id === dispatch.id);
            const card = document.createElement('article');
            card.className = `task-card dispatch-manifest-card dispatch-${status}`;
            card.draggable = false;
            card.innerHTML = `<div class="dispatch-manifest-head">
                <strong>${esc(dispatch.truck_id || 'TRUCK')}</strong>
                <span class="dispatch-manifest-state">${label}</span>
            </div>
            <div class="dispatch-manifest-route">${esc(dispatch.origin_name || '')} → ${esc(dispatch.destination_name || '')}</div>
            <div class="dispatch-manifest-meta">${percent}% complete${dispatch.trailer_id ? ` · ${esc(dispatch.trailer_id)}` : ''}</div>
            <div class="dispatch-manifest-progress"><span style="width:${percent}%"></span></div>
            <div class="dispatch-manifest-actions">
                <a href="/control-panel">TRACK TRUCK</a>
                ${active ? `<button type="button" data-cancel="${esc(dispatch.id)}">CANCEL</button>` : ''}
            </div>`;
            list.prepend(card);
        });

        Object.entries(statusLists).forEach(([status, list]) => {
            const count = list?.querySelectorAll('.task-card').length || 0;
            const node = document.getElementById(`count-${status}`);
            if (node) node.textContent = count;
        });
        const suspendedCount = statusLists.suspended?.querySelectorAll('.task-card').length || 0;
        const suspendedNode = document.getElementById('count-suspended');
        if (suspendedNode) suspendedNode.textContent = suspendedCount;
    }

    async function refresh() {
        try {
            const response = await fetch('/api/dispatch', { headers: { Accept: 'application/json' } });
            if (!response.ok) return;
            lastState = await response.json();
            render();
        } catch (error) {
            console.warn('Manifest dispatch sync unavailable.', error);
        }
    }

    document.addEventListener('click', async event => {
        const button = event.target.closest('[data-cancel]');
        if (!button) return;
        if (!window.confirm('Cancel this truck dispatch?')) return;
        button.disabled = true;
        try {
            const response = await fetch(`/api/dispatch/${encodeURIComponent(button.dataset.cancel)}/cancel`, { method: 'POST' });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Dispatch could not be cancelled.');
            await refresh();
        } catch (error) {
            window.showNotice?.('CANCEL FAILED', esc(error.message), 3200, false, true);
            button.disabled = false;
        }
    });
    window.addEventListener('manifest:render', render);
    refresh();
    setInterval(refresh, 1500);
})();
