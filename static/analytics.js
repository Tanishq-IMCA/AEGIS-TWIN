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
    const animations = new WeakMap();
    const lineCircles = new Map();
    const barDays = new Map();

    function layer(svg, name) {
        let group = svg.querySelector(`[data-layer="${name}"]`);
        if (!group) {
            group = svgEl('g', { 'data-layer': name });
            svg.appendChild(group);
        }
        return group;
    }

    function bindTooltip(target, tooltipId) {
        if (target.dataset.tooltipBound) return;
        target.dataset.tooltipBound = 'true';
        const tooltip = document.getElementById(tooltipId);
        const show = event => {
            if (!target._tooltipHTML) return;
            const panel = target.closest('.analytics-panel');
            if (!panel || !tooltip) return;
            tooltip.innerHTML = target._tooltipHTML;
            tooltip.style.display = 'block';
            const bounds = panel.getBoundingClientRect();
            const x = event.clientX ? event.clientX - bounds.left + 12 : 18;
            const y = event.clientY ? event.clientY - bounds.top + 12 : 50;
            tooltip.style.left = `${Math.max(10, Math.min(x, panel.clientWidth - tooltip.offsetWidth - 10))}px`;
            tooltip.style.top = `${Math.max(10, Math.min(y, panel.clientHeight - tooltip.offsetHeight - 10))}px`;
        };
        target.addEventListener('pointerenter', show);
        target.addEventListener('pointermove', show);
        target.addEventListener('pointerleave', () => { tooltip.style.display = 'none'; });
        target.addEventListener('focus', show);
        target.addEventListener('blur', () => { tooltip.style.display = 'none'; });
    }

    function animateAttributes(node, targets, duration = 760) {
        const prior = animations.get(node);
        if (prior) cancelAnimationFrame(prior);
        const from = {};
        Object.keys(targets).forEach(key => {
            from[key] = Number(node.getAttribute(key));
            if (!Number.isFinite(from[key])) from[key] = Number(targets[key]) || 0;
        });
        const start = performance.now();
        const ease = t => 1 - Math.pow(1 - t, 3);
        const step = now => {
            const t = Math.min(1, (now - start) / duration);
            const eased = ease(t);
            Object.keys(targets).forEach(key => {
                const value = from[key] + (Number(targets[key]) - from[key]) * eased;
                node.setAttribute(key, value.toFixed(2));
            });
            if (t < 1) animations.set(node, requestAnimationFrame(step));
            else animations.delete(node);
        };
        animations.set(node, requestAnimationFrame(step));
    }

    function animatePath(path, points, baseline) {
        const previous = path._chartPoints || [];
        const starts = points.map((point, index) => {
            if (!previous.length) return [point[0], baseline];
            const sourceIndex = points.length < 2 ? 0 : index * (previous.length - 1) / (points.length - 1);
            const lower = Math.floor(sourceIndex);
            const upper = Math.min(previous.length - 1, lower + 1);
            const ratio = sourceIndex - lower;
            return [
                previous[lower][0] + (previous[upper][0] - previous[lower][0]) * ratio,
                previous[lower][1] + (previous[upper][1] - previous[lower][1]) * ratio
            ];
        });
        const prior = animations.get(path);
        if (prior) cancelAnimationFrame(prior);
        const start = performance.now();
        const ease = t => 1 - Math.pow(1 - t, 3);
        const step = now => {
            const t = Math.min(1, (now - start) / 760);
            const eased = ease(t);
            const current = points.map((point, index) => [
                starts[index][0] + (point[0] - starts[index][0]) * eased,
                starts[index][1] + (point[1] - starts[index][1]) * eased
            ]);
            path.setAttribute('d', current.length
                ? `M ${current.map(point => `${point[0].toFixed(2)},${point[1].toFixed(2)}`).join(' L ')}`
                : '');
            if (t < 1) animations.set(path, requestAnimationFrame(step));
            else animations.delete(path);
        };
        path._chartPoints = points;
        animations.set(path, requestAnimationFrame(step));
    }

    function formatDay(day, options = { month: 'short', day: 'numeric' }) {
        return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-US', { ...options, timeZone: 'UTC' });
    }

    function niceAxisMax(value) {
        if (value <= 1) return 1;
        const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
        const scaled = value / magnitude;
        return (scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10) * magnitude;
    }

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
        const width = 720, height = 280, left = 62, right = 18, top = 20, bottom = 48;
        const plotWidth = width - left - right, plotHeight = height - top - bottom;
        const values = rows.flatMap(row => series.map(item => Number(row[item.key]) || 0));
        const rawMin = Math.min(0, ...values), rawMax = Math.max(1, ...values);
        const padding = Math.max(1, (rawMax - rawMin) * .08);
        const min = rawMin < 0 ? rawMin - padding : 0;
        const max = rawMax + padding;
        const span = max - min || 1;
        const baseline = top + plotHeight * (max / span);
        const axes = layer(svg, 'axes');
        const paths = layer(svg, 'series');
        const pointsLayer = layer(svg, 'points');
        axes.replaceChildren();
        for (let index = 0; index <= 4; index++) {
            const y = top + plotHeight * index / 4;
            axes.appendChild(svgEl('line', { x1: left, x2: width - right, y1: y, y2: y, class: 'chart-gridline' }));
            const label = svgEl('text', { x: left - 8, y: y + 4, 'text-anchor': 'end' });
            label.textContent = money(max - span * index / 4);
            axes.appendChild(label);
        }
        const yTitle = svgEl('text', { x: 14, y: top + plotHeight / 2, 'text-anchor': 'middle', class: 'axis-title', transform: `rotate(-90 14 ${top + plotHeight / 2})` });
        yTitle.textContent = 'USD PER DAY';
        axes.appendChild(yTitle);
        const dateTicks = rows.length ? [0, .25, .5, .75, 1] : [];
        dateTicks.forEach(fraction => {
            const index = Math.min(rows.length - 1, Math.round((rows.length - 1) * fraction));
            const label = svgEl('text', { x: left + plotWidth * fraction, y: height - 19, 'text-anchor': 'middle' });
            label.textContent = formatDay(rows[index].date);
            axes.appendChild(label);
        });
        const xTitle = svgEl('text', { x: left + plotWidth / 2, y: height - 3, 'text-anchor': 'middle', class: 'axis-title' });
        xTitle.textContent = 'DATE';
        axes.appendChild(xTitle);

        series.forEach(item => {
            const coordinates = rows.map((row, index) => {
                const x = left + plotWidth * (rows.length < 2 ? .5 : index / (rows.length - 1));
                const y = top + plotHeight * (max - (Number(row[item.key]) || 0)) / span;
                return [x, y];
            });
            let path = paths.querySelector(`path[data-series="${item.key}"]`);
            if (!path) {
                path = svgEl('path', { stroke: item.color, class: `chart-series${item.dotted ? ' dotted' : ''}`, 'data-series': item.key });
                paths.appendChild(path);
            }
            path.setAttribute('stroke', item.color);
            path.setAttribute('class', `chart-series${item.dotted ? ' dotted' : ''}`);
            animatePath(path, coordinates.length ? coordinates : [[left, baseline], [width - right, baseline]], baseline);

            let circles = lineCircles.get(item.key) || [];
            const updatedCircles = coordinates.map(([x, y], index) => {
                let circle = circles[index];
                if (!circle) {
                    circle = svgEl('circle', { cx: x, cy: baseline, r: 0, fill: item.color, class: 'chart-point', tabindex: '0', role: 'img' });
                    pointsLayer.appendChild(circle);
                    bindTooltip(circle, 'line-tooltip');
                }
                const row = rows[index];
                circle._tooltipHTML = `<strong>${escapeHtml(formatDay(row.date))}</strong>${escapeHtml(item.label)}: ${money(row[item.key])}`;
                circle.setAttribute('aria-label', `${formatDay(row.date)}, ${item.label}: ${money(row[item.key])}`);
                animateAttributes(circle, { cx: x, cy: y, r: 4 });
                return circle;
            });
            circles.slice(updatedCircles.length).forEach(circle => circle.remove());
            lineCircles.set(item.key, updatedCircles);
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
        const pie = document.getElementById('cost-pie');
        pie._tooltipHTML = `<strong>Estimated cost composition</strong>Fuel: ${preciseMoney(totals.fuel_cost)}<br>Delivery operations: ${preciseMoney(totals.operating_cost)}<br>Total: ${preciseMoney(totals.total_cost)}`;
        bindTooltip(pie, 'pie-tooltip');
    }

    function renderBarChart(daily) {
        const svg = document.getElementById('bar-chart');
        const rows = daily.slice(-14);
        const width = 600, height = 280, left = 58, right = 58, top = 34, bottom = 52;
        const plotHeight = height - top - bottom, plotWidth = width - left - right;
        const maxMiles = niceAxisMax(Math.max(0, ...rows.map(row => Number(row.distance_miles) || 0)) * 1.08);
        const maxDeliveries = niceAxisMax(Math.max(0, ...rows.map(row => Number(row.deliveries) || 0)));
        const slot = plotWidth / Math.max(1, rows.length);
        const baseline = top + plotHeight;
        const bars = layer(svg, 'bars');
        const axes = layer(svg, 'axes');
        axes.replaceChildren();
        [0, .5, 1].forEach(fraction => {
            const y = top + plotHeight * (1 - fraction);
            axes.appendChild(svgEl('line', { x1: left, x2: width - right, y1: y, y2: y, class: 'chart-gridline' }));
            const leftLabel = svgEl('text', { x: left - 8, y: y + 4, 'text-anchor': 'end' });
            leftLabel.textContent = number(maxMiles * fraction, 0);
            axes.appendChild(leftLabel);
            const rightLabel = svgEl('text', { x: width - right + 8, y: y + 4, 'text-anchor': 'start' });
            rightLabel.textContent = number(maxDeliveries * fraction, 0);
            axes.appendChild(rightLabel);
        });
        const leftTitle = svgEl('text', { x: 13, y: top + plotHeight / 2, 'text-anchor': 'middle', class: 'axis-title', transform: `rotate(-90 13 ${top + plotHeight / 2})` });
        leftTitle.textContent = 'MILES';
        axes.appendChild(leftTitle);
        const rightTitle = svgEl('text', { x: width - 7, y: top + plotHeight / 2, 'text-anchor': 'middle', class: 'axis-title', transform: `rotate(90 ${width - 7} ${top + plotHeight / 2})` });
        rightTitle.textContent = 'DELIVERIES';
        axes.appendChild(rightTitle);
        const labelStep = Math.max(1, Math.ceil(rows.length / 7));
        rows.forEach((row, index) => {
            let group = barDays.get(row.date);
            if (!group) {
                group = svgEl('g', { 'data-date': row.date });
                const hitArea = svgEl('rect', { x: 0, y: top, width: slot, height: plotHeight, fill: 'transparent', 'pointer-events': 'all', tabindex: '0', role: 'img' });
                const milesBar = svgEl('rect', { x: 0, y: baseline, width: 0, height: 0, rx: 2, fill: colors.miles, class: 'chart-bar' });
                const deliveriesBar = svgEl('rect', { x: 0, y: baseline, width: 0, height: 0, rx: 2, fill: colors.deliveries, class: 'chart-bar' });
                group.append(hitArea, milesBar, deliveriesBar);
                bars.appendChild(group);
                group._hitArea = hitArea;
                group._milesBar = milesBar;
                group._deliveriesBar = deliveriesBar;
                barDays.set(row.date, group);
                bindTooltip(hitArea, 'bar-tooltip');
                bindTooltip(milesBar, 'bar-tooltip');
                bindTooltip(deliveriesBar, 'bar-tooltip');
            }
            group.setAttribute('transform', `translate(${left + index * slot},0)`);
            const barWidth = Math.min(15, slot * .27);
            const milesHeight = plotHeight * (Number(row.distance_miles) || 0) / maxMiles;
            const deliveryHeight = plotHeight * (Number(row.deliveries) || 0) / maxDeliveries;
            const barX = (slot - (barWidth * 2 + 5)) / 2;
            group._hitArea.setAttribute('width', slot);
            group._hitArea.setAttribute('height', plotHeight);
            group._hitArea._tooltipHTML = `<strong>${escapeHtml(formatDay(row.date, { weekday: 'short', month: 'short', day: 'numeric' }))}</strong>Distance travelled: ${number(row.distance_miles)} mi<br>Completed deliveries: ${number(row.deliveries, 0)}`;
            const milesLabel = `${formatDay(row.date)} · ${number(row.distance_miles)} miles travelled`;
            const deliveriesLabel = `${formatDay(row.date)} · ${number(row.deliveries, 0)} deliveries completed`;
            group._milesBar._tooltipHTML = `<strong>${escapeHtml(formatDay(row.date))}</strong>Distance travelled: ${number(row.distance_miles)} mi`;
            group._deliveriesBar._tooltipHTML = `<strong>${escapeHtml(formatDay(row.date))}</strong>Completed deliveries: ${number(row.deliveries, 0)}`;
            group._hitArea.setAttribute('aria-label', `${milesLabel}; ${deliveriesLabel}`);
            animateAttributes(group._milesBar, {
                x: barX, y: baseline - milesHeight, width: barWidth, height: milesHeight
            });
            animateAttributes(group._deliveriesBar, {
                x: barX + barWidth + 5, y: baseline - deliveryHeight, width: barWidth, height: deliveryHeight
            });
            if (index % labelStep === 0 || index === rows.length - 1) {
                const label = svgEl('text', { x: left + index * slot + slot / 2, y: height - 22, 'text-anchor': 'middle' });
                label.textContent = formatDay(row.date, { month: 'numeric', day: 'numeric' });
                axes.appendChild(label);
            }
        });
        const dates = new Set(rows.map(row => row.date));
        for (const [date, group] of barDays) {
            if (!dates.has(date)) {
                group.remove();
                barDays.delete(date);
            }
        }
        const xTitle = svgEl('text', { x: left + plotWidth / 2, y: height - 3, 'text-anchor': 'middle', class: 'axis-title' });
        xTitle.textContent = 'DATE';
        axes.appendChild(xTitle);
        if (!rows.length) {
            const empty = svgEl('text', { x: left + plotWidth / 2, y: top + plotHeight / 2, 'text-anchor': 'middle' });
            empty.textContent = 'NO FLEET ACTIVITY YET';
            axes.appendChild(empty);
        }
        renderLegend('bar-legend', [
            { label: 'Miles travelled', color: colors.miles },
            { label: 'Deliveries completed', color: colors.deliveries }
        ]);
    }

    function renderLive(records, assumptions) {
        const active = records.filter(item => item.status === 'in_transit');
        const container = document.getElementById('live-deliveries');
        const scrollTop = container.scrollTop;
        if (!active.length) {
            container.innerHTML = '<div class="pie-row"><span>No deliveries currently in transit</span><span>Fleet standing by</span></div>';
            return;
        }
        container.innerHTML = active.map(item => {
            const finance = estimatedFinance(item, assumptions);
            const percent = Math.round(Math.min(1, Number(item.progress) || 0) * 100);
            return `<div class="live-delivery-row">
                <div class="pie-row"><strong>${escapeHtml(item.truck_id)}</strong><span>${percent}% · ${number(finance.miles)} / ${number(item.route_distance_miles || item.distance_miles)} mi</span></div>
                <div style="color:#89969d;font-size:.79rem;margin-top:7px">${escapeHtml(item.origin)} → ${escapeHtml(item.destination)}</div>
                <div style="color:#b8c2c6;font-size:.8rem;margin-top:7px">Earned ${money(finance.revenue)} · estimated net ${money(finance.profit)}</div>
                <div style="height:3px;background:rgba(255,255,255,.08);margin-top:10px"><i style="display:block;height:100%;width:${percent}%;background:var(--accent-orange);transition:width .8s ease"></i></div>
            </div>`;
        }).join('');
        container.scrollTop = scrollTop;
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
