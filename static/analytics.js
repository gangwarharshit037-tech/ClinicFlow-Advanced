
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

  let appliedStartDate = "";
  let appliedEndDate = "";
  let requestSequence = 0;

  function setFilterError(message) {
    byId("analytics-filter-error").textContent = message;
  }

  function periodLabel(start, end) {
    if (start && end) return `${start} to ${end}`;
    if (start) return `From ${start}`;
    if (end) return `Through ${end}`;
    return "All time";
  }

  function clearAnalytics() {
    [
      "analytics-total-count",
      "analytics-active-count",
      "analytics-cancelled-count",
      "analytics-cancellation-rate",
      "analytics-doctor-count"
    ].forEach((id) => {
      byId(id).textContent = "--";
    });

    [
      "analytics-daily-chart",
      "analytics-doctor-chart",
      "analytics-time-chart"
    ].forEach((id) => {
      byId(id).replaceChildren();
    });
  }

  async function loadAnalytics() {
    const sequence = ++requestSequence;

    const startDate = appliedStartDate;
    const endDate = appliedEndDate;

    const params = new URLSearchParams();

    if (startDate) {
      params.set("start_date", startDate);
    }

    if (endDate) {
      params.set("end_date", endDate);
    }

    const query = params.toString();

    const endpoint = query
      ? `/api/admin/analytics?${query}`
      : "/api/admin/analytics";

    const period = periodLabel(startDate, endDate);

    byId("analytics-period").textContent =
      `Selected period: ${period}`;

    clearAnalytics();

    setStatus("Loading appointment analytics...");

    try {
      const response = await fetch(endpoint, {
        credentials: "same-origin",
        cache: "no-store"
      });

      if (sequence !== requestSequence) return;

      if (!response.ok) {
        throw new Error(
          `Analytics API returned HTTP ${response.status}`
        );
      }

      const data = await response.json();

      if (sequence !== requestSequence) return;

      if (
        !data ||
        !data.summary ||
        !Array.isArray(data.doctors) ||
        !Array.isArray(data.daily) ||
        !Array.isArray(data.times)
      ) {
        throw new Error("Invalid analytics response");
      }

      const summary = data.summary;

      byId("analytics-total-count").textContent =
        String(Number(summary.total) || 0);

      byId("analytics-active-count").textContent =
        String(Number(summary.active) || 0);

      byId("analytics-cancelled-count").textContent =
        String(Number(summary.cancelled) || 0);

      const rate = Number(summary.cancellation_rate);

      byId("analytics-cancellation-rate").textContent =
        `${Number.isFinite(rate) ? rate.toFixed(1) : "0.0"}%`;

      byId("analytics-doctor-count").textContent =
        String(data.doctors.length);

      renderChart(
        "analytics-daily-chart",
        data.daily.slice(-12),
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
        `Analytics updated. ${Number(summary.total) || 0} appointments analyzed.`
      );

    } catch (error) {
      if (sequence !== requestSequence) return;

      clearAnalytics();

      console.error("ClinicFlow analytics:", error);

      setStatus(
        "Unable to load analytics. Please apply the filters again."
      );
    }
  }

  function initializeAnalytics() {
    const form = byId("analytics-filter-form");
    const startInput = byId("analytics-start-date");
    const endInput = byId("analytics-end-date");
    const resetButton = byId("analytics-reset-button");

    form.addEventListener("submit", (event) => {
      event.preventDefault();

      const start = startInput.value;
      const end = endInput.value;

      if (start && end && start > end) {
        setFilterError(
          "Start date must not be after end date."
        );
        return;
      }

      setFilterError("");

      appliedStartDate = start;
      appliedEndDate = end;

      loadAnalytics();
    });

    resetButton.addEventListener("click", () => {
      startInput.value = "";
      endInput.value = "";

      appliedStartDate = "";
      appliedEndDate = "";

      setFilterError("");

      loadAnalytics();
    });

    startInput.addEventListener("input", () => {
      setFilterError("");
    });

    endInput.addEventListener("input", () => {
      setFilterError("");
    });

    loadAnalytics();
  }

  // Load analytics after the HTML and existing admin scripts are ready.
  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initializeAnalytics
    );
  } else {
    initializeAnalytics();
  }

  // Allow a future refresh button to call this function.
  window.loadAnalytics = loadAnalytics;
})();
