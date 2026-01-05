document.addEventListener("DOMContentLoaded", () => {
  const registerForm = document.getElementById("register-form");
  const messageDiv = document.getElementById("message-div");
  const backButton = document.getElementById("back-to-login");

  registerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    messageDiv.style.display = "none";

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    let adminCode = document.getElementById("admin_code").value;

    if (!username || !password) {
      showMessage(false, "Username and password are required.");
      return;
    }

    if (adminCode.trim() === "") {
      adminCode = "none";
    }

    window.api.send("register-attempt", { username, password, adminCode });
  });

  backButton.addEventListener("click", () => {
    window.api.send("open-login-window");
  });

  window.api.receive("register-result", (result) => {
    const isSuccess = result.success === true || result.status === "success";
    showMessage(isSuccess, result.message);

    if (isSuccess) {
      registerForm.reset();
    }
  });

  function showMessage(success, message) {
    messageDiv.textContent = message;
    messageDiv.className = success
      ? "alert alert-success"
      : "alert alert-danger";
    messageDiv.style.display = "block";
  }
});
