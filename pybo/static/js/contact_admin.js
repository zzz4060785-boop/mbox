document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector(".contact-admin-page");
  const form = document.getElementById("contactAdminForm");
  const subject = document.getElementById("contactAdminSubject");
  const message = document.getElementById("contactAdminMessage");
  const status = document.getElementById("contactAdminStatus");
  const submitButton = form?.querySelector('button[type="submit"]');

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submitButton.disabled = true;
    status.className = "contact-admin-help sending";
    status.textContent = "이메일을 보내는 중입니다…";
    try {
      const response = await fetch("/api/contact-admin", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: subject.value.trim(),
          message: message.value.trim(),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message);
      status.className = "contact-admin-help success";
      status.textContent = `✅ ${data.message}`;
      form.reset();
    } catch (error) {
      status.className = "contact-admin-help error";
      status.textContent = `❌ ${error.message || "이메일 전송에 실패했습니다."}`;
    } finally {
      submitButton.disabled = false;
    }
  });
});
