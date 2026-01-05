const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  send: (channel, data) => {
    const validChannels = [
      "delete-incident",
      "get-incidents",
      "login-attempt",
      "logout-request",
      "open-camera",
      "open-dashboard",
      "open-incidents",
      "open-login-window",
      "open-register-window",
      "register-attempt",
      "save-form-config",
      "toggle-global-weapon-detection",
      "toggle-overlays-change",
      "update-incident-status",
      "upload-profile",
    ];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },

  receive: (channel, func) => {
    const validChannels = [
      "incident-updated",
      "incidents-data",
      "init-camera",
      "init-home",
      "login-fail",
      "login-success",
      "python-data",
      "register-result",
      "save-form-config-fail",
      "save-form-config-success",
      "upload-result",
    ];
    if (validChannels.includes(channel)) {
      ipcRenderer.removeAllListeners(channel);
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    }
  },

  invoke: (channel, ...args) => {
    const validChannels = ["load-form-config", "show-confirm-dialog"];
    if (validChannels.includes(channel)) {
      return ipcRenderer.invoke(channel, ...args);
    }
  },
});
