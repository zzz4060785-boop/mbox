const findInput = document.getElementById("findInput");
const nextButton = document.getElementById("nextBtn");
const codeBox = document.getElementById("codeBox");
const codeInput = document.getElementById("codeInput");
const timerText = document.getElementById("timerText");
const successCheck = document.getElementById("successCheck");
const resendButton = document.getElementById("resendBtn");
const findIdMessage = document.getElementById("findIdMessage");
const scriptElement = document.currentScript;
const loginUrl = scriptElement.dataset.loginUrl;

let timer;
let timeLeft = 180;

function updateNextButton() {
  const cleanValue = findInput.value.replace(/[- ]/g, "").trim();
  nextButton.disabled = cleanValue.length < 5;
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

    timerText.textContent =
      `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    timeLeft -= 1;

    if (timeLeft < 0) {
      clearInterval(timer);
      timerText.textContent = "시간 만료";
      resendButton.classList.add("show");
    }
  }, 1000);
}

function checkCode() {
  const code = codeInput.value.replace(/\D/g, "").slice(0, 6);
  codeInput.value = code;

  if (code === "123456") {
    clearInterval(timer);
    timerText.style.display = "none";
    resendButton.classList.remove("show");
    successCheck.classList.add("show");
    findIdMessage.textContent = "데모 인증이 완료되었습니다.";

    setTimeout(() => {
      window.location.href = loginUrl;
    }, 1200);
    return;
  }

  successCheck.classList.remove("show");

  if (code.length === 6 && !codeInput.classList.contains("shake")) {
    codeInput.classList.add("shake");
    setTimeout(() => codeInput.classList.remove("shake"), 300);
  }
}

findInput.addEventListener("input", updateNextButton);

nextButton.addEventListener("click", () => {
  codeBox.classList.add("show");
  findIdMessage.textContent = "데모 인증번호는 123456입니다.";
  startTimer();
  codeInput.focus();
});

codeInput.addEventListener("input", checkCode);
resendButton.addEventListener("click", startTimer);
