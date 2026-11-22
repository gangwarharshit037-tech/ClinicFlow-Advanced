
"use strict";

(function () {
  const byId = (id) => document.getElementById(id);

  function setStatus(message) {
    const element = byId("analytics-loading-status");
    if (element) element.textContent = message;
  }

  function renderChart(elementId, items, labelKey, limit = 12) {
    const container = byId(elementId);
    if (!container) return;

    container.replaceChildren();

    if (!Array.isArray(items) || items.length === 0) {
      const empty = document.createElement("p");
      empty.className = "analytics-status";
      empty.textContent = "No appointment data available.";
      container.appendChild(empty);
      return;
    }

    const visible = items.slice(0, limit);

    const maximum = Math.max(
      1,
      ...visible.map((item) => Number(item.total) || 0)
    );

    visible.forEach((item) => {
      const count = Math.max(0, Number(item.total) || 0);
      const label = String(item[labelKey] ?? "Unknown");

      const row = document.createElement("div");
      row.style.display = "grid";
      row.style.gridTemplateColumns = "minmax(75px, 130px) 1fr 42px";
      row.style.alignItems = "center";
      row.style.gap = "10px";

      const name = document.createElement("span");
      name.textContent = label;
      name.style.fontSize = "13px";
      name.style.overflowWrap = "anywhere";

      const track = document.createElement("div");
      track.style.background = "#e2e8f0";
      track.style.height = "18px";
      track.style.borderRadius = "5px";
      track.style.overflow = "hidden";

      const bar = document.createElement("div");
      bar.style.height = "100%";
      bar.style.width = `${(count / maximum) * 100}%`;
      bar.style.background = "#0f766e";
      bar.style.borderRadius = "5px";

      track.appendChild(bar);

      const value = document.createElement("strong");
      value.textContent = String(count);
      value.style.fontSize = "13px";
      value.style.textAlign = "right";

      row.append(name, track, value);
      container.appendChild(row);
    });
  }

  async function loadAnalytics() {
    setStatus("Loading appointment analytics...");

    try {
      const response = await fetch("/api/admin/analytics", {
        credentials: "same-origin",
        cache: "no-store"
      });

      if (!response.ok) {
        throw new Error(`Analytics API returned HTTP ${response.status}`);
      }

      const data = await response.json();

      if (
        !data ||
        !data.summary ||
        !Array.isArray(data.doctors) ||
        !Array.isArray(data.daily) ||
        !Array.isArray(data.times)
      ) {
        throw new Error("Invalid analytics response");
      }

      const rate = Number(data.summary.cancellation_rate);

      byId("analytics-cancellation-rate").textContent =
        `${Number.isFinite(rate) ? rate.toFixed(1) : "0.0"}%`;

      byId("analytics-doctor-count").textContent =
        String(data.doctors.length);

      // Show the latest 12 appointment dates in chronological order.
      const recentDays = data.daily.slice(-12);

      renderChart(
        "analytics-daily-chart",
        recentDays,
        "date"
      );

      renderChart(
        "analytics-doctor-chart",
        data.doctors,
        "doctor",
        10
      );

      renderChart(
        "analytics-time-chart",
        data.times,
        "time",
        10
      );

      setStatus(
        `Analytics updated. ${Number(data.summary.total) || 0} appointments analyzed.`
      );

    } catch (error) {
      console.error("ClinicFlow analytics:", error);
      setStatus("Unable to load analytics. Please try refreshing.");
    }
  }

  // Load analytics after the HTML and existing admin scripts are ready.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadAnalytics);
  } else {
    loadAnalytics();
  }

  // Allow a future refresh button to call this function.
  window.loadAnalytics = loadAnalytics;
})();
