/*
 * main_album_right.html 전용 동작 작성 공간
 */
function openNavRightItem() {
  // 앞으로 오른쪽 메뉴의 실행 내용을 여기에 작성하세요.
  return true;
}

function openSchedule() {
  // 동창회 일정 기능을 여기에 작성하세요.
  return true;
}

function openGameZoneLock() {
  const modal = document.getElementById("gameZoneLockModal");
  modal.hidden = false;
  document.getElementById("gameZoneLockClose")?.focus();
}

function closeGameZoneLock() {
  document.getElementById("gameZoneLockModal").hidden = true;
}

function openHoguShopLock() {
  const modal = document.getElementById("hoguShopLockModal");
  modal.hidden = false;
  document.getElementById("hoguShopLockClose")?.focus();
  return false;
}

function closeHoguShopLock() {
  document.getElementById("hoguShopLockModal").hidden = true;
}

function openContactAdminConfirm() {
  document.getElementById("contactAdminConfirmModal").hidden = false;
  return false;
}

function closeContactAdminConfirm() {
  document.getElementById("contactAdminConfirmModal").hidden = true;
}

function openLanguageConfirm(event, targetUrl, languageName) {
  event.preventDefault();
  const modal = document.getElementById("languageConfirmModal");
  document.getElementById("languageConfirmName").textContent = languageName;
  document.getElementById("languageConfirmGo").href = targetUrl;
  modal.hidden = false;
  document.getElementById("languageConfirmCancel")?.focus();
  return false;
}

function closeLanguageConfirm() {
  document.getElementById("languageConfirmModal").hidden = true;
}

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const gameZoneModal = document.getElementById("gameZoneLockModal");
  const hoguShopModal = document.getElementById("hoguShopLockModal");
  const contactAdminModal = document.getElementById(
    "contactAdminConfirmModal",
  );
  const languageModal = document.getElementById("languageConfirmModal");
  if (gameZoneModal && !gameZoneModal.hidden) {
    closeGameZoneLock();
  }
  if (hoguShopModal && !hoguShopModal.hidden) {
    closeHoguShopLock();
  }
  if (contactAdminModal && !contactAdminModal.hidden) {
    closeContactAdminConfirm();
  }
  if (languageModal && !languageModal.hidden) {
    closeLanguageConfirm();
  }
});

function openVote() {
  // 투표 기능을 여기에 작성하세요.
  return true;
}

function openAlumniNews() {
  // 동창 소식 기능을 여기에 작성하세요.
  return true;
}

function openEventPhotos() {
  // 행사 사진 기능을 여기에 작성하세요.
  return true;
}

function openDues() {
  // 회비 내역 기능을 여기에 작성하세요.
  return true;
}
