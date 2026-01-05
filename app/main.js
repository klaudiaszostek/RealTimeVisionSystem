const { app, BrowserWindow, ipcMain, Menu, dialog } = require("electron");
const path = require("path");
const { PythonShell } = require("python-shell");
const fs = require("fs");
const os = require("os");

let loginWindow;
let homeWindow;
let dashboardWindow;
let cameraWindow;
let incidentsWindow;
let registerWindow;

let pyShell;
let currentUserRole = null;
let currentIsOffline = false;

// --- SETTINGS ---
const settingsPath = path.join(app.getAppPath(), "..", "settings.json");

function loadSettings() {
  try {
    if (fs.existsSync(settingsPath)) {
      return JSON.parse(fs.readFileSync(settingsPath, "utf8"));
    }
  } catch (e) {
    console.error("Error loading settings", e);
  }
  return { detect_weapons: true };
}

function saveSettings(settings) {
  try {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
  } catch (e) {
    console.error("Error saving settings", e);
  }
}

// --- WINDOW MANAGEMENT ---

function createLoginWindow() {
  if (loginWindow) return loginWindow.focus();
  loginWindow = new BrowserWindow({
    width: 400,
    height: 500,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  loginWindow.loadFile(path.join(__dirname, "views/login.html"));
  loginWindow.on("closed", () => (loginWindow = null));
}

function createHomeWindow() {
  if (homeWindow) return homeWindow.focus();
  homeWindow = new BrowserWindow({
    width: 600,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  homeWindow.loadFile(path.join(__dirname, "views/home.html"));
  homeWindow.webContents.on("did-finish-load", () => {
    homeWindow.webContents.send("init-home", {
      role: currentUserRole,
      isOffline: currentIsOffline,
    });
  });
  homeWindow.on("closed", () => {
    homeWindow = null;
    if (currentUserRole) app.quit();
  });
}

function createCameraWindow() {
  if (cameraWindow) return cameraWindow.focus();
  if (homeWindow) homeWindow.hide();
  cameraWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  cameraWindow.maximize();
  cameraWindow.show();
  cameraWindow.loadFile(path.join(__dirname, "views/camera_view.html"));

  cameraWindow.webContents.on("did-finish-load", () => {
    startPythonRecognition();

    const currentSettings = loadSettings();
    cameraWindow.webContents.send("init-camera", {
      role: currentUserRole,
      settings: currentSettings,
    });
  });

  cameraWindow.on("closed", () => {
    if (pyShell) {
      pyShell.kill();
      pyShell = null;
    }
    cameraWindow = null;
    if (homeWindow) homeWindow.show();
  });
}

function createDashboardWindow() {
  if (dashboardWindow) return dashboardWindow.focus();
  dashboardWindow = new BrowserWindow({
    width: 800,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  dashboardWindow.loadFile(path.join(__dirname, "views/dashboard.html"));
  dashboardWindow.on("closed", () => (dashboardWindow = null));
}

function createIncidentsWindow() {
  if (incidentsWindow) return incidentsWindow.focus();
  incidentsWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  incidentsWindow.loadFile(path.join(__dirname, "views/incidents.html"));
  incidentsWindow.on("closed", () => (incidentsWindow = null));
}

function createRegisterWindow() {
  if (registerWindow) return registerWindow.focus();
  registerWindow = new BrowserWindow({
    width: 400,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
    },
  });
  registerWindow.loadFile(path.join(__dirname, "views/register.html"));
  registerWindow.on("closed", () => (registerWindow = null));
}

function handleLogout() {
  currentUserRole = null;
  if (pyShell) {
    pyShell.kill();
    pyShell = null;
  }
  if (cameraWindow) cameraWindow.close();
  if (dashboardWindow) dashboardWindow.close();
  if (incidentsWindow) incidentsWindow.close();
  if (homeWindow) {
    homeWindow.removeAllListeners("closed");
    homeWindow.close();
    homeWindow = null;
  }
  createLoginWindow();
}

// ---------------------------------------------------------
// PYTHON & IPC
// ---------------------------------------------------------

function startPythonRecognition() {
  if (pyShell) return;
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");

  pyShell = new PythonShell("main_recognition.py", {
    mode: "json",
    pythonPath,
    scriptPath,
  });

  const currentSettings = loadSettings();
  pyShell.send({
    command: "set_weapon_detection",
    value: currentSettings.detect_weapons,
  });

  pyShell.on("message", (message) => {
    if (cameraWindow) cameraWindow.webContents.send("python-data", message);
  });
  pyShell.on("stderr", (stderr) => console.error(`${stderr}`));
  pyShell.on("close", () => (pyShell = null));
}

ipcMain.on("toggle-overlays-change", (event, shouldShow) => {
  if (pyShell) {
    pyShell.send({ command: "toggle_overlays", value: shouldShow });
  }
});

ipcMain.on("toggle-global-weapon-detection", (event, isEnabled) => {
  const settings = loadSettings();
  settings.detect_weapons = isEnabled;
  saveSettings(settings);

  if (pyShell) {
    pyShell.send({ command: "set_weapon_detection", value: isEnabled });
  }
  console.log("Global Weapon Detection set to:", isEnabled);
});

// IPC Handlers
ipcMain.on("open-camera", () => createCameraWindow());
ipcMain.on("open-dashboard", () => createDashboardWindow());
ipcMain.on("open-incidents", () => createIncidentsWindow());
ipcMain.on("logout-request", () => handleLogout());

ipcMain.on("login-attempt", (event, credentials) => {
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");

  PythonShell.run("authenticator.py", {
    mode: "json",
    pythonPath,
    scriptPath,
    args: [credentials.username, credentials.password],
  })
    .then((results) => {
      if (results && results[0] && results[0].status === "success") {
        currentUserRole = results[0].role;
        currentIsOffline = results[0].mode === "offline";
        if (loginWindow) loginWindow.close();
        createHomeWindow();
      } else {
        event.reply("login-fail", results[0]?.message || "Login failed");
      }
    })
    .catch((err) => event.reply("login-fail", err.toString()));
});

ipcMain.on("open-register-window", () => {
  if (loginWindow) loginWindow.close();
  createRegisterWindow();
});
ipcMain.on("open-login-window", () => {
  if (registerWindow) registerWindow.close();
  createLoginWindow();
});
ipcMain.on("register-attempt", (event, args) => {
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");
  PythonShell.run("register.py", {
    mode: "json",
    pythonPath,
    scriptPath,
    args: [args.username, args.password, args.adminCode],
  }).then((results) => event.reply("register-result", results[0]));
});

ipcMain.on("upload-profile", (event, { userData, fileBuffer, fileName }) => {
  let tempPath = "";
  try {
    const buffer = Buffer.from(fileBuffer);
    const fileExtension = path.extname(fileName);
    tempPath = path.join(os.tmpdir(), `temp_${Date.now()}${fileExtension}`);
    fs.writeFileSync(tempPath, buffer);
    const cleanTempPath = tempPath.replace(/\\/g, "/");
    const pythonPath = path.join(
      app.getAppPath(),
      "..",
      "venv",
      "Scripts",
      "python.exe"
    );
    const scriptPath = path.join(app.getAppPath(), "..", "python_backend");

    PythonShell.run("admin_uploader.py", {
      mode: "json",
      pythonPath,
      scriptPath,
      args: [JSON.stringify(userData), cleanTempPath],
    })
      .then((results) => {
        event.reply("upload-result", {
          success: results[0].status === "success",
          message: results[0].message,
        });
      })
      .catch((err) =>
        event.reply("upload-result", {
          success: false,
          message: err.toString(),
        })
      )
      .finally(() => {
        if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
      });
  } catch (err) {
    event.reply("upload-result", { success: false, message: err.message });
  }
});

ipcMain.on("get-incidents", (event) => {
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");
  PythonShell.run("incident_manager.py", {
    mode: "json",
    pythonPath,
    scriptPath,
    args: ["list"],
  }).then((r) => event.reply("incidents-data", r[0]));
});
ipcMain.on("update-incident-status", (event, args) => {
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");
  PythonShell.run("incident_manager.py", {
    mode: "json",
    pythonPath,
    scriptPath,
    args: ["update", args.id, args.status],
  }).then(() => event.reply("incident-updated"));
});
ipcMain.on("delete-incident", (event, args) => {
  const pythonPath = path.join(
    app.getAppPath(),
    "..",
    "venv",
    "Scripts",
    "python.exe"
  );
  const scriptPath = path.join(app.getAppPath(), "..", "python_backend");
  PythonShell.run("incident_manager.py", {
    mode: "json",
    pythonPath,
    scriptPath,
    args: ["delete", args.id],
  }).then(() => event.reply("incident-updated"));
});

ipcMain.handle("show-confirm-dialog", async (event, message) => {
  const result = await dialog.showMessageBox({
    type: "warning",
    buttons: ["Yes, delete", "Cancel"],
    defaultId: 1,
    title: "Confirmation",
    message: "Are you sure?",
    detail: message,
    noLink: true,
  });
  return result.response === 0;
});
ipcMain.handle("load-form-config", () => {
  try {
    return JSON.parse(
      fs.readFileSync(
        path.join(app.getAppPath(), "..", "form_config.json"),
        "utf8"
      )
    );
  } catch {
    return null;
  }
});

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createLoginWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createLoginWindow();
  });
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
