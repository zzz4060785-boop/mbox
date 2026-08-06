(() => {
  let opener = null;

  function closePhotoLightbox() {
    const lightbox = document.getElementById("sharedPhotoLightbox");
    if (!lightbox) return;
    lightbox.hidden = true;
    lightbox.style.display = "none";

    const container = lightbox.querySelector(".photo-lightbox-container");
    if (container) container.innerHTML = "";

    document.body.classList.remove("photo-lightbox-open");
    opener?.focus();
  }

  function openPhotoLightbox(targetElement) {
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
        <div class="photo-lightbox-container"></div>
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

    const container = lightbox.querySelector(".photo-lightbox-container");
    container.innerHTML = "";

    const photoWrap = targetElement.closest(".photo-wrap");
    if (photoWrap && photoWrap.querySelector("[data-slot-class]")) {
      // 🌟 졸업앨범: 배경사진 + 합성된 모든 얼굴 슬롯을 그대로 복사해서 확대 팝업에 표시!
      const clone = photoWrap.cloneNode(true);

      // 클론 내부 드래그/클릭 오작동 방지
      clone.style.pointerEvents = "none";
      clone.style.width = "100%";
      clone.style.margin = "0 auto";

      container.appendChild(clone);
    } else {
      // 일반 단일 이미지 확대
      const img = document.createElement("img");
      const srcImg =
        targetElement.tagName === "IMG"
          ? targetElement
          : targetElement.querySelector("img");
      if (srcImg) {
        img.src = srcImg.currentSrc || srcImg.src;
        img.alt = srcImg.alt || "확대된 사진";
      }
      container.appendChild(img);
    }

    opener = targetElement;
    lightbox.hidden = false;
    lightbox.style.display = "grid";
    document.body.classList.add("photo-lightbox-open");
    lightbox.querySelector(".photo-lightbox-close").focus();
  }

  document.addEventListener("click", (event) => {
    // 1. 임원 제어 패널, 버튼, 입력창 클릭 시 제외
    if (event.target.closest(".executive-control-panel, button, input")) {
      return;
    }

    // 2. 앨범 구역(.photo-wrap, .album-section, 얼굴 슬롯 등) 내부의 모든 클릭은 라이트박스 확대 완전 금지
    if (
      event.target.closest(
        ".photo-wrap, .album-section, [data-slot-class], .face-slot, .face-slot2, .face-slot3, .face-slot4, .face-slot5, .user-face"
      )
    ) {
      return;
    }

    // 3. 앨범 외 일반 게시판 등의 data-photo-lightbox 속성을 가진 이미지에 한해 확대 허용
    const target = event.target.closest("img[data-photo-lightbox]");
    if (!target) return;

    event.preventDefault();
    openPhotoLightbox(target);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePhotoLightbox();
  });
})();

