(() => {
    const colors = {
        revenue: '#63d6b0',
        profit: '#82e6a3',
        fuel: '#7c91ff',
        operating: '#f1ad60',
        miles: '#63d6b0',
        deliveries: '#7c91ff'
    };
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));
    const money = value => new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD', maximumFractionDigits: 0
    }).format(Number(value) || 0);
    const preciseMoney = value => new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD', maximumFractionDigits: 2
    }).format(Number(value) || 0);
    const number = (value, digits = 1) => new Intl.NumberFormat('en-US', {
        maximumFractionDigits: digits
    }).format(Number(value) || 0);
    const svgNS = 'http://www.w3.org/2000/svg';
    const svgEl = (tag, attrs = {}) => {
        const node = document.createElementNS(svgNS, tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        return node;
    };
    let lastMetrics = {};

    function metric(id, value, rawValue) {
        const node = document.getElementById(id);
        if (!node) return;
        node.textContent = value;
        if (lastMetrics[id] !== rawValue) {
            node.classList.remove('updated');
            void node.offsetWidth;
            node.classList.add('updated');
        }
        lastMetrics[id] = rawValue;
    }

    function estimatedFinance(dispatch, assumptions) {
        const totalDistance = Number(dispatch.route_distance_miles || dispatch.distance_miles) || 0;
        const progress = dispatch.status === 'completed'
            ? 1
            : Math.max(0, Math.min(1, Number(dispatch.progress) || 0));
        const miles = totalDistance * progress;
        const revenue = miles * assumptions.revenue_per_mile;
        const fuelCost = miles / assumptions.miles_per_gallon * assumptions.fuel_price_per_gallon;
        const operatingCost = miles * assumptions.fleet_cost_per_mile;
        return {
            miles,
            revenue,
            fuelCost,
            operatingCost,
            profit: revenue - fuelCost - operatingCost
        };
    }

    function renderMetrics(data) {
        const totals = data.totals;
        metric('metric-revenue', money(totals.revenue), totals.revenue);
        metric('metric-profit', money(totals.profit), totals.profit);
        metric('metric-fuel', `${number(totals.fuel_gallons, 1)} gal`, totals.fuel_gallons);
        metric('metric-fuel-cost', `${money(totals.fuel_cost)} estimated fuel cost`, totals.fuel_cost);
        metric('metric-distance', `${number(totals.distance_miles)} mi`, totals.distance_miles);
        metric('metric-deliveries', `${totals.completed_deliveries} completed · ${totals.active_deliveries} active`,
            `${totals.completed_deliveries}:${totals.active_deliveries}`);
        const saved = Number(totals.time_saved_minutes) || 0;
        metric('metric-time', saved >= 60 ? `${number(saved / 60)} hr` : `${number(saved, 0)} min`, saved);
        metric('metric-operating', money(totals.operating_cost), totals.operating_cost);
        const assumptions = data.assumptions;
        document.getElementById('analytics-assumptions').textContent =
            `Financials are estimates, not accounting records. Model assumptions: ${preciseMoney(assumptions.revenue_per_mile)}/mile revenue, ${number(assumptions.miles_per_gallon, 1)} MPG, ${preciseMoney(assumptions.fuel_price_per_gallon)}/gallon fuel, and ${preciseMoney(assumptions.fleet_cost_per_mile)}/mile fleet operating costs.`;
    }

    function renderLegend(elementId, series) {
        document.getElementById(elementId).innerHTML = series.map(item =>
            `<span class="legend-item"><i class="legend-dot" style="background:${item.color}"></i>${escapeHtml(item.label)}</span>`
        ).join('');
    }

    function renderLineChart(daily) {
        const svg = document.getElementById('line-chart');
        const rows = daily.slice(-30);
        const series = [
            { key: 'revenue', label: 'Revenue', color: colors.revenue },
            { key: 'profit', label: 'Net profit', color: colors.profit },
            { key: 'fuel_cost', label: 'Fuel cost', color: colors.fuel, dotted: true },
            { key: 'operating_cost', label: 'Delivery operating cost', color: colors.operating, dotted: true }
        ];
        const width = 720, height = 260, left = 48, right = 12, top = 16, bottom = 32;
        const plotWidth = width - left - right, plotHeight = height - top - bottom;
        const max = Math.max(1, ...rows.flatMap(row => series.map(item => Number(row[item.key]) || 0))) * 1.12;
        svg.replaceChildren();
        for (let index = 0; index <= 4; index++) {
            const y = top + plotHeight * index / 4;
            svg.appendChild(svgEl('line', { x1: left, x2: width - right, y1: y, y2: y, class: 'chart-gridline' }));
            const label = svgEl('text', { x: left - 8, y: y + 4, 'text-anchor': 'end' });
            label.textContent = money(max * (4 - index) / 4);
            svg.appendChild(label);
        }
        const count = Math.max(2, rows.length);
        series.forEach(item => {
            const points = rows.map((row, index) => {
                const x = left + plotWidth * (rows.length < 2 ? .5 : index / (rows.length - 1));
                const y = top + plotHeight * (1 - Math.max(0, Number(row[item.key]) || 0) / max);
                return `${x},${y}`;
            });
            svg.appendChild(svgEl('path', {
                d: points.length > 1 ? `M ${points.join(' L ')}` : `M ${left},${top + plotHeight} L ${width - right},${top + plotHeight}`,
                stroke: item.color,
                class: `chart-series${item.dotted ? ' dotted' : ''}`
            }));
        });
        [0, .25, .5, .75, 1].forEach(fraction => {
            const index = Math.min(rows.length - 1, Math.round((rows.length - 1) * fraction));
            if (rows[index]) {
                const label = svgEl('text', { x: left + plotWidth * fraction, y: height - 7, 'text-anchor': 'middle' });
                label.textContent = new Date(`${rows[index].date}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
                svg.appendChild(label);
            }
        });
        renderLegend('line-legend', series);
    }

    function renderPie(data) {
        const totals = data.totals;
        const values = [
            { label: 'Fuel expense', value: Number(totals.fuel_cost) || 0, color: colors.fuel },
            { label: 'Delivery operating costs', value: Number(totals.operating_cost) || 0, color: colors.operating }
        ];
        const sum = values.reduce((total, item) => total + item.value, 0);
        let angle = 0;
        const segments = values.map(item => {
            const portion = sum ? item.value / sum * 360 : 0;
            const start = angle;
            angle += portion;
            return `${item.color} ${start}deg ${angle}deg`;
        });
        document.getElementById('cost-pie').style.background = sum
            ? `conic-gradient(${segments.join(',')})`
            : 'conic-gradient(rgba(255,255,255,.12) 0deg 360deg)';
        document.getElementById('pie-total').textContent = money(totals.total_cost);
        document.querySelector('.pie-center span').textContent = 'TOTAL COST';
        document.getElementById('pie-legend').innerHTML = values.map(item => {
            const share = sum ? Math.round(item.value / sum * 100) : 0;
            return `<div class="pie-row"><span class="pie-row-label"><i class="legend-dot" style="background:${item.color}"></i>${item.label}</span><strong>${money(item.value)} <span style="color:#849198;font-weight:400">(${share}%)</span></strong></div>`;
        }).join('');
    }

    function renderBarChart(daily) {
        const svg = document.getElementById('bar-chart');
        const rows = daily.slice(-14);
        const width = 600, height = 250, left = 40, right = 8, top = 18, bottom = 32;
        const plotHeight = height - top - bottom;
        const maxMiles = Math.max(1, ...rows.map(row => Number(row.distance_miles) || 0)) * 1.12;
        const maxDeliveries = Math.max(1, ...rows.map(row => Number(row.deliveries) || 0));
        const slot = (width - left - right) / Math.max(1, rows.length);
        svg.replaceChildren();
        [0, .5, 1].forEach(fraction => {
            const y = top + plotHeight * fraction;
            svg.appendChild(svgEl('line', { x1: left, x2: width - right, y1: y, y2: y, class: 'chart-gridline' }));
        });
        rows.forEach((row, index) => {
            const group = svgEl('g', { transform: `translate(${left + index * slot},0)` });
            const barWidth = Math.min(17, slot * .3);
            const milesHeight = plotHeight * (Number(row.distance_miles) || 0) / maxMiles;
            const deliveryHeight = plotHeight * (Number(row.deliveries) || 0) / maxDeliveries;
            const baseline = top + plotHeight;
            group.appendChild(svgEl('rect', { x: slot * .22, y: baseline - milesHeight, width: barWidth, height: Math.max(0, milesHeight), rx: 2, fill: colors.miles, class: 'chart-bar', style: `animation-delay:${Math.min(index * 25, 250)}ms` }));
            group.appendChild(svgEl('rect', { x: slot * .22 + barWidth + 4, y: baseline - deliveryHeight, width: barWidth, height: Math.max(0, deliveryHeight), rx: 2, fill: colors.deliveries, class: 'chart-bar', style: `animation-delay:${Math.min(index * 25 + 60, 300)}ms` }));
            if (index % Math.max(1, Math.ceil(rows.length / 7)) === 0 || index === rows.length - 1) {
                const label = svgEl('text', { x: slot / 2, y: height - 7, 'text-anchor': 'middle' });
                label.textContent = new Date(`${row.date}T00:00:00Z`).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', timeZone: 'UTC' });
                group.appendChild(label);
            }
            svg.appendChild(group);
        });
        renderLegend('bar-legend', [
            { label: 'Miles travelled (scaled to peak day)', color: colors.miles },
            { label: 'Deliveries completed (scaled to peak day)', color: colors.deliveries }
        ]);
    }

    function renderLive(records, assumptions) {
        const active = records.filter(item => item.status === 'in_transit');
        const container = document.getElementById('live-deliveries');
        if (!active.length) {
            container.innerHTML = '<div class="pie-row"><span>No deliveries currently in transit</span><span>Fleet standing by</span></div>';
            return;
        }
        container.innerHTML = active.map(item => {
            const finance = estimatedFinance(item, assumptions);
            const percent = Math.round(Math.min(1, Number(item.progress) || 0) * 100);
            return `<div style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,.07)">
                <div class="pie-row"><strong>${escapeHtml(item.truck_id)}</strong><span>${percent}% · ${number(finance.miles)} / ${number(item.route_distance_miles || item.distance_miles)} mi</span></div>
                <div style="color:#89969d;font-size:.79rem;margin-top:7px">${escapeHtml(item.origin)} → ${escapeHtml(item.destination)}</div>
                <div style="color:#b8c2c6;font-size:.8rem;margin-top:7px">Earned ${money(finance.revenue)} · estimated net ${money(finance.profit)}</div>
                <div style="height:3px;background:rgba(255,255,255,.08);margin-top:10px"><i style="display:block;height:100%;width:${percent}%;background:var(--accent-orange);transition:width .8s ease"></i></div>
            </div>`;
        }).join('');
    }

    function renderRecords(records) {
        const body = document.getElementById('records-body');
        const ordered = [...records].sort((a, b) => Number(b.recorded_at || 0) - Number(a.recorded_at || 0));
        if (!ordered.length) {
            body.innerHTML = '<tr><td colspan="10">No delivery records yet. Financial activity appears as deliveries move.</td></tr>';
            return;
        }
        body.innerHTML = ordered.map(item => {
            const date = new Date((Number(item.recorded_at) || 0) * 1000).toLocaleString();
            return `<tr>
                <td>${escapeHtml(date)}</td><td>${escapeHtml(String(item.status || '').replace('_', ' '))}</td>
                <td>${escapeHtml(item.truck_id)}</td><td>${escapeHtml(item.origin)} → ${escapeHtml(item.destination)}</td>
                <td>${number(item.distance_miles)}</td><td>${number(item.fuel_gallons, 2)}</td>
                <td>${preciseMoney(item.revenue)}</td><td>${preciseMoney(item.fuel_cost)}</td>
                <td>${preciseMoney(item.operating_cost)}</td><td>${preciseMoney(item.profit)}</td>
            </tr>`;
        }).join('');
    }

    async function refresh() {
        try {
            const response = await fetch('/api/analytics', { cache: 'no-store' });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Analytics are unavailable.');
            renderMetrics(data);
            renderLineChart(data.daily || []);
            renderPie(data);
            renderBarChart(data.daily || []);
            renderLive(data.records || [], data.assumptions);
            renderRecords(data.records || []);
            document.getElementById('analytics-error').style.display = 'none';
        } catch (error) {
            const notice = document.getElementById('analytics-error');
            notice.textContent = error.message || 'Analytics are temporarily unavailable.';
            notice.style.display = 'block';
        }
    }

    refresh();
    window.setInterval(refresh, 12000);
})();
