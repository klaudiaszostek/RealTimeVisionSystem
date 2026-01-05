document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const errorDiv = document.getElementById("error-message");
  const registerButton = document.getElementById("go-to-register");
  const loginBtn = document.getElementById("login-btn");
  const loginSpinner = document.getElementById("login-spinner");

  function updateOnlineStatus() {
    if (navigator.onLine) {
      registerButton.disabled = false;
      registerButton.textContent = "Register New Account";
      registerButton.classList.remove("btn-secondary");
      registerButton.classList.add("btn-outline-secondary");
      registerButton.title = "";
    } else {
      registerButton.disabled = true;
      registerButton.textContent = "Register (Offline - Unavailable)";
      registerButton.classList.remove("btn-outline-secondary");
      registerButton.classList.add("btn-secondary");
      registerButton.title =
        "An internet connection is required to create a new account.";
    }
  }

  updateOnlineStatus();
  window.addEventListener("online", updateOnlineStatus);
  window.addEventListener("offline", updateOnlineStatus);

  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    loginBtn.disabled = true;
    loginSpinner.classList.remove("d-none");

    if (loginBtn.childNodes[2]) {
      loginBtn.childNodes[2].textContent = " Logging in...";
    }

    errorDiv.style.display = "none";

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    window.api.send("login-attempt", { username, password });
  });

  window.api.receive("login-fail", (message) => {
    loginBtn.disabled = false;
    loginSpinner.classList.add("d-none");

    if (loginBtn.childNodes[2]) {
      loginBtn.childNodes[2].textContent = " Login";
    }

    errorDiv.textContent = message;
    errorDiv.style.display = "block";
  });

  registerButton.addEventListener("click", () => {
    if (navigator.onLine) {
      window.api.send("open-register-window");
    }
  });
});
