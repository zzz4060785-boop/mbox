(() => {
  let opener = null;

  function closePhotoLightbox() {
    const lightbox = document.getElementById("sharedPhotoLightbox");
    if (!lightbox || lightbox.hidden) return;
    lightbox.hidden = true;
    lightbox.querySelector("img").removeAttribute("src");
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
        <button type="button" class="photo-lightbox-close">&larr; 뒤로가기</button>
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
    enlargedImage.alt = sourceImage.alt;
    opener = sourceImage;
    lightbox.hidden = false;
    document.body.classList.add("photo-lightbox-open");
    lightbox.querySelector(".photo-lightbox-close").focus();
  }

  document.addEventListener("click", (event) => {
    const image = event.target.closest("img[data-photo-lightbox]");
    if (!image) return;
    event.preventDefault();
    openPhotoLightbox(image);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePhotoLightbox();
  });
})();
