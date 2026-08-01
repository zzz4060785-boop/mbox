const allAgreeButton = document.getElementById("allAgreeBtn");
const agreementItems = [...document.querySelectorAll(".agree-item")];
const choiceGroups = [...document.querySelectorAll("[data-choice-group]")];
const carrierSelect = document.getElementById("carrierSelect");
const phoneInput = document.getElementById("phoneInput");
const sendPhoneButton = document.getElementById("sendPhoneBtn");
const phoneAuthForm = document.getElementById("phoneAuthForm");
const phoneAuthMessage = document.getElementById("phoneAuthMessage");
const testNoticeModal = document.getElementById("testNoticeModal");
const closeTestNoticeButton = document.getElementById("closeTestNoticeBtn");

/*
 * ================= 테스트 운영 안내 모달 동작 시작 =================
 * 페이지 진입 시 표시되며, 휴대폰 확인 버튼을 눌러도 다시 표시됩니다.
 * 정식 인증 도입 후에는 이 구간과 HTML/CSS의 같은 이름 구간을
 * 함께 삭제하세요.
 */
function openTestNoticeModal() {
  testNoticeModal.hidden = false;
  document.body.classList.add("test-notice-open");
  closeTestNoticeButton.focus();
}

function closeTestNoticeModal() {
  testNoticeModal.hidden = true;
  document.body.classList.remove("test-notice-open");
}

closeTestNoticeButton.addEventListener("click", closeTestNoticeModal);
document.addEventListener("DOMContentLoaded", openTestNoticeModal);
/* ================== 테스트 운영 안내 모달 동작 끝 ================== */

function setCircle(button, active) {
  button.querySelector(".check-circle").classList.toggle("active", active);
  button.setAttribute("aria-pressed", String(active));
}

function allTermsAreChecked() {
  return agreementItems.every((item) =>
    item.querySelector(".check-circle").classList.contains("active"),
  );
}

allAgreeButton.addEventListener("click", () => {
  const shouldActivate = !allTermsAreChecked();
  setCircle(allAgreeButton, shouldActivate);
  agreementItems.forEach((item) => setCircle(item, shouldActivate));
});

agreementItems.forEach((item) => {
  item.addEventListener("click", () => {
    const circle = item.querySelector(".check-circle");
    setCircle(item, !circle.classList.contains("active"));
    setCircle(allAgreeButton, allTermsAreChecked());
  });
});

choiceGroups.forEach((group) => {
  group.addEventListener("click", (event) => {
    const selectedButton = event.target.closest(".small-btn");
    if (!selectedButton) return;

    group
      .querySelectorAll(".small-btn")
      .forEach((button) => button.classList.remove("active"));
    selectedButton.classList.add("active");
    group.dataset.selected = selectedButton.dataset.value;
  });
});

carrierSelect.addEventListener("change", () => {
  carrierSelect.classList.toggle("selected", Boolean(carrierSelect.value));
});

phoneInput.addEventListener("input", () => {
  const numbers = phoneInput.value.replace(/\D/g, "").slice(0, 11);

  if (numbers.length < 4) {
    phoneInput.value = numbers;
  } else if (numbers.length < 8) {
    phoneInput.value = `${numbers.slice(0, 3)}-${numbers.slice(3)}`;
  } else {
    phoneInput.value =
      `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7)}`;
  }
});

sendPhoneButton.addEventListener("click", () => {
  if (phoneInput.value.replace(/\D/g, "").length < 10) {
    phoneAuthMessage.textContent = "올바른 전화번호를 입력해 주세요.";
    phoneInput.focus();
    return;
  }

  phoneAuthMessage.textContent =
    "휴대폰 인증 API는 아직 연결되지 않았습니다.";
});

phoneAuthForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const name = document.getElementById("authName").value.trim();
  const birthDate = document.getElementById("birthDate").value.trim();
  const gender = document.querySelector('[data-choice-group="gender"]');
  const country = document.querySelector('[data-choice-group="country"]');

  if (
    !allTermsAreChecked() ||
    !name ||
    !/^\d{8}$/.test(birthDate) ||
    !gender.dataset.selected ||
    !country.dataset.selected ||
    !carrierSelect.value ||
    phoneInput.value.replace(/\D/g, "").length < 10
  ) {
    phoneAuthMessage.textContent =
      "필수 약관과 본인확인 정보를 모두 입력해 주세요.";
    return;
  }

  phoneAuthMessage.textContent =
    "입력 확인이 완료되었습니다. 인증 API 연결이 필요합니다.";
});

// 테스트 기간에는 휴대폰 확인 버튼을 누를 때도 안내 모달을 표시합니다.
sendPhoneButton.addEventListener("click", openTestNoticeModal);
