document.addEventListener("DOMContentLoaded", () => {
  const btnCamera = document.getElementById("btn-camera");
  const btnUsers = document.getElementById("btn-users");
  const btnIncidents = document.getElementById("btn-incidents");
  const btnLogout = document.getElementById("btn-logout");
  const statusText = document.getElementById("status-text");

  window.api.receive("init-home", ({ role, isOffline }) => {
    let statusMsg = `Logged in as: <strong>${role}</strong>`;

    if (isOffline) {
      statusMsg += ` <span class="badge bg-warning text-dark">OFFLINE MODE</span>`;
    } else {
      statusMsg += ` <span class="badge bg-success">ONLINE</span>`;
    }

    statusText.innerHTML = statusMsg;

    if (role === "admin" && !isOffline) {
      btnUsers.style.display = "flex";
      btnIncidents.style.display = "flex";
    } else {
      btnUsers.style.display = "none";
      btnIncidents.style.display = "none";
    }
  });

  btnCamera.addEventListener("click", () => {
    window.api.send("open-camera");
  });

  btnUsers.addEventListener("click", () => {
    window.api.send("open-dashboard");
  });

  btnIncidents.addEventListener("click", () => {
    window.api.send("open-incidents");
  });

  btnLogout.addEventListener("click", () => {
    window.api.send("logout-request");
  });
});
