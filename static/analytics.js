
"use strict";

(function () {
  const byId = (id) => document.getElementById(id);

  function setStatus(message) {
    const element = byId("analytics-loading-status");
    if (element) element.textContent = message;
  }


  // V2 Interactive Chart Management
  const chartInstances = new Map();

  function destroyChart(elementId) {
    const chart = chartInstances.get(elementId);

    if (chart) {
      chart.destroy();
      chartInstances.delete(elementId);
    }
  }

  function showEmptyChart(elementId) {
    destroyChart(elementId);

    const container = byId(elementId);
    container.replaceChildren();

    const message = document.createElement("p");
    message.className = "analytics-status";
    message.textContent = "No appointment data available.";

    container.appendChild(message);
  }

  function createInteractiveChart(elementId, config, description) {
    destroyChart(elementId);

    const container = byId(elementId);
    container.replaceChildren();

    const wrapper = document.createElement("div");
    wrapper.className = "analytics-canvas-wrapper";

    const canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", description);
    canvas.textContent = description;

    wrapper.appendChild(canvas);
    container.appendChild(wrapper);

    const chart = new window.Chart(canvas, config);
    chartInstances.set(elementId, chart);
  }

  function renderDailyLineChart(items, kpis) {
    const elementId = "analytics-daily-chart";

    if (!items.length) {
      showEmptyChart(elementId);
      return;
    }

    // Display up to the last 30 calendar days.
    const end = new Date(
      `${kpis.period_end || items[items.length - 1].date}T00:00:00Z`
    );

    const start = new Date(
      `${kpis.period_start || items[0].date}T00:00:00Z`
    );

    const dayMs = 86400000;

    const first = Math.max(
      start.getTime(),
      end.getTime() - 29 * dayMs
    );

    const counts = new Map(
      items.map((item) => [
        item.date,
        Number(item.total) || 0
      ])
    );

    const labels = [];
    const values = [];

    for (
      let day = first;
      day <= end.getTime();
      day += dayMs
    ) {
      const label = new Date(day).toISOString().slice(0, 10);

      labels.push(label);
      values.push(counts.get(label) || 0);
    }

    const description = labels.map(
      (label, index) => `${label}: ${values[index]} appointments`
    ).join("; ");

    createInteractiveChart(elementId, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Appointments",
          data: values,
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.12)",
          borderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 7,
          tension: 0,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: true
          }
        },
        scales: {
          x: {
            ticks: {
              maxTicksLimit: 7
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          }
        }
      }
    }, description);

    const note = document.createElement("p");
    note.className = "analytics-status";
    note.textContent =
      `Showing ${labels[0]} to ${labels[labels.length - 1]} (maximum 30 calendar days).`;

    byId(elementId).appendChild(note);
  }


  function renderDoctorBarChart(items) {
    const elementId = "analytics-doctor-chart";

    if (!items.length) {
      showEmptyChart(elementId);
      return;
    }

    const visible = items.slice(0, 10);

    const labels = visible.map(
      (item) => String(item.doctor)
    );

    const values = visible.map(
      (item) => Number(item.total) || 0
    );

    const description = labels.map(
      (label, index) => `${label}: ${values[index]} appointments`
    ).join("; ");

    createInteractiveChart(elementId, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Appointments",
          data: values,
          backgroundColor: "#0f766e",
          hoverBackgroundColor: "#115e59",
          borderRadius: 5,
          maxBarThickness: 32
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: true
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          },
          y: {
            ticks: {
              autoSkip: false,
              callback: function(value) {
                const label = this.getLabelForValue(value);
                return label.split(" - ");
              }
            }
          }
        }
      }
    }, description);

    const note = document.createElement("p");
    note.className = "analytics-status";
    note.textContent =
      `Showing ${visible.length} of ${items.length} doctors, ranked by appointment volume.`;

    byId(elementId).appendChild(note);
  }

  function renderTimeBarChart(items) {
    const elementId = "analytics-time-chart";

    if (!items.length) {
      showEmptyChart(elementId);
      return;
    }

    const visible = items.slice(0, 10);

    const labels = visible.map(
      (item) => String(item.time)
    );

    const values = visible.map(
      (item) => Number(item.total) || 0
    );

    const description = labels.map(
      (label, index) => `${label}: ${values[index]} appointments`
    ).join("; ");

    createInteractiveChart(elementId, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Appointments",
          data: values,
          backgroundColor: "#2563eb",
          hoverBackgroundColor: "#1d4ed8",
          borderRadius: 5,
          maxBarThickness: 40
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: true
          }
        },
        scales: {
          x: {
            ticks: {
              maxRotation: 45,
              minRotation: 0
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          }
        }
      }
    }, description);

    const note = document.createElement("p");
    note.className = "analytics-status";
    note.textContent =
      `Showing ${visible.length} of ${items.length} time slots, ranked by appointment volume.`;

    byId(elementId).appendChild(note);
  }


  function renderStatusDoughnutChart(summary) {
    const elementId = "analytics-status-chart";

    const total = Number(summary.total);
    const active = Number(summary.active);
    const cancelled = Number(summary.cancelled);

    if (
      ![total, active, cancelled].every(
        (value) => Number.isInteger(value) && value >= 0
      ) ||
      active + cancelled > total
    ) {
      throw new Error("Invalid appointment status counts");
    }

    if (total === 0) {
      showEmptyChart(elementId);
      return;
    }

    const labels = ["Active", "Cancelled"];
    const values = [active, cancelled];
    const colors = ["#0f766e", "#dc6262"];

    const other = total - active - cancelled;

    if (other > 0) {
      labels.push("Other");
      values.push(other);
      colors.push("#64748b");
    }

    const description = labels.map(
      (label, index) =>
        `${label}: ${values[index]} appointments`
    ).join("; ");

    createInteractiveChart(elementId, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderColor: "#ffffff",
          borderWidth: 3,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        cutout: "68%",
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            onClick: () => {},
            labels: {
              padding: 16,
              usePointStyle: true
            }
          },
          tooltip: {
            enabled: true,
            callbacks: {
              label: function(context) {
                const count = Number(context.raw);
                const percentage = (count / total * 100).toFixed(1);

                return `${context.label}: ${count} (${percentage}%)`;
              }
            }
          }
        }
      }
    }, description);

    const note = document.createElement("p");
    note.className = "analytics-status";

    note.textContent = labels.map(
      (label, index) => {
        const percentage =
          (values[index] / total * 100).toFixed(1);

        return `${label}: ${values[index]} (${percentage}%)`;
      }
    ).join(" | ");

    byId(elementId).appendChild(note);
  }

  let appliedStartDate = "";
  let appliedEndDate = "";
  let appliedDoctor = "";
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
      "analytics-doctor-count",
      "analytics-active-rate",
      "analytics-average-daily",
      "analytics-reporting-days",
      "analytics-busiest-day",
      "analytics-busiest-detail",
      "analytics-peak-time",
      "analytics-peak-detail",
      "analytics-top-doctor",
      "analytics-doctor-detail",
      "analytics-reporting-period"
    ].forEach((id) => {
      byId(id).textContent = "--";
    });

    [
      "analytics-daily-chart",
      "analytics-doctor-chart",
      "analytics-time-chart",
      "analytics-status-chart"
    ].forEach((id) => {
      destroyChart(id);
      byId(id).replaceChildren();
    });
  }

  function renderTopKpi(metric, valueId, detailId) {
    if (!metric || !Array.isArray(metric.ties)) {
      throw new Error("Invalid top KPI response");
    }

    const valueElement = byId(valueId);
    const detailElement = byId(detailId);

    if (metric.value === null) {
      valueElement.textContent = "N/A";
      detailElement.textContent = "No matching appointments";
      return;
    }

    valueElement.textContent = String(metric.value);

    const count = Number(metric.total);
    const label = count === 1 ? "appointment" : "appointments";

    let detail = `${count} ${label}`;

    if (metric.ties.length > 1) {
      detail += ` | ${metric.ties.length}-way tie: `;
      detail += metric.ties.join(", ");
    }

    detailElement.textContent = detail;
  }

  function renderAdvancedKpis(kpis, total) {
    const activeRate = Number(kpis.active_booking_rate);
    const average = Number(kpis.average_daily_appointments);
    const days = Number(kpis.reporting_days);

    if (
      !Number.isFinite(activeRate) ||
      !Number.isFinite(average) ||
      !Number.isInteger(days) ||
      days < 0
    ) {
      throw new Error("Invalid advanced KPI values");
    }

    byId("analytics-active-rate").textContent =
      total > 0 ? `${activeRate.toFixed(1)}%` : "N/A";

    byId("analytics-average-daily").textContent =
      days > 0 ? average.toFixed(2) : "N/A";

    byId("analytics-reporting-days").textContent =
      days > 0
        ? `Over ${days} calendar ${days === 1 ? "day" : "days"}`
        : "Reporting duration unavailable";

    byId("analytics-reporting-period").textContent =
      kpis.period_start && kpis.period_end
        ? `Reporting period: ${kpis.period_start} to ${kpis.period_end} (${days} ${days === 1 ? "day" : "days"})`
        : "Reporting period: Insufficient date information";

    renderTopKpi(
      kpis.busiest_day,
      "analytics-busiest-day",
      "analytics-busiest-detail"
    );

    renderTopKpi(
      kpis.peak_appointment_time,
      "analytics-peak-time",
      "analytics-peak-detail"
    );

    renderTopKpi(
      kpis.most_booked_doctor,
      "analytics-top-doctor",
      "analytics-doctor-detail"
    );
  }


  // V2 Period Comparison

  function clearComparison(message) {
    destroyChart("analytics-comparison-chart");
    byId("analytics-comparison-chart").replaceChildren();

    byId("comparison-content").hidden = true;
    byId("comparison-message").textContent = message;

    const keys = [
      "total",
      "active",
      "cancelled",
      "active-rate",
      "cancellation-rate",
      "average-daily"
    ];

    for (const key of keys) {
      byId(`comparison-${key}-current`).textContent = "--";
      byId(`comparison-${key}-previous`).textContent = "--";

      const change = byId(`comparison-${key}-change`);
      change.textContent = "--";
      change.dataset.direction = "neutral";
    }

    byId("comparison-current-period").textContent = "--";
    byId("comparison-previous-period").textContent = "--";
    byId("comparison-reporting-days").textContent = "--";
  }

  function formatComparisonValue(value, type) {
    if (value === null) return "N/A";

    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error("Invalid comparison metric");
    }

    if (type === "rate") {
      return `${value.toFixed(2)}%`;
    }

    if (type === "average") {
      return value.toFixed(2);
    }

    return String(value);
  }

  function renderComparisonCard(
    key,
    current,
    previous,
    change,
    valueType,
    changeType
  ) {
    byId(`comparison-${key}-current`).textContent =
      formatComparisonValue(current, valueType);

    byId(`comparison-${key}-previous`).textContent =
      formatComparisonValue(previous, valueType);

    const element = byId(`comparison-${key}-change`);

    element.dataset.direction = "neutral";

    if (change === null) {
      element.textContent = "N/A";
      return;
    }

    if (typeof change !== "number" || !Number.isFinite(change)) {
      throw new Error("Invalid comparison change");
    }

    if (change === 0) {
      element.textContent = "No change";
      return;
    }

    const increase = change > 0;
    const direction = increase ? "Increase" : "Decrease";
    const magnitude = Math.abs(change);

    element.dataset.direction =
      increase ? "increase" : "decrease";

    if (changeType === "percent") {
      element.textContent =
        `${direction}: ${magnitude.toFixed(2)}%`;

    } else if (changeType === "points") {
      element.textContent =
        `${direction}: ${magnitude.toFixed(2)} pp`;

    } else {
      const unit =
        magnitude === 1 ? "appointment" : "appointments";

      element.textContent =
        `${direction}: ${magnitude} ${unit}`;
    }
  }


  function renderComparisonChart(current, previous) {
    const elementId = "analytics-comparison-chart";

    if (current.total === 0 && previous.total === 0) {
      showEmptyChart(elementId);
      return;
    }

    const labels = [
      "Total",
      "Active",
      "Cancelled"
    ];

    const previousValues = [
      previous.total,
      previous.active,
      previous.cancelled
    ];

    const currentValues = [
      current.total,
      current.active,
      current.cancelled
    ];

    const description = labels.map(
      (label, index) =>
        `${label}: previous ${previousValues[index]}, current ${currentValues[index]}`
    ).join("; ");

    createInteractiveChart(elementId, {
      type: "bar",

      data: {
        labels: labels,

        datasets: [
          {
            label: "Previous Period",
            data: previousValues,
            backgroundColor: "#94a3b8",
            hoverBackgroundColor: "#64748b",
            borderRadius: 5,
            maxBarThickness: 48
          },
          {
            label: "Current Period",
            data: currentValues,
            backgroundColor: "#0f766e",
            hoverBackgroundColor: "#115e59",
            borderRadius: 5,
            maxBarThickness: 48
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,

        interaction: {
          mode: "index",
          intersect: false
        },

        plugins: {
          legend: {
            display: true,
            position: "bottom"
          },

          tooltip: {
            enabled: true
          }
        },

        scales: {
          y: {
            beginAtZero: true,

            ticks: {
              precision: 0
            }
          }
        }
      }
    }, description);
  }

  function renderPeriodComparison(comparison, doctor) {
    if (!comparison || typeof comparison.available !== "boolean") {
      throw new Error("Invalid period comparison response");
    }

    if (!comparison.available) {
      clearComparison(
        comparison.reason ||
        "Select both start and end dates to compare periods."
      );
      return;
    }

    const current = comparison.current;
    const previous = comparison.previous;
    const changes = comparison.changes;
    const days = comparison.reporting_days;

    if (
      !current ||
      !previous ||
      !changes ||
      !Number.isInteger(days) ||
      days < 1
    ) {
      throw new Error("Invalid period comparison data");
    }

    byId("comparison-current-period").textContent =
      `${current.start_date} to ${current.end_date}`;

    byId("comparison-previous-period").textContent =
      `${previous.start_date} to ${previous.end_date}`;

    byId("comparison-reporting-days").textContent =
      `${days} calendar ${days === 1 ? "day" : "days"} per period | Doctor: ${doctor || "All Doctors"}`;

    renderComparisonCard(
      "total",
      current.total,
      previous.total,
      changes.total_growth_percentage,
      "count",
      "percent"
    );

    renderComparisonCard(
      "active",
      current.active,
      previous.active,
      changes.active_difference,
      "count",
      "count"
    );

    renderComparisonCard(
      "cancelled",
      current.cancelled,
      previous.cancelled,
      changes.cancelled_difference,
      "count",
      "count"
    );

    renderComparisonCard(
      "active-rate",
      current.active_booking_rate,
      previous.active_booking_rate,
      changes.active_rate_percentage_points,
      "rate",
      "points"
    );

    renderComparisonCard(
      "cancellation-rate",
      current.cancellation_rate,
      previous.cancellation_rate,
      changes.cancellation_rate_percentage_points,
      "rate",
      "points"
    );

    renderComparisonCard(
      "average-daily",
      current.average_daily_appointments,
      previous.average_daily_appointments,
      changes.average_daily_growth_percentage,
      "average",
      "percent"
    );

    byId("comparison-message").textContent =
      "Comparing the selected period with the immediately preceding period.";

    byId("comparison-content").hidden = false;

    renderComparisonChart(current, previous);
  }

  async function loadAnalytics() {
    const sequence = ++requestSequence;

    const startDate = appliedStartDate;
    const endDate = appliedEndDate;
    const doctor = appliedDoctor;

    const params = new URLSearchParams();
    params.set("include_kpis", "1");
    params.set("include_comparison", "1");

    if (startDate) {
      params.set("start_date", startDate);
    }

    if (endDate) {
      params.set("end_date", endDate);
    }

    if (doctor) {
      params.set("doctor", doctor);
    }

    const query = params.toString();

    const endpoint = query
      ? `/api/admin/analytics?${query}`
      : "/api/admin/analytics";

    const period = periodLabel(startDate, endDate);

    byId("analytics-period").textContent =
      `Selected period: ${period} | Doctor: ${doctor || "All Doctors"}`;

    clearAnalytics();
    clearComparison("Loading period comparison...");

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
        !data.kpis ||
        !Array.isArray(data.doctors) ||
        !Array.isArray(data.daily) ||
        !Array.isArray(data.times)
      ) {
        throw new Error("Invalid analytics response");
      }

      const summary = data.summary;

      renderAdvancedKpis(
        data.kpis,
        Number(summary.total)
      );

      byId("analytics-total-count").textContent =
        String(Number(summary.total) || 0);

      byId("analytics-active-count").textContent =
        String(Number(summary.active) || 0);

      byId("analytics-cancelled-count").textContent =
        String(Number(summary.cancelled) || 0);

      const rate = Number(summary.cancellation_rate);

      byId("analytics-cancellation-rate").textContent =
        Number(summary.total) > 0 &&
        summary.cancellation_rate != null &&
        Number.isFinite(rate)
          ? `${rate.toFixed(1)}%`
          : "N/A";

      byId("analytics-doctor-count").textContent =
        String(data.doctors.length);

      renderDailyLineChart(data.daily, data.kpis);

      renderDoctorBarChart(data.doctors);

      renderTimeBarChart(data.times);

      renderStatusDoughnutChart(summary);

      renderPeriodComparison(data.comparison, doctor);

      setStatus(
        `Analytics updated. ${Number(summary.total) || 0} appointments analyzed.`
      );

    } catch (error) {
      if (sequence !== requestSequence) return;

      clearAnalytics();
      clearComparison("Unable to load period comparison.");

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
    const doctorInput = byId("analytics-doctor");
    const resetButton = byId("analytics-reset-button");

    form.addEventListener("submit", (event) => {
      event.preventDefault();

      const start = startInput.value;
      const end = endInput.value;
      const doctor = doctorInput.value;

      if (start && end && start > end) {
        setFilterError(
          "Start date must not be after end date."
        );
        return;
      }

      setFilterError("");

      appliedStartDate = start;
      appliedEndDate = end;
      appliedDoctor = doctor;

      loadAnalytics();
    });

    resetButton.addEventListener("click", () => {
      startInput.value = "";
      endInput.value = "";
      doctorInput.value = "";

      appliedStartDate = "";
      appliedEndDate = "";
      appliedDoctor = "";

      setFilterError("");

      loadAnalytics();
    });

    startInput.addEventListener("input", () => {
      setFilterError("");
    });

    doctorInput.addEventListener("change", () => {
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
