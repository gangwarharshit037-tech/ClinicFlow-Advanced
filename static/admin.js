const csrf = JSON.parse(document.getElementById("csrf-data").textContent);
const $ = (id) => document.getElementById(id);
function td(tr, val) {
  let x = document.createElement("td");
  x.textContent = val ?? "";
  tr.append(x);
}
async function load() {
  let r = await fetch("/api/admin/appointments");
  if (!r.ok) {
    location.href = "/admin/login";
    return;
  }
  let rows = await r.json();

$("total-count").textContent = rows.length;
$("active-count").textContent = rows.filter(
    x => x.status === "Booked"
).length;
$("cancelled-count").textContent = rows.filter(
    x => x.status === "Cancelled"
).length;
  $("stats").textContent =
    `${rows.length} total • ${rows.filter((x) => x.status === "Booked").length} active • ${rows.filter((x) => x.status === "Cancelled").length} cancelled`;
  $("rows").replaceChildren();
  for (let a of rows) {
    let tr = document.createElement("tr");
    for (let key of [
      "id",
      "patient",
      "phone",
      "doctor",
      "date",
      "time",
      "status",
    ])
      td(tr, a[key]);
    let action = document.createElement("td");
    if (a.status === "Booked") {
      let b = document.createElement("button");
      b.textContent = "Cancel";
      b.onclick = () => cancel(a.id);
      action.append(b);
    }
    tr.append(action);
    $("rows").append(tr);
  }
  let logs = await (await fetch("/api/admin/deliveries")).json();

$("reminder-count").textContent = logs.length;

  $("deliveries").replaceChildren();
  for (let a of logs) {
    let tr = document.createElement("tr");
    for (let key of ["appointment_id", "channel", "status", "detail"])
      td(tr, a[key]);
    $("deliveries").append(tr);
  }
}
async function cancel(id) {
  if (!confirm("Cancel this appointment?")) return;
  let r = await fetch(`/api/admin/appointments/${id}/cancel`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
  });
  $("notice").textContent = r.ok
    ? "Appointment cancelled"
    : (await r.json()).error;
  load();
}
async function remind() {
  let r = await fetch("/api/admin/reminders/run", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
  });
  let j = await r.json();
  $("notice").textContent = r.ok
    ? `${j.results.length} due reminder(s) processed`
    : j.error || "Failed";
  load();
}
async function logout() {
  await fetch("/admin/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
  });
  location.href = "/admin/login";
}
load();

function searchAppointments() {
    const search = document.getElementById("appointment-search").value.toLowerCase().trim();

    const rows = document.querySelectorAll("#rows tr");

    rows.forEach(function(row) {
        const patient = row.cells[1]?.textContent.toLowerCase() || "";
        const phone = row.cells[2]?.textContent.toLowerCase() || "";
        const doctor = row.cells[3]?.textContent.toLowerCase() || "";

        if (patient.includes(search) ||
            phone.includes(search) ||
            doctor.includes(search)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}
function filterAppointments() {
    const status = document.getElementById("status-filter").value;
    const rows = document.querySelectorAll("#rows tr");

    rows.forEach(function(row) {
        const rowStatus = row.cells[6]?.textContent.trim();

        if (status === "All" || rowStatus === status) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}
function resetFilters() {
    document.getElementById("appointment-search").value = "";
    document.getElementById("status-filter").value = "All";

    document.querySelectorAll("#rows tr").forEach(function(row) {
        row.style.display = "";
    });
}

function exportAppointmentsCSV() {
    const table = document.querySelector("#rows")?.closest("table");

    if (!table) {
        alert("Appointment table not found.");
        return;
    }

    const lines = [];

    const headers = Array.from(
        table.querySelectorAll("thead th")
    ).slice(0, -1).map(th => th.textContent.trim());

    lines.push(headers);

    document.querySelectorAll("#rows tr").forEach(row => {
        if (row.style.display === "none") return;

        const cells = Array.from(row.querySelectorAll("td"))
            .slice(0, -1)
            .map(td => td.textContent.trim());

        if (cells.length) lines.push(cells);
    });

    const csv = lines.map(cells =>
        cells.map(value =>
            '"' + value.replace(/"/g, '""') + '"'
        ).join(",")
    ).join("\r\n");

    const blob = new Blob(["\uFEFF" + csv], {
        type: "text/csv;charset=utf-8;"
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "ClinicFlow_Appointments.csv";
    link.click();

    URL.revokeObjectURL(url);
}
