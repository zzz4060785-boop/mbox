(() => {
  let opener = null;

  function closePhotoLightbox() {
    const lightbox = document.getElementById("sharedPhotoLightbox");
    if (!lightbox) return;
    lightbox.hidden = true;
    lightbox.style.display = "none";
    const img = lightbox.querySelector("img");
    if (img) img.removeAttribute("src");
    document.body.classList.remove("photo-lightbox-open");
    opener?.focus();
  }

  function openPhotoLightbox(sourceImage) {
    let lightbox = document.getElementById("sharedPhotoLightbox");
    if (!lightbox) {
      lightbox = document.createElement("div");
      lightbox.id = "sharedPhotoLightbox";
      lightbox.className = "photo-lightbox";
      lightbox.hidden = true;
      lightbox.setAttribute("role", "dialog");
      lightbox.setAttribute("aria-modal", "true");
      lightbox.setAttribute("aria-label", "사진 확대 보기");
      lightbox.innerHTML = `
        <button type="button" class="photo-lightbox-close" aria-label="닫기">&times;</button>
        <img alt="확대된 사진">
      `;
      lightbox.addEventListener("click", (event) => {
        if (
          event.target === lightbox ||
          event.target.closest(".photo-lightbox-close")
        ) {
          closePhotoLightbox();
        }
      });
      document.body.appendChild(lightbox);
    }

    const enlargedImage = lightbox.querySelector("img");
    enlargedImage.src = sourceImage.currentSrc || sourceImage.src;
    enlargedImage.alt = sourceImage.alt || "확대된 사진";
    opener = sourceImage;
    lightbox.hidden = false;
    lightbox.style.display = "grid";
    document.body.classList.add("photo-lightbox-open");
    lightbox.querySelector(".photo-lightbox-close").focus();
  }

  document.addEventListener("click", (event) => {
    if (
      document.querySelector(".executive-control-panel") &&
      event.target.closest("[data-slot-class], .face-slot, .face-slot2, .face-slot3, .face-slot4, .face-slot5")
    ) {
      return;
    }

    const image = event.target.closest(
      "img[data-photo-lightbox], .bg-photo, .user-face, .photo-wrap img"
    );
    if (!image) return;

    event.preventDefault();
    openPhotoLightbox(image);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePhotoLightbox();
  });
})();

