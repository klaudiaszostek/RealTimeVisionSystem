document.addEventListener("DOMContentLoaded", async () => {
  const profileForm = document.getElementById("profile-form");
  const messageDiv = document.getElementById("message-div");
  const addBtn = document.getElementById("add-btn");
  const addSpinner = document.getElementById("add-spinner");

  try {
    const config = await window.api.invoke("load-form-config");
    if (config) {
      document.getElementById("form-title").textContent =
        config.formTitle || "Add New Person";
      document.getElementById("dynamic-field-label").textContent =
        config.dynamicFieldLabel || config.dynamic_field || "Apartment Number";
      const statusSelect = document.getElementById("status");
      statusSelect.innerHTML = "";
      (config.statusOptions || []).forEach((optionText) => {
        const option = document.createElement("option");
        option.value = optionText;
        option.textContent = optionText;
        statusSelect.appendChild(option);
      });
    }
  } catch (err) {
    console.error("Failed to load form configuration:", err);
  }

  profileForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const userData = {
      name: document.getElementById("name").value.trim(),
      surname: document.getElementById("surname").value.trim(),
      status: document.getElementById("status").value,
      dynamic_field: document.getElementById("dynamic_field").value.trim(),
    };

    const imageFile = document.getElementById("profile_image").files[0];
    if (!imageFile) {
      messageDiv.textContent = "Please select an image file.";
      messageDiv.className = "alert alert-danger";
      messageDiv.style.display = "block";
      return;
    }

    addBtn.disabled = true;
    addSpinner.classList.remove("d-none");
    messageDiv.style.display = "none";
    messageDiv.textContent = "";
    messageDiv.className = "";

    const reader = new FileReader();
    reader.onload = () => {
      const fileBuffer = reader.result;
      const fileName = imageFile.name;
      window.api.send("upload-profile", { userData, fileBuffer, fileName });
    };

    reader.onerror = () => {
      messageDiv.textContent = `Error reading file: ${reader.error}`;
      messageDiv.className = "alert alert-danger";
      messageDiv.style.display = "block";
      addBtn.disabled = false;
      addSpinner.classList.add("d-none");
    };

    reader.readAsArrayBuffer(imageFile);
  });

  window.api.receive("upload-result", (result) => {
    addBtn.disabled = false;
    addSpinner.classList.add("d-none");

    if (!result) return;

    const { success, message } = result;
    messageDiv.textContent =
      message || (success ? "Success!" : "Error occurred.");
    messageDiv.className = success
      ? "alert alert-success"
      : "alert alert-danger";
    messageDiv.style.display = "block";

    if (success) {
      profileForm.reset();
    }
  });
});
