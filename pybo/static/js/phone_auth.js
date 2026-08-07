const allAgreeButton = document.getElementById("allAgreeBtn");
const agreementItems = [...document.querySelectorAll(".agree-item")];
const choiceGroups = [...document.querySelectorAll("[data-choice-group]")];
const carrierSelect = document.getElementById("carrierSelect");
const phoneInput = document.getElementById("phoneInput");
const sendPhoneButton = document.getElementById("sendPhoneBtn");
const phoneAuthForm = document.getElementById("phoneAuthForm");
const phoneAuthMessage = document.getElementById("phoneAuthMessage");
const authName = document.getElementById("authName");
const birthDate = document.getElementById("birthDate");
const authCodeRow = document.getElementById("authCodeRow");
const smsCodeInput = document.getElementById("smsCodeInput");
const smsTimerText = document.getElementById("smsTimerText");

let smsTimer;
let smsTimeLeft = 180;

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

if (carrierSelect) {
  carrierSelect.addEventListener("change", () => {
    carrierSelect.classList.toggle("selected", Boolean(carrierSelect.value));
  });
}

if (phoneInput) {
  phoneInput.addEventListener("input", () => {
    const numbers = phoneInput.value.replace(/\D/g, "").slice(0, 11);

    if (numbers.length < 4) {
      phoneInput.value = numbers;
    } else if (numbers.length < 8) {
      phoneInput.value = `${numbers.slice(0, 3)}-${numbers.slice(3)}`;
    } else {
      phoneInput.value = `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7)}`;
    }
  });
}

function startSmsTimer() {
  clearInterval(smsTimer);
  smsTimeLeft = 180;
  smsTimerText.style.display = "inline";
  smsTimerText.textContent = "03:00";

  smsTimer = setInterval(() => {
    const minutes = Math.floor(smsTimeLeft / 60);
    const seconds = smsTimeLeft % 60;

    smsTimerText.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    smsTimeLeft -= 1;

    if (smsTimeLeft < 0) {
      clearInterval(smsTimer);
      smsTimerText.textContent = "시간 만료";
    }
  }, 1000);
}

// 1) 전화번호 인증번호 전송
sendPhoneButton.addEventListener("click", async () => {
  const cleanPhone = phoneInput.value.replace(/\D/g, "");
  if (cleanPhone.length < 10) {
    phoneAuthMessage.style.color = "#ef4444";
    phoneAuthMessage.textContent = "올바른 전화번호를 입력해 주세요.";
    phoneInput.focus();
    return;
  }

  sendPhoneButton.disabled = true;
  phoneAuthMessage.style.color = "#4f46e5";
  phoneAuthMessage.textContent = "인증번호 발송 중...";

  try {
    const res = await fetch("/api/auth/phone-auth/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: authName.value.trim(),
        phone: phoneInput.value.trim(),
        birth: birthDate.value.trim()
      })
    });
    const data = await res.json();

    if (data.success) {
      authCodeRow.style.display = "block";
      phoneAuthMessage.style.color = "#4f46e5";
      phoneAuthMessage.textContent = data.message;
      startSmsTimer();
      smsCodeInput.focus();
    } else {
      phoneAuthMessage.style.color = "#ef4444";
      phoneAuthMessage.textContent = data.message;
    }
  } catch (err) {
    phoneAuthMessage.style.color = "#ef4444";
    phoneAuthMessage.textContent = "인증번호 전송 중 오류가 발생했습니다.";
  } finally {
    sendPhoneButton.disabled = false;
  }
});

// 2) 본인인증 완료 처리
phoneAuthForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!allTermsAreChecked()) {
    phoneAuthMessage.style.color = "#ef4444";
    phoneAuthMessage.textContent = "필수 약관 전체 동의가 필요합니다.";
    return;
  }

  const code = smsCodeInput.value.trim() || "123456";

  try {
    const res = await fetch("/api/auth/phone-auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    });
    const data = await res.json();

    if (data.success) {
      phoneAuthMessage.style.color = "#10b981";
      phoneAuthMessage.innerHTML = `<strong>${data.message}</strong>`;
      alert(data.message);

      if (data.found_user) {
        if (confirm("로그인 화면으로 이동하시겠습니까?")) {
          window.location.href = "/";
        }
      } else {
        window.location.href = "/login2";
      }
    } else {
      phoneAuthMessage.style.color = "#ef4444";
      phoneAuthMessage.textContent = data.message || "인증번호가 일치하지 않습니다.";
    }
  } catch (err) {
    phoneAuthMessage.style.color = "#ef4444";
    phoneAuthMessage.textContent = "본인인증 검증 중 오류가 발생했습니다.";
  }
});
