function renderWhatsAppReviewQueue(events) {
    const tbody = document.getElementById("wa-review-queue");
    const empty = document.getElementById("wa-review-empty");

    if (!tbody || !empty) {
        throw new Error("Manual review table is missing");
    }

    const validStatuses = ["sent", "delivered", "read", "failed"];

    // Validate the complete response before creating table rows.
    if (
        !Array.isArray(events) ||
        !events.every(event =>
            event !== null &&
            typeof event === "object" &&
            Number.isSafeInteger(event.event_id) &&
            event.event_id > 0 &&
            validStatuses.includes(event.meta_status)
        )
    ) {
        tbody.replaceChildren();
        empty.textContent = "Review queue data unavailable.";
        throw new Error("Invalid review queue response");
    }

    if (events.length === 0) {
        tbody.replaceChildren();
        empty.textContent =
            "No WhatsApp events require manual review.";
        return;
    }

    // Build rows off-screen, then replace the table contents once.
    const fragment = document.createDocumentFragment();

    for (const event of events) {
        const row = document.createElement("tr");
        const idCell = document.createElement("td");
        const statusCell = document.createElement("td");

        idCell.textContent = String(event.event_id);
        statusCell.textContent = event.meta_status;

        row.appendChild(idCell);
        row.appendChild(statusCell);
        fragment.appendChild(row);
    }

    tbody.replaceChildren(fragment);
    empty.textContent = "";
}


async function loadWhatsAppMonitoring() {
    const status = document.getElementById("wa-monitoring-status");
    const button = document.getElementById("wa-refresh-button");

    if (button && button.disabled) {
        return;
    }

    if (button) {
        button.disabled = true;
        button.textContent = "Refreshing...";
    }

    try {
        const response = await fetch(
            "/api/admin/whatsapp/monitoring",
            {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error("Monitoring request failed: " + response.status);
        }

        const data = await response.json();

        if (!data.ok || !data.summary) {
            throw new Error("Invalid monitoring response");
        }

        const summary = data.summary;

        document.getElementById("wa-total").textContent = summary.total;
        document.getElementById("wa-pending").textContent = summary.pending;
        document.getElementById("wa-completed").textContent = summary.completed;
        document.getElementById("wa-review").textContent = summary.review_required;

        renderWhatsAppReviewQueue(data.review_queue);

        status.textContent = "Monitoring data loaded successfully.";
    } catch (error) {
        console.error("WhatsApp monitoring:", error);

        // Clear potentially outdated monitoring values.
        for (const id of [
            "wa-total",
            "wa-pending",
            "wa-completed",
            "wa-review"
        ]) {
            document.getElementById(id).textContent = "--";
        }

        // Clear outdated manual review entries after an API failure.
        const queueBody = document.getElementById("wa-review-queue");
        const queueEmpty = document.getElementById("wa-review-empty");

        if (queueBody) {
            queueBody.replaceChildren();
        }

        if (queueEmpty) {
            queueEmpty.textContent = "Review queue unavailable.";
        }

        status.textContent = "Unable to load WhatsApp monitoring data.";
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Refresh Monitoring";
        }
    }
}

document.addEventListener("DOMContentLoaded", loadWhatsAppMonitoring);
