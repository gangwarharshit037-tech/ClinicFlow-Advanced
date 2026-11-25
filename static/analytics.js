
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

  async function loadAnalytics() {
    const sequence = ++requestSequence;

    const startDate = appliedStartDate;
    const endDate = appliedEndDate;
    const doctor = appliedDoctor;

    const params = new URLSearchParams();
    params.set("include_kpis", "1");

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
        `${Number.isFinite(rate) ? rate.toFixed(1) : "0.0"}%`;

      byId("analytics-doctor-count").textContent =
        String(data.doctors.length);

      renderDailyLineChart(data.daily, data.kpis);

      renderDoctorBarChart(data.doctors);

      renderTimeBarChart(data.times);

      renderStatusDoughnutChart(summary);

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
