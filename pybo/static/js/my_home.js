document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("myHomeStatus");

  /* =========================
     말풍선 (Speech Bubble) 관리
  ========================= */
  const bubbleTimeouts = {};

  function showSpeechBubble(slotNumber, text) {
    const bubble = document.getElementById(`speechBubble${slotNumber}`);
    if (!bubble) return;

    bubble.textContent = text;
    bubble.hidden = false;
    bubble.style.display = "block";

    if (bubbleTimeouts[slotNumber]) {
      clearTimeout(bubbleTimeouts[slotNumber]);
    }

    bubbleTimeouts[slotNumber] = setTimeout(() => {
      bubble.hidden = true;
      bubble.style.display = "none";
    }, 5500);
  }

  /* =========================
     1:1 교실 아바타 대화 (DB 연동)
  ========================= */
  const urlParams = new URLSearchParams(window.location.search);
  const chatUserId = urlParams.get("chat_user");

  let lastSeenMessageId = 0;

  async function initClassroomChat() {
    if (!chatUserId) {
      if (status) {
        status.textContent =
          "접속 중인 1촌 목록에서 '1:1 대화하기'를 누르면 짝꿍 아바타가 교실에 등장합니다!";
      }
      return;
    }

    const slot2 = document.getElementById("avatarSlot2");
    const slot2Name = document.getElementById("avatarSlot2Name");
    const chatTargetName = document.getElementById("chatTargetName");
    const chatInput = document.getElementById("classroomChatInput");
    const chatSendBtn = document.getElementById("classroomChatSendBtn");

    try {
      const response = await fetch(`/api/social/users/${chatUserId}`);
      const data = await response.json();

      if (!response.ok || !data.user) {
        if (status) status.textContent = "1촌 정보를 불러올 수 없습니다.";
        return;
      }

      const targetUser = data.user;
      if (slot2) slot2.hidden = false;
      if (slot2Name) slot2Name.textContent = targetUser.username;
      if (chatTargetName)
        chatTargetName.textContent = `${targetUser.username}님과 대화 중`;

      if (status) {
        status.textContent = `${targetUser.username}님과 교실에 입실했습니다! 대화를 나눠보세요.`;
      }

      // 대화 전송 이벤트
      async function sendChatMessage() {
        const content = chatInput.value.trim();
        if (!content) return;

        chatSendBtn.disabled = true;
        try {
          const postRes = await fetch("/api/social/messages", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              receiver_id: Number(chatUserId),
              content: content,
            }),
          });
          const postData = await postRes.json();

          if (!postRes.ok) {
            alert(postData.message || "대화 전송에 실패했습니다.");
            return;
          }

          chatInput.value = "";
          showSpeechBubble(1, content);
        } catch (error) {
          alert("전송 중 오류가 발생했습니다.");
        } finally {
          chatSendBtn.disabled = false;
          chatInput.focus();
        }
      }

      if (chatSendBtn) chatSendBtn.addEventListener("click", sendChatMessage);
      if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
          if (e.key === "Enter") sendChatMessage();
        });
      }

      // 실시간 메시지 수신 폴링 (3초 간격)
      async function checkIncomingMessages() {
        try {
          const res = await fetch(`/api/social/chat/${chatUserId}`);
          if (!res.ok) return;
          const chatData = await res.json();

          if (chatData.messages && chatData.messages.length > 0) {
            const latestMsg =
              chatData.messages[chatData.messages.length - 1];
            if (
              latestMsg.id > lastSeenMessageId &&
              Number(latestMsg.sender_id) === Number(chatUserId)
            ) {
              lastSeenMessageId = latestMsg.id;
              showSpeechBubble(2, latestMsg.content);
            } else if (lastSeenMessageId === 0) {
              lastSeenMessageId = latestMsg.id;
            }
          }
        } catch (e) {
          // ignore
        }
      }

      checkIncomingMessages();
      setInterval(checkIncomingMessages, 3000);
    } catch (error) {
      console.error("Failed to init classroom chat:", error);
    }
  }

  initClassroomChat();

  /* =========================
     아바타 클릭 선택
  ========================= */
  document.querySelectorAll(".classroom-avatar").forEach((avatar) => {
    avatar.addEventListener("click", () => {
      const nameTag = avatar.querySelector(".avatar-name-tag");
      const name = nameTag ? nameTag.textContent : "아바타";
      if (status) {
        status.textContent = `${name}를 선택했습니다.`;
      }
    });
  });

  /* =========================
     교실 사진 확대
  ========================= */
  const classroomPhotoOpen = document.getElementById("classroomPhotoOpen");
  const classroomPhotoImage = document.querySelector(".classroom-background-image");
  let photoLightbox = null;
  let photoLightboxImage = null;
  let photoLightboxClose = null;

  function closePhotoLightbox() {
    if (!photoLightbox) return;
    photoLightbox.hidden = true;
    photoLightbox.setAttribute("aria-hidden", "true");
    document.body.classList.remove("photo-lightbox-open");
    if (classroomPhotoOpen) classroomPhotoOpen.focus();
  }

  function createPhotoLightbox() {
    const existingLightbox = document.getElementById("sharedPhotoLightbox");
    if (existingLightbox) {
      photoLightbox = existingLightbox;
      photoLightboxImage = photoLightbox.querySelector("img");
      photoLightboxClose = photoLightbox.querySelector(".photo-lightbox-close");
      return;
    }

    photoLightbox = document.createElement("div");
    photoLightbox.id = "sharedPhotoLightbox";
    photoLightbox.className = "photo-lightbox";
    photoLightbox.hidden = true;
    photoLightbox.setAttribute("aria-hidden", "true");
    photoLightbox.innerHTML = `
      <button type="button" class="photo-lightbox-close" aria-label="확대 사진 닫기">← 뒤로가기</button>
      <img src="" alt="">
    `;

    document.body.appendChild(photoLightbox);
    photoLightboxImage = photoLightbox.querySelector("img");
    photoLightboxClose = photoLightbox.querySelector(".photo-lightbox-close");

    photoLightboxClose.addEventListener("click", closePhotoLightbox);
    photoLightbox.addEventListener("click", (event) => {
      if (event.target === photoLightbox) closePhotoLightbox();
    });
    photoLightboxImage.addEventListener("click", (e) => e.stopPropagation());
  }

  function openPhotoLightbox() {
    if (!classroomPhotoImage) return;
    createPhotoLightbox();
    photoLightboxImage.src =
      classroomPhotoImage.currentSrc || classroomPhotoImage.src;
    photoLightboxImage.alt =
      classroomPhotoImage.alt || "확대된 교실 사진";
    photoLightbox.hidden = false;
    photoLightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("photo-lightbox-open");
    photoLightboxClose.focus();
  }

  if (classroomPhotoOpen) {
    classroomPhotoOpen.addEventListener("click", openPhotoLightbox);
  }

  /* =========================
     아바타샵 모달
  ========================= */
  const shopModal = document.getElementById("avatarShopModal");
  const shopOpen = document.getElementById("avatarShopOpen");
  const shopClose = document.getElementById("avatarShopClose");
  const shopBackdrop = shopModal?.querySelector("[data-avatar-shop-close]");

  function closeAvatarShopModal() {
    if (!shopModal) return;
    shopModal.hidden = true;
    if (shopOpen) shopOpen.focus();
  }

  if (shopOpen && shopModal && shopClose) {
    shopOpen.addEventListener("click", () => {
      shopModal.hidden = false;
      shopClose.focus();
    });
    shopClose.addEventListener("click", closeAvatarShopModal);
    shopBackdrop?.addEventListener("click", closeAvatarShopModal);
  }

  /* =========================
     ESC 키 처리
  ========================= */
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (photoLightbox && !photoLightbox.hidden) {
      closePhotoLightbox();
      return;
    }
    if (shopModal && !shopModal.hidden) {
      closeAvatarShopModal();
    }
  });
});