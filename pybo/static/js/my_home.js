document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("myHomeStatus");
  document.querySelectorAll(".classroom-avatar").forEach((avatar) => {
    avatar.addEventListener("click", () => {
      document
        .querySelectorAll(".classroom-avatar")
        .forEach((item) => item.classList.remove("selected"));
      avatar.classList.add("selected");
      status.textContent = `${avatar.dataset.avatarName}를 선택했습니다.`;
    });
  });

  const shopModal = document.getElementById("avatarShopModal");
  const shopOpen = document.getElementById("avatarShopOpen");
  const shopClose = document.getElementById("avatarShopClose");

  function closeAvatarShopModal() {
    shopModal.hidden = true;
    shopOpen.focus();
  }

  shopOpen.addEventListener("click", () => {
    shopModal.hidden = false;
    shopClose.focus();
  });
  shopClose.addEventListener("click", closeAvatarShopModal);
  shopModal
    .querySelector("[data-avatar-shop-close]")
    .addEventListener("click", closeAvatarShopModal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !shopModal.hidden) {
      closeAvatarShopModal();
    }
  });
});
