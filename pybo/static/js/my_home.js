document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("myHomeStatus");

  /* =========================
     아바타 선택
  ========================= */

  document.querySelectorAll(".classroom-avatar").forEach((avatar) => {
    avatar.addEventListener("click", () => {
      document
        .querySelectorAll(".classroom-avatar")
        .forEach((item) => item.classList.remove("selected"));

      avatar.classList.add("selected");

      if (status) {
        status.textContent =
          `${avatar.dataset.avatarName}를 선택했습니다.`;
      }
    });
  });

  /* =========================
     교실 사진 확대
  ========================= */

  const classroomPhotoOpen =
    document.getElementById("classroomPhotoOpen");

  const classroomPhotoImage =
    document.querySelector(".classroom-background-image");

  let photoLightbox = null;
  let photoLightboxImage = null;
  let photoLightboxClose = null;

  function closePhotoLightbox() {
    if (!photoLightbox) {
      return;
    }

    photoLightbox.hidden = true;
    photoLightbox.setAttribute("aria-hidden", "true");

    document.body.classList.remove("photo-lightbox-open");

    if (classroomPhotoOpen) {
      classroomPhotoOpen.focus();
    }
  }

  function createPhotoLightbox() {
    const existingLightbox =
      document.getElementById("sharedPhotoLightbox");

    if (existingLightbox) {
      photoLightbox = existingLightbox;
      photoLightboxImage =
        photoLightbox.querySelector("img");
      photoLightboxClose =
        photoLightbox.querySelector(".photo-lightbox-close");

      return;
    }

    photoLightbox = document.createElement("div");
    photoLightbox.id = "sharedPhotoLightbox";
    photoLightbox.className = "photo-lightbox";
    photoLightbox.hidden = true;
    photoLightbox.setAttribute("aria-hidden", "true");

    photoLightbox.innerHTML = `
      <button
        type="button"
        class="photo-lightbox-close"
        aria-label="확대 사진 닫기"
      >
        ← 뒤로가기
      </button>

      <img
        src=""
        alt=""
      >
    `;

    document.body.appendChild(photoLightbox);

    photoLightboxImage =
      photoLightbox.querySelector("img");

    photoLightboxClose =
      photoLightbox.querySelector(".photo-lightbox-close");

    photoLightboxClose.addEventListener(
      "click",
      closePhotoLightbox,
    );

    photoLightbox.addEventListener("click", (event) => {
      if (event.target === photoLightbox) {
        closePhotoLightbox();
      }
    });

    photoLightboxImage.addEventListener(
      "click",
      (event) => {
        event.stopPropagation();
      },
    );
  }

  function openPhotoLightbox() {
    if (!classroomPhotoImage) {
      return;
    }

    createPhotoLightbox();

    photoLightboxImage.src =
      classroomPhotoImage.currentSrc
      || classroomPhotoImage.src;

    photoLightboxImage.alt =
      classroomPhotoImage.alt
      || "확대된 교실 사진";

    photoLightbox.hidden = false;
    photoLightbox.setAttribute("aria-hidden", "false");

    document.body.classList.add("photo-lightbox-open");

    photoLightboxClose.focus();
  }

  if (classroomPhotoOpen) {
    classroomPhotoOpen.addEventListener(
      "click",
      openPhotoLightbox,
    );
  }

  /* =========================
     아바타샵 모달
  ========================= */

  const shopModal =
    document.getElementById("avatarShopModal");

  const shopOpen =
    document.getElementById("avatarShopOpen");

  const shopClose =
    document.getElementById("avatarShopClose");

  const shopBackdrop =
    shopModal?.querySelector("[data-avatar-shop-close]");

  function closeAvatarShopModal() {
    if (!shopModal) {
      return;
    }

    shopModal.hidden = true;

    if (shopOpen) {
      shopOpen.focus();
    }
  }

  if (shopOpen && shopModal && shopClose) {
    shopOpen.addEventListener("click", () => {
      shopModal.hidden = false;
      shopClose.focus();
    });

    shopClose.addEventListener(
      "click",
      closeAvatarShopModal,
    );

    shopBackdrop?.addEventListener(
      "click",
      closeAvatarShopModal,
    );
  }

  /* =========================
     ESC 키 처리
  ========================= */

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }

    if (photoLightbox && !photoLightbox.hidden) {
      closePhotoLightbox();
      return;
    }

    if (shopModal && !shopModal.hidden) {
      closeAvatarShopModal();
    }
  });
});