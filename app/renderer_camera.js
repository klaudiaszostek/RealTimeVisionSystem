document.addEventListener("DOMContentLoaded", () => {
  const cameraFeed = document.getElementById("camera-feed");
  const infoPanel = document.getElementById("info-panel");
  const body = document.body;
  const timerDisplay = document.getElementById("timer-display");
  const recordingStatusDisplay = document.getElementById(
    "recording-status-display"
  );
  const toggleOverlays = document.getElementById("toggle-overlays");

  const loadingSection = document.getElementById("system-loading");
  const adminSection = document.getElementById("admin-section");
  const userSection = document.getElementById("user-section");

  const globalWeaponToggle = document.getElementById("global-weapon-toggle");
  const adminToggleLabel = document.querySelector(
    'label[for="global-weapon-toggle"]'
  );
  const userWeaponStatus = document.getElementById("user-weapon-status");

  let savedRole = null;

  window.api.receive("init-camera", (data) => {
    savedRole = data.role;

    if (globalWeaponToggle) {
      globalWeaponToggle.checked = data.settings.detect_weapons;
    }
  });

  if (toggleOverlays) {
    toggleOverlays.addEventListener("change", (e) =>
      window.api.send("toggle-overlays-change", e.target.checked)
    );
  }

  if (globalWeaponToggle) {
    globalWeaponToggle.addEventListener("change", (e) => {
      updateAdminLabel(e.target.checked);
      window.api.send("toggle-global-weapon-detection", e.target.checked);
    });
  }

  function updateAdminLabel(isActive) {
    if (!adminToggleLabel) return;
    if (isActive) {
      adminToggleLabel.innerHTML =
        'AI Weapon Detection: <span class="text-success fw-bold">ACTIVE</span>';
    } else {
      adminToggleLabel.innerHTML =
        'AI Weapon Detection: <span class="text-danger fw-bold">DISABLED</span>';
    }
  }

  window.api.receive("python-data", (data) => {
    if (!data) return;

    if (loadingSection) loadingSection.classList.add("d-none");

    if (savedRole === "admin") {
      if (adminSection) adminSection.classList.remove("d-none");
    } else {
      if (userSection) userSection.classList.remove("d-none");
    }

    if (data.frame) {
      cameraFeed.src = "data:image/jpeg;base64," + data.frame;
    }

    body.className = data.theme || "theme-neutral";
    infoPanel.innerHTML = "";

    const isDetectionOn = data.weapon_detection_enabled;

    if (globalWeaponToggle) {
      updateAdminLabel(isDetectionOn);
      if (!globalWeaponToggle.matches(":focus")) {
        globalWeaponToggle.checked = isDetectionOn;
      }
    }

    if (userWeaponStatus) {
      if (isDetectionOn) {
        userWeaponStatus.className =
          "alert alert-success d-flex align-items-center py-2";
        userWeaponStatus.innerHTML =
          "✅ &nbsp; AI Weapon Detection:&nbsp; <strong>ACTIVE</strong>";
      } else {
        userWeaponStatus.className =
          "alert alert-warning d-flex align-items-center py-2";
        userWeaponStatus.innerHTML =
          "⚠️ &nbsp; AI Weapon Detection:&nbsp; <strong>DISABLED</strong>";
      }
    }

    if (data.threats && data.threats.length > 0) {
      data.threats.forEach((threat) => {
        const label = threat.label;
        const conf = threat.confidence
          ? Math.round(threat.confidence * 100)
          : 0;
        infoPanel.innerHTML += `
          <div class="card person-card bg-danger text-white mb-2 border-0 shadow">
            <div class="card-body text-center">
              <h4 class="card-title">⚠️ DANGER</h4>
              <h5 class="card-subtitle mb-2 text-warning">${label}</h5>
              <p class="card-text mb-0 small">Confidence: ${conf}%</p>
            </div>
          </div>`;
      });
    }

    if (data.results && data.results.length > 0) {
      data.results.forEach((person_tuple) => {
        const p = person_tuple[1];
        const status = p.status || "No data";
        let cardClass = "bg-light";

        if (
          status.includes("Denied") ||
          status.includes("Unknown") ||
          status.includes("No profile")
        ) {
          cardClass = "bg-danger-subtle text-danger-emphasis";
        } else if (status.includes("All") || status.includes("Full")) {
          cardClass = "bg-success-subtle text-success-emphasis";
        } else if (status.includes("Only first floor")) {
          cardClass = "bg-warning-subtle text-warning-emphasis";
        }

        infoPanel.innerHTML += `
          <div class="card person-card ${cardClass}">
            <div class="card-body">
              <h5 class="card-title">${p.name || ""} ${
          p.surname || "Unknown"
        }</h5>
              <p class="card-text mb-1"><strong>Status:</strong> ${status}</p>
              <p class="card-text mb-0"><strong>Apartment:</strong> ${
                p.dynamic_field || "N/A"
              }</p>
            </div>
          </div>`;
      });
    } else if (!data.threats || data.threats.length === 0) {
      if (data.weapon_detection_enabled === false) {
        infoPanel.innerHTML =
          '<div class="alert alert-warning text-center small">⚠️ Weapon Detection is <strong>DISABLED</strong> by Admin</div>';
      } else {
        infoPanel.innerHTML =
          '<p class="text-muted">No threats or persons detected.</p>';
      }
    }

    if (data.is_offline) {
      timerDisplay.style.display = "none";
    } else {
      timerDisplay.style.display = "block";
      if (data.timer !== undefined) {
        timerDisplay.textContent = `Next analysis in: ${data.timer.toFixed(
          1
        )} s`;
      }
    }

    if (data.is_recording) {
      recordingStatusDisplay.classList.add("active");
    } else {
      recordingStatusDisplay.classList.remove("active");
    }

    const offlineBanner = document.getElementById("offline-banner");
    if (offlineBanner) {
      offlineBanner.style.display = data.is_offline ? "block" : "none";
    }
  });
});
