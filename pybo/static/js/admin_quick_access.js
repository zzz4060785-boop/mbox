(() => {
  const adminButton = document.getElementById("adminQuickAccessButton");
  adminButton?.addEventListener("click", () => {
    window.location.href = adminButton.dataset.url;
  });

  const avatarButton = document.getElementById("avatarQuickAccessButton");
  const modal = document.getElementById("avatarSelectorModal");
  if (!avatarButton || !modal) return;

  const status = document.getElementById("avatarSelectorStatus");
  const choices = [...modal.querySelectorAll("[data-avatar-value]")];

  const closeModal = () => {
    modal.hidden = true;
    document.body.classList.remove("friendary-modal-open");
  };

  avatarButton.addEventListener("click", () => {
    status.textContent = "";
    modal.hidden = false;
    document.body.classList.add("friendary-modal-open");
    choices[0]?.focus();
  });

  modal.querySelectorAll("[data-avatar-close]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  choices.forEach((choice) => {
    choice.addEventListener("click", async () => {
      choices.forEach((item) => (item.disabled = true));
      status.textContent = "아바타를 저장하는 중입니다...";
      try {
        const response = await fetch("/api/social/avatar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ avatar: choice.dataset.avatarValue }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "아바타를 저장하지 못했습니다.");
        choices.forEach((item) => item.classList.toggle("selected", item === choice));
        status.textContent = data.message;
      } catch (error) {
        status.textContent = error.message;
      } finally {
        choices.forEach((item) => (item.disabled = false));
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });
})();
