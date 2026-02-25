
(function () {
    "use strict";

    const TOTAL_SEATS = 28;
    const ALERT_LIMIT = 20;
    const HISTORY_POINTS_MAX = 720;

    const STATE_COLORS = {
        empty:     "#22c55e",
        occupied:  "#ef4444",
        suspected: "#eab308",
        ghost:     "#a855f7",
    };

    const ZONE_DEFINITIONS = [
        "Zone A - Window",
        "Zone B - Center",
        "Zone C - Back Wall",
        "Zone D - Study Pods",
        "Zone E - Group Tables",
        "Zone F - Quiet Area",
        "Zone G - Lounge",
        "Zone H - Entrance",
    ];

    const socket = io({ transports: ["websocket", "polling"] });

    socket.on("connect", () => {
        setConnectionStatus(true);
        console.log("[Dashboard] Connected to server");
        socket.emit("request_history", { minutes: 60 });
    });

    socket.on("disconnect", () => {
        setConnectionStatus(false);
        console.warn("[Dashboard] Disconnected from server");
    });

    const dom = {
        clock:            document.getElementById("live-clock"),
        connStatus:       document.getElementById("connection-status"),
        sensorIndicators: document.getElementById("sensor-indicators"),
        cameraImg:        {},
        cameraOverlay:    {},
        zoneGrid:         document.getElementById("zone-grid"),
        seatGrid:         document.getElementById("seat-grid"),
        radarList:        document.getElementById("radar-list"),
        alertFeed:        document.getElementById("alert-feed"),
        chartCanvas:      document.getElementById("history-chart"),
        statOccupied:     document.getElementById("stat-occupied"),
        statEmpty:        document.getElementById("stat-empty"),
        statGhost:        document.getElementById("stat-ghost"),
        statScans:        document.getElementById("stat-scans"),
        statUtil:         document.getElementById("stat-util"),
        tooltip:          document.getElementById("seat-tooltip"),
    };

    let seats = {};
    let zones = {};
    let alertCount = 0;
    let historyChart = null;

    function init() {
        dom.cameraImg["back_rail"]  = document.getElementById("camera-img-back");
        dom.cameraImg["front_rail"] = document.getElementById("camera-img-front");
        dom.cameraOverlay["back_rail"]  = document.getElementById("camera-overlay-back_rail");
        dom.cameraOverlay["front_rail"] = document.getElementById("camera-overlay-front_rail");

        buildZoneGrid();
        buildSeatGrid();
        buildRadarList();
        initHistoryChart();
        startClock();

        socket.on("telemetry",     handleTelemetry);
        socket.on("camera_frame",  handleCameraFrame);
        socket.on("sensor_status", handleSensorStatus);
        socket.on("ghost_alert",   handleGhostAlert);
        socket.on("stats",         handleStats);
        socket.on("seat_state",    handleSeatState);
        socket.on("history_data",  handleHistoryData);
    }

    function startClock() {
        function tick() {
            const now = new Date();
            dom.clock.textContent = now.toLocaleTimeString("en-US", {
                hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
            });
        }
        tick();
        setInterval(tick, 1000);
    }

    function setConnectionStatus(connected) {
        const el = dom.connStatus;
        if (connected) {
            el.className = "connection-status";
            el.innerHTML = '<span class="dot"></span> LIVE';
        } else {
            el.className = "connection-status disconnected";
            el.innerHTML = '<span class="dot"></span> OFFLINE';
        }
    }

    function handleSensorStatus(data) {
        let el = document.getElementById("sensor-ind-" + data.sensor_id);
        if (!el) {
            el = document.createElement("div");
            el.className = "sensor-indicator";
            el.id = "sensor-ind-" + data.sensor_id;
            el.innerHTML =
                '<span class="sensor-dot"></span><span class="sensor-label"></span>';
            dom.sensorIndicators.appendChild(el);
        }
        const dot = el.querySelector(".sensor-dot");
        const label = el.querySelector(".sensor-label");
        label.textContent = data.sensor_id;

        dot.className = "sensor-dot";
        const status = (data.status || "").toLowerCase();
        if (status === "scanning" || status === "online") {
            dot.classList.add("online");
            if (status === "scanning") dot.classList.add("scanning");
        }

        const camId = data.sensor_id;
        if (dom.cameraOverlay[camId]) {
            const overlay = dom.cameraOverlay[camId];
            const badge = overlay.querySelector(".status-badge");
            const zoneSub = overlay.querySelector(".zone-sub");
            if (badge) {
                badge.className = "status-badge " + status;
                badge.textContent = status.toUpperCase() || "IDLE";
            }
            if (zoneSub) {
                zoneSub.textContent = data.zone ? "Scanning: " + data.zone : "";
            }
        }
    }

    function handleCameraFrame(data) {
        const imgEl = dom.cameraImg[data.sensor_id];
        if (imgEl && data.image) {
            imgEl.src = "data:image/jpeg;base64," + data.image;
            imgEl.style.display = "block";
            const placeholder = imgEl.parentElement.querySelector(".camera-placeholder");
            if (placeholder) placeholder.style.display = "none";
        }
    }

    function buildZoneGrid() {
        dom.zoneGrid.innerHTML = "";
        ZONE_DEFINITIONS.forEach((name, i) => {
            const card = document.createElement("div");
            card.className = "zone-card state-empty";
            card.id = "zone-card-" + i;
            if (name.includes("Lounge")) card.classList.add("dimmed");
            card.innerHTML = `
                <div class="zone-name">${name}</div>
                <div class="zone-count">0 <span style="font-size:.75rem;font-weight:400;color:var(--text-muted)">/ 0</span></div>
                <div class="zone-total">No data yet</div>
                <div class="zone-bar"><div class="zone-bar-fill" style="width:0%"></div></div>
            `;
            dom.zoneGrid.appendChild(card);
        });
    }

    function updateZoneCard(zoneName, zoneData) {
        const idx = ZONE_DEFINITIONS.findIndex(
            (z) => z.toLowerCase() === zoneName.toLowerCase() ||
                   z.toLowerCase().includes(zoneName.toLowerCase())
        );
        if (idx < 0) return;

        const card = document.getElementById("zone-card-" + idx);
        if (!card) return;

        const occupied = zoneData.occupied || 0;
        const total = zoneData.total || 0;

        let dominantState = "empty";
        if (zoneData.seats) {
            const counts = { empty: 0, occupied: 0, suspected: 0, ghost: 0 };
            const seatValues = typeof zoneData.seats === "object"
                ? Object.values(zoneData.seats) : zoneData.seats;
            seatValues.forEach((s) => {
                const st = s.state || "empty";
                if (counts[st] !== undefined) counts[st]++;
            });
            if (counts.ghost > 0)         dominantState = "ghost";
            else if (counts.suspected > 0) dominantState = "suspected";
            else if (counts.occupied > 0)  dominantState = "occupied";
        } else if (occupied > 0) {
            dominantState = "occupied";
        }

        card.className = "zone-card state-" + dominantState;
        if (ZONE_DEFINITIONS[idx].includes("Lounge")) card.classList.add("dimmed");

        const pct = total > 0 ? Math.round((occupied / total) * 100) : 0;

        card.querySelector(".zone-count").innerHTML =
            `${occupied} <span style="font-size:.75rem;font-weight:400;color:var(--text-muted)">/ ${total}</span>`;
        card.querySelector(".zone-total").textContent =
            `${pct}% occupied`;
        card.querySelector(".zone-bar-fill").style.width = pct + "%";
    }

    function buildSeatGrid() {
        dom.seatGrid.innerHTML = "";
        for (let i = 1; i <= TOTAL_SEATS; i++) {
            const dot = document.createElement("div");
            dot.className = "seat-dot empty";
            dot.id = "seat-" + i;
            dot.dataset.seatId = i;
            dot.textContent = i;

            dot.addEventListener("mouseenter", showTooltip);
            dot.addEventListener("mousemove", moveTooltip);
            dot.addEventListener("mouseleave", hideTooltip);

            dom.seatGrid.appendChild(dot);
        }
    }

    function updateSeatDot(seatId, seatData) {
        const numId = parseInt(String(seatId).replace(/\D/g, ""), 10);
        const dot = document.getElementById("seat-" + numId);
        if (!dot) return;

        const st = seatData.state || "empty";
        dot.className = "seat-dot " + st;
        dot.dataset.state = st;
        dot.dataset.presence = seatData.presence != null ? seatData.presence : "";
        dot.dataset.zone = seatData.zone || "";
    }

    function showTooltip(e) {
        const d = e.currentTarget.dataset;
        const tt = dom.tooltip;
        tt.innerHTML = `
            <div class="tt-id">Seat ${d.seatId}</div>
            <div class="tt-state" style="color:${STATE_COLORS[d.state] || '#94a3b8'}">
                ${(d.state || "unknown")}
            </div>
            <div class="tt-presence">Presence: ${d.presence || "N/A"}%</div>
            ${d.zone ? '<div style="color:var(--text-muted);margin-top:2px">' + d.zone + '</div>' : ""}
        `;
        tt.classList.add("visible");
        moveTooltip(e);
    }

    function moveTooltip(e) {
        dom.tooltip.style.left = (e.clientX + 14) + "px";
        dom.tooltip.style.top  = (e.clientY - 10) + "px";
    }

    function hideTooltip() {
        dom.tooltip.classList.remove("visible");
    }

    function buildRadarList() {
        dom.radarList.innerHTML = "";
        for (let i = 1; i <= TOTAL_SEATS; i++) {
            const row = document.createElement("div");
            row.className = "radar-row";
            row.id = "radar-row-" + i;
            row.innerHTML = `
                <span class="radar-label">S${String(i).padStart(2, "0")}</span>
                <div class="radar-bar-bg">
                    <div class="radar-bar-fill empty" style="width:0%"></div>
                </div>
                <span class="radar-value">0%</span>
            `;
            dom.radarList.appendChild(row);
        }
    }

    function updateRadarBar(seatId, seatData) {
        const numId = parseInt(String(seatId).replace(/\D/g, ""), 10);
        const row = document.getElementById("radar-row-" + numId);
        if (!row) return;

        const presence = parseFloat(seatData.presence) || 0;
        const st = seatData.state || "empty";
        const fill = row.querySelector(".radar-bar-fill");
        const val  = row.querySelector(".radar-value");

        fill.style.width = Math.min(presence, 100) + "%";
        fill.className = "radar-bar-fill " + st;
        val.textContent = Math.round(presence) + "%";
    }

    function handleGhostAlert(data) {
        alertCount++;

        const emptyMsg = dom.alertFeed.querySelector(".alert-empty");
        if (emptyMsg) emptyMsg.remove();

        const item = document.createElement("div");
        const alertType = data.type || "ghost";
        item.className = "alert-item type-" + alertType;

        const iconMap = {
            ghost:    "\u{1F47B}",
            warning:  "\u26A0\uFE0F",
            critical: "\u{1F6A8}",
            info:     "\u{2139}\uFE0F",
        };
        const icon = iconMap[alertType] || iconMap.ghost;

        const ts = data.timestamp
            ? new Date(data.timestamp).toLocaleTimeString("en-US", { hour12: false })
            : new Date().toLocaleTimeString("en-US", { hour12: false });

        const countdownHtml = data.countdown
            ? `<span class="alert-countdown" data-countdown="${data.countdown}">${data.countdown}s</span>`
            : "";

        item.innerHTML = `
            <div class="alert-icon">${icon}</div>
            <div class="alert-body">
                <div class="alert-message">${escapeHtml(data.message || "Ghost detected")}</div>
                <div class="alert-meta">
                    <span>${ts}</span>
                    ${data.seat_id ? "<span>Seat " + escapeHtml(String(data.seat_id)) + "</span>" : ""}
                    ${data.zone ? "<span>" + escapeHtml(data.zone) + "</span>" : ""}
                </div>
            </div>
            ${countdownHtml}
        `;

        dom.alertFeed.prepend(item);

        while (dom.alertFeed.children.length > ALERT_LIMIT) {
            dom.alertFeed.removeChild(dom.alertFeed.lastChild);
        }

        if (data.countdown) {
            startCountdown(item.querySelector(".alert-countdown"), data.countdown);
        }
    }

    function startCountdown(el, seconds) {
        let remaining = seconds;
        const iv = setInterval(() => {
            remaining--;
            if (remaining <= 0) {
                clearInterval(iv);
                el.textContent = "EXPIRED";
                el.style.color = "var(--color-red)";
                return;
            }
            el.textContent = remaining + "s";
        }, 1000);
    }

    function initHistoryChart() {
        const ctx = dom.chartCanvas.getContext("2d");

        historyChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Occupied",
                        data: [],
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239,68,68,.08)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: "Empty",
                        data: [],
                        borderColor: "#22c55e",
                        backgroundColor: "rgba(34,197,94,.06)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: "Ghost",
                        data: [],
                        borderColor: "#a855f7",
                        backgroundColor: "rgba(168,85,247,.06)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: "top",
                        align: "end",
                        labels: {
                            color: "#94a3b8",
                            boxWidth: 10,
                            boxHeight: 10,
                            padding: 16,
                            font: { size: 11, family: "system-ui" },
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(17,24,39,.95)",
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                        borderColor: "#374151",
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8,
                        titleFont: { weight: "600" },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(31,41,55,.5)", drawBorder: false },
                        ticks: {
                            color: "#64748b",
                            maxRotation: 0,
                            font: { size: 10 },
                            maxTicksLimit: 12,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(31,41,55,.5)", drawBorder: false },
                        ticks: {
                            color: "#64748b",
                            font: { size: 10 },
                            stepSize: 1,
                        },
                    },
                },
                animation: {
                    duration: 400,
                },
            },
        });
    }

    function addHistoryPoint(point) {
        if (!historyChart) return;
        const labels = historyChart.data.labels;
        const ts = new Date(point.ts).toLocaleTimeString("en-US", {
            hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
        });

        labels.push(ts);
        historyChart.data.datasets[0].data.push(point.occupied || 0);
        historyChart.data.datasets[1].data.push(point.empty || 0);
        historyChart.data.datasets[2].data.push(point.ghost || 0);

        if (labels.length > HISTORY_POINTS_MAX) {
            labels.shift();
            historyChart.data.datasets.forEach((ds) => ds.data.shift());
        }

        historyChart.update("none");
    }

    function handleHistoryData(data) {
        if (!historyChart || !Array.isArray(data)) return;
        historyChart.data.labels = [];
        historyChart.data.datasets.forEach((ds) => (ds.data = []));

        data.forEach((point) => {
            const ts = new Date(point.ts).toLocaleTimeString("en-US", {
                hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
            });
            historyChart.data.labels.push(ts);
            historyChart.data.datasets[0].data.push(point.occupied || 0);
            historyChart.data.datasets[1].data.push(point.empty || 0);
            historyChart.data.datasets[2].data.push(point.ghost || 0);
        });

        historyChart.update();
    }

    function handleTelemetry(data) {
        if (data.zone && data.zone_data) {
            zones[data.zone] = data.zone_data;
            updateZoneCard(data.zone, data.zone_data);
        }
        if (data.stats) {
            handleStats(data.stats);
        }

        if (data.stats) {
            addHistoryPoint({
                ts: new Date().toISOString(),
                occupied: data.stats.occupied || 0,
                empty: data.stats.empty || 0,
                ghost: data.stats.ghost || 0,
            });
        }
    }

    function handleSeatState(data) {
        if (!data.seats) return;
        seats = data.seats;
        Object.entries(seats).forEach(([id, sdata]) => {
            updateSeatDot(id, sdata);
            updateRadarBar(id, sdata);
        });
    }

    function handleStats(data) {
        if (!data) return;
        animateNumber(dom.statOccupied, data.occupied || 0);
        animateNumber(dom.statEmpty, data.empty || 0);
        animateNumber(dom.statGhost, data.ghost || 0);
        animateNumber(dom.statScans, data.total_scans || 0);
        dom.statUtil.textContent = (data.utilization || 0).toFixed(1) + "%";
    }

    function animateNumber(el, target) {
        const current = parseInt(el.textContent, 10) || 0;
        if (current === target) return;
        el.textContent = target;
        el.style.transform = "scale(1.15)";
        setTimeout(() => { el.style.transform = "scale(1)"; }, 200);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
