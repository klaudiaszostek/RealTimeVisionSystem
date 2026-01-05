let currentIncidentId = null;

const statusMap = {
  New: { badgeClass: "bg-danger", badgeText: "CHECK" },
  Confirmed: { badgeClass: "bg-dark", badgeText: "CONFIRMED THREAT" },
  FalseAlarm: { badgeClass: "bg-secondary", badgeText: "False Alarm" },
  Resolved: { badgeClass: "bg-success", badgeText: "Resolved" },
};

document.addEventListener("DOMContentLoaded", () => {
  const listContainer = document.getElementById("list-column");
  const refreshBtn = document.getElementById("refresh-btn");

  loadIncidents();

  refreshBtn.addEventListener("click", loadIncidents);

  window.api.receive("incidents-data", (response) => {
    listContainer.innerHTML = "";

    if (response.status === "error") {
      listContainer.innerHTML = `<div class="p-3 text-danger">Error: ${response.message}</div>`;
      return;
    }

    if (response.data.length === 0) {
      listContainer.innerHTML = `<div class="p-3 text-center">No incidents found.</div>`;
      return;
    }

    response.data.forEach((incident) => {
      const item = document.createElement("div");
      item.className = "list-group-item incident-item";

      const statusConfig = statusMap[incident.status] || {
        badgeClass: "bg-secondary",
        badgeText: incident.status,
      };

      item.innerHTML = `
        <div class="d-flex w-100 justify-content-between">
          <small>${new Date(incident.timestamp).toLocaleString()}</small>
          <span class="badge ${statusConfig.badgeClass}">${
        statusConfig.badgeText
      }</span>
        </div>
        <p class="mb-1 small text-truncate">${incident.id}</p>
      `;

      item.addEventListener("click", () => {
        document
          .querySelectorAll(".incident-item")
          .forEach((el) => el.classList.remove("active"));
        item.classList.add("active");
        playIncident(incident);
      });

      listContainer.appendChild(item);
    });
  });

  window.api.receive("incident-updated", () => {
    loadIncidents();
  });
});

function loadIncidents() {
  const listContainer = document.getElementById("list-column");
  listContainer.innerHTML = `
    <div class="d-flex justify-content-center p-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
  `;
  window.api.send("get-incidents");
}

function playIncident(incident) {
  currentIncidentId = incident.id;
  document.getElementById("video-placeholder").style.display = "none";
  const container = document.getElementById("video-container");
  container.style.display = "block";

  document.getElementById("incident-id-display").textContent = incident.id;

  const player = document.getElementById("player");
  player.src = incident.videoUrl;
  player.play();
}

window.setStatus = async (status) => {
  if (!currentIncidentId) return;

  if (status === "FalseAlarm") {
    const userConfirmed = await window.api.invoke(
      "show-confirm-dialog",
      "This will permanently delete the video and incident records."
    );

    if (userConfirmed) {
      window.api.send("delete-incident", { id: currentIncidentId });
      document.getElementById("video-container").style.display = "none";
      document.getElementById("video-placeholder").style.display = "block";
      currentIncidentId = null;
    }
  } else {
    window.api.send("update-incident-status", {
      id: currentIncidentId,
      status: status,
    });
  }
};
