(() => {
    const grid = document.getElementById('calendar-grid');
    const agenda = document.getElementById('calendar-event-list');
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let visibleMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    let selectedDate = new Date(today);
    let events = [];

    function keyFor(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }
    function parseDate(value) {
        if (!value) return null;
        const date = typeof value === 'number' ? new Date(value * 1000) : new Date(`${value}`.length === 10 ? `${value}T12:00:00` : value);
        return Number.isNaN(date.getTime()) ? null : date;
    }
    function addEvent(date, event) {
        const parsed = parseDate(date);
        if (!parsed) return;
        const day = keyFor(parsed);
        events.push({ ...event, date: day, sortTime: parsed.getTime() });
    }
    function shortTime(event) {
        if (!event.sortTime) return 'ALL DAY';
        return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(event.sortTime));
    }
    function eventClass(event) {
        return event.kind === 'task' ? 'task'
            : event.kind === 'attention' ? 'attention'
            : event.kind === 'cancelled' ? 'cancelled'
            : event.kind === 'delivery' ? '' : 'order';
    }

    async function load() {
        const [calendarResponse, tasksResponse, dispatchResponse] = await Promise.all([
            fetch('/api/storage/calendar_events'),
            fetch('/api/storage/tasks'),
            fetch('/api/dispatch')
        ]);
        if (![calendarResponse, tasksResponse, dispatchResponse].every(response => response.ok)) {
            throw new Error('Scheduled orders could not be loaded.');
        }
        const [calendarData, tasks, dispatchState] = await Promise.all([
            calendarResponse.json(), tasksResponse.json(), dispatchResponse.json()
        ]);
        events = [];
        (Array.isArray(calendarData) ? calendarData : []).forEach(item => {
            addEvent(item.date || item.start || item.due, {
                kind: 'order',
                title: item.title || 'Scheduled event',
                subtitle: item.sender ? `Shared by ${item.sender}` : 'Calendar event'
            });
        });
        (Array.isArray(tasks) ? tasks : []).forEach(item => {
            if (item.start) addEvent(item.start, { kind:'task', title:item.title || 'Task', subtitle:'Task starts' });
            if (item.end) addEvent(item.end, { kind:'task', title:item.title || 'Task', subtitle:'Task deadline' });
        });
        (dispatchState.active || []).forEach(item => {
            const dueAt = Number(item.started_at || 0) + Number(item.expected_duration_minutes || 0) * 60;
            const delayed = item.status === 'slowed' || (dueAt && Date.now()/1000 > dueAt && item.progress < 1);
            addEvent(dueAt || item.started_at, {
                kind: ['needs_assistance','assistance_requested'].includes(item.status) ? 'attention' : delayed ? 'attention' : 'order',
                title: `${item.truck_id || 'Truck'} · ${item.destination_name || 'Delivery'}`,
                subtitle: `${delayed ? 'Delayed delivery' : 'Delivery ETA'} · ${item.speed_mph || 0} mph`
            });
        });
        (dispatchState.completed || []).forEach(item => addEvent(item.arrived_at, {
            kind:'delivery', title:`${item.truck_id || 'Truck'} · ${item.destination_name || 'Delivery'}`, subtitle:'Delivery completed'
        }));
        (dispatchState.cancelled || []).forEach(item => addEvent(item.cancelled_at, {
            kind:'cancelled', title:`${item.truck_id || 'Truck'} · ${item.destination_name || 'Delivery'}`, subtitle:'Dispatch cancelled'
        }));
        render();
    }

    function renderAgenda() {
        const selectedKey = keyFor(selectedDate);
        const label = new Intl.DateTimeFormat(undefined, { weekday:'long', month:'long', day:'numeric', year:'numeric' }).format(selectedDate);
        document.getElementById('calendar-selected-date').textContent = label;
        const daily = events.filter(event => event.date === selectedKey).sort((a,b) => a.sortTime - b.sortTime);
        agenda.innerHTML = daily.length ? daily.map(event => `<article class="calendar-event ${eventClass(event)}">
            <time class="calendar-event-time">${esc(shortTime(event))}</time>
            <div><div class="calendar-event-title">${esc(event.title)}</div><div class="calendar-event-subtitle">${esc(event.subtitle || '')}</div></div>
        </article>`).join('') : '<div class="calendar-empty">No orders, deliveries, or appointments scheduled for this date.</div>';
    }

    function render() {
        document.getElementById('calendar-month-label').textContent =
            new Intl.DateTimeFormat(undefined, { month:'long', year:'numeric' }).format(visibleMonth);
        const byDate = new Map();
        events.forEach(event => {
            if (!byDate.has(event.date)) byDate.set(event.date, []);
            byDate.get(event.date).push(event);
        });
        const firstDay = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
        const gridStart = new Date(firstDay);
        gridStart.setDate(firstDay.getDate() - ((firstDay.getDay() + 6) % 7));
        grid.innerHTML = Array.from({ length:42 }, (_, index) => {
            const date = new Date(gridStart);
            date.setDate(gridStart.getDate() + index);
            const dateKey = keyFor(date);
            const dayEvents = byDate.get(dateKey) || [];
            const chips = dayEvents.slice(0, 2).map(event =>
                `<span class="calendar-event-chip ${eventClass(event)}">${esc(event.title)}</span>`).join('');
            const more = dayEvents.length > 2 ? `<span class="calendar-more">+${dayEvents.length - 2} more</span>` : '';
            const outside = date.getMonth() !== visibleMonth.getMonth();
            return `<button type="button" class="calendar-day${outside ? ' outside-month' : ''}${dateKey === keyFor(today) ? ' today' : ''}${dateKey === keyFor(selectedDate) ? ' selected' : ''}" data-date="${dateKey}" aria-label="${esc(date.toLocaleDateString())}, ${dayEvents.length} events">
                <span class="calendar-day-number">${date.getDate()}</span>
                <span class="calendar-day-events">${chips}${more}</span>
            </button>`;
        }).join('');
        renderAgenda();
    }

    grid.addEventListener('click', event => {
        const day = event.target.closest('[data-date]');
        if (!day) return;
        const [year, month, date] = day.dataset.date.split('-').map(Number);
        selectedDate = new Date(year, month - 1, date);
        visibleMonth = new Date(year, month - 1, 1);
        render();
    });
    document.getElementById('calendar-prev').addEventListener('click', () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1);
        selectedDate = new Date(visibleMonth);
        render();
    });
    document.getElementById('calendar-next').addEventListener('click', () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1);
        selectedDate = new Date(visibleMonth);
        render();
    });
    document.getElementById('calendar-today').addEventListener('click', () => {
        selectedDate = new Date(today);
        visibleMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        render();
    });
    load().catch(error => {
        agenda.innerHTML = `<div class="calendar-empty">${esc(error.message)}</div>`;
        render();
    });
    setInterval(() => load().catch(() => {}), 15000);
})();
