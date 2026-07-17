const API_BASE = "https://bengaluru-water-crisis-6.onrender.com/api"; // relative — works locally and on any deployed domain

const RISK_COLORS = {
  Low: "#2fb8a6",
  Medium: "#d9a441",
  High: "#d16a3a",
  Critical: "#c23a34",
};
const RISK_ORDER = ["Low", "Medium", "High", "Critical"];

const map = L.map("map", { zoomControl: true }).setView([12.965, 77.605], 11);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  maxZoom: 19,
}).addTo(map);

let trendChart = null;
let scrubberChart = null;
const markers = {};       // ward_id -> Leaflet marker
let currentWards = [];    // wards currently loaded on the map (for the active month)
let activeMonth = null;   // { year, month, date } or null = "latest"
let activeCategory = null; // "Low" | "Medium" | "High" | "Critical" | null = all

function radiusForRisk(score) {
  return 8 + (score / 100) * 14;
}

function clearMarkers() {
  Object.values(markers).forEach((m) => map.removeLayer(m));
  for (const k in markers) delete markers[k];
}

function renderMarkers(wards) {
  clearMarkers();
  wards.forEach((ward) => {
    const visible = !activeCategory || ward.risk_label === activeCategory;
    if (!visible) return;

    const color = RISK_COLORS[ward.risk_label] || "#8fa0ac";
    const marker = L.circleMarker([ward.lat, ward.lon], {
      radius: radiusForRisk(ward.risk_score),
      fillColor: color,
      color: color,
      weight: 1.5,
      fillOpacity: 0.55,
      className: ward.risk_label === "Critical" ? "ward-marker-critical" : "",
    }).addTo(map);

    marker.bindTooltip(`${ward.ward_name} — ${ward.risk_score} (${ward.risk_label})`, {
      direction: "top",
      offset: [0, -6],
    });

    marker.on("click", () => selectWard(ward.ward_id));
    markers[ward.ward_id] = marker;
  });
}

function updateMonthBadge() {
  const badge = document.getElementById("month-badge");
  const reset = document.getElementById("reset-month");
  if (!activeMonth) {
    badge.firstChild.textContent = "viewing latest data";
    reset.textContent = "";
  } else {
    const label = new Date(activeMonth.date).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
    badge.firstChild.textContent = `viewing ${label}`;
    reset.textContent = "· back to latest";
  }
}

async function loadWardsForLatest() {
  const res = await fetch(`${API_BASE}/wards`);
  currentWards = await res.json();
  renderMarkers(currentWards);
}

async function loadWardsForMonth(year, month, date) {
  const res = await fetch(`${API_BASE}/wards/by-month?year=${year}&month=${month}`);
  currentWards = await res.json();
  activeMonth = { year, month, date };
  updateMonthBadge();
  renderMarkers(currentWards);
}

async function loadSummary() {
  const res = await fetch(`${API_BASE}/summary`);
  const s = await res.json();
  document.getElementById("stat-avg").textContent = s.avg_risk_score;
  document.getElementById("stat-max").textContent = s.max_risk_score;
  document.getElementById("stat-critical").textContent = s.critical_ward_count;
}

async function selectWard(wardId) {
  document.getElementById("detail-empty").style.display = "none";
  const content = document.getElementById("detail-content");
  content.style.display = "block";

  const [historyRes, predictRes] = await Promise.all([
    fetch(`${API_BASE}/wards/${wardId}/history`),
    fetch(`${API_BASE}/wards/${wardId}/predict`),
  ]);
  const history = await historyRes.json();
  const predict = await predictRes.json();

  // Show the record for the currently active month if one is selected, else latest
  const record = activeMonth
    ? history.find((h) => h.year === activeMonth.year && h.month === activeMonth.month) || history[history.length - 1]
    : history[history.length - 1];

  document.getElementById("d-name").textContent = record.ward_name;
  document.getElementById("d-zone").textContent = new Date(record.date).toLocaleDateString("en-IN", { month: "short", year: "numeric" });

  const badge = document.getElementById("d-risk-badge");
  document.getElementById("d-risk-score").textContent = record.risk_score;
  document.getElementById("d-risk-label").textContent = record.risk_label;
  badge.style.borderColor = RISK_COLORS[record.risk_label];
  badge.style.color = RISK_COLORS[record.risk_label];

  document.getElementById("d-forecast").textContent =
    `${predict.predicted_next_month_risk_score} (${predict.predicted_risk_label})`;
  document.getElementById("d-forecast").style.color = RISK_COLORS[predict.predicted_risk_label];

  document.getElementById("d-groundwater").textContent = `${record.groundwater_depth_m} m`;
  document.getElementById("d-tanker").textContent = `₹${record.tanker_price_inr}/kl`;
  document.getElementById("d-rainfall").textContent = `${record.rainfall_mm} mm`;

  renderChart(history, record.date);
}

function renderChart(history, highlightDate) {
  const ctx = document.getElementById("trend-chart").getContext("2d");
  const labels = history.map((h) => `${h.year}-${String(h.month).padStart(2, "0")}`);
  const scores = history.map((h) => h.risk_score);
  const pointColors = history.map((h) => (h.date === highlightDate ? "#ffffff" : "rgba(0,0,0,0)"));

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Risk score",
        data: scores,
        borderColor: "#d9a441",
        backgroundColor: "rgba(217, 164, 65, 0.15)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: pointColors,
        pointBorderColor: "#d9a441",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8fa0ac", maxTicksLimit: 6 }, grid: { color: "#2a3945" } },
        y: { ticks: { color: "#8fa0ac" }, grid: { color: "#2a3945" }, min: 0, max: 100 },
      },
    },
  });
}

async function loadScrubber() {
  const res = await fetch(`${API_BASE}/months/breakdown`);
  const monthly = await res.json();

  const labels = monthly.map((m) => `${m.year}-${String(m.month).padStart(2, "0")}`);
  const datasets = RISK_ORDER.map((label) => ({
    label,
    data: monthly.map((m) => m[label] || 0),
    backgroundColor: RISK_COLORS[label],
    stack: "risk",
  }));

  const ctx = document.getElementById("scrubber-chart").getContext("2d");
  scrubberChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      onClick: (evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const m = monthly[idx];
        loadWardsForMonth(m.year, m.month, m.date);
      },
      plugins: {
        legend: { labels: { color: "#8fa0ac", font: { family: "JetBrains Mono", size: 11 } } },
      },
      scales: {
        x: { stacked: true, ticks: { color: "#8fa0ac", maxTicksLimit: 12, font: { size: 10 } }, grid: { display: false } },
        y: { stacked: true, ticks: { color: "#8fa0ac" }, grid: { color: "#2a3945" } },
      },
    },
  });
}

function setupLegendFilters() {
  document.querySelectorAll(".legend-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const label = btn.dataset.label;
      if (activeCategory === label) {
        activeCategory = null;
        btn.classList.remove("active");
      } else {
        document.querySelectorAll(".legend-btn").forEach((b) => b.classList.remove("active"));
        activeCategory = label;
        btn.classList.add("active");
      }
      renderMarkers(currentWards);
    });
  });
}

document.getElementById("reset-month").addEventListener("click", () => {
  activeMonth = null;
  updateMonthBadge();
  loadWardsForLatest();
});

setupLegendFilters();
updateMonthBadge();
loadWardsForLatest();
loadSummary();
loadScrubber();
