const findInput = document.getElementById("findInput");
const nextButton = document.getElementById("nextBtn");
const codeBox = document.getElementById("codeBox");
const codeInput = document.getElementById("codeInput");
const timerText = document.getElementById("timerText");
const successCheck = document.getElementById("successCheck");
const resendButton = document.getElementById("resendBtn");
const findIdMessage = document.getElementById("findIdMessage");
const scriptElement = document.currentScript;
const loginUrl = scriptElement ? scriptElement.dataset.loginUrl : "/";

let timer;
let timeLeft = 180;

function updateNextButton() {
  const cleanValue = findInput.value.replace(/[- ]/g, "").trim();
  nextButton.disabled = cleanValue.length < 3;
}

function startTimer() {
  clearInterval(timer);
  timeLeft = 180;
  timerText.style.display = "block";
  timerText.textContent = "03:00";
  resendButton.classList.remove("show");

  timer = setInterval(() => {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;

    timerText.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    timeLeft -= 1;

    if (timeLeft < 0) {
      clearInterval(timer);
      timerText.textContent = "시간 만료";
      resendButton.classList.add("show");
    }
  }, 1000);
}

async function requestFindId() {
  const query = findInput.value.trim();
  if (!query) {
    findIdMessage.textContent = "전화번호 또는 이메일을 입력해 주세요.";
    return;
  }

  nextButton.disabled = true;
  findIdMessage.textContent = "회원 정보 조회 중...";

  try {
    const res = await fetch("/api/auth/find-id/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });
    const data = await res.json();

    if (data.success) {
      codeBox.classList.add("show");
      findIdMessage.style.color = "#4f46e5";
      findIdMessage.textContent = data.message;
      startTimer();
      codeInput.focus();
    } else {
      findIdMessage.style.color = "#ef4444";
      findIdMessage.textContent = data.message || "회원 정보를 찾을 수 없습니다.";
      nextButton.disabled = false;
    }
  } catch (err) {
    findIdMessage.style.color = "#ef4444";
    findIdMessage.textContent = "서버 통신 중 오류가 발생했습니다.";
    nextButton.disabled = false;
  }
}

async function checkCode() {
  const code = codeInput.value.replace(/\D/g, "").slice(0, 6);
  codeInput.value = code;

  if (code.length === 6) {
    try {
      const res = await fetch("/api/auth/find-id/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code })
      });
      const data = await res.json();

      if (data.success) {
        clearInterval(timer);
        timerText.style.display = "none";
        resendButton.classList.remove("show");
        successCheck.classList.add("show");
        findIdMessage.style.color = "#10b981";
        findIdMessage.innerHTML = `🎉 <strong>${data.message}</strong>`;

        setTimeout(() => {
          if (confirm("회원님의 아이디가 확인되었습니다! 로그인 페이지로 이동할까요?")) {
            window.location.href = loginUrl;
          }
        }, 800);
      } else {
        successCheck.classList.remove("show");
        findIdMessage.style.color = "#ef4444";
        findIdMessage.textContent = data.message;
      }
    } catch (err) {
      findIdMessage.textContent = "인증 검증 중 오류가 발생했습니다.";
    }
  }
}

findInput.addEventListener("input", updateNextButton);
nextButton.addEventListener("click", requestFindId);
codeInput.addEventListener("input", checkCode);
resendButton.addEventListener("click", requestFindId);
