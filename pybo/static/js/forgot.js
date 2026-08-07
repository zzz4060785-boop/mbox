const forgotForm = document.getElementById("forgotForm");
const forgotLoginId = document.getElementById("forgotLoginId");
const forgotMessage = document.getElementById("forgotMessage");
const forgotSub = document.getElementById("forgotSub");
const step1Box = document.getElementById("step1Box");
const step2Box = document.getElementById("step2Box");
const submitBtn = document.getElementById("submitBtn");

const authCodeInput = document.getElementById("authCodeInput");
const newPasswordInput = document.getElementById("newPasswordInput");
const newPasswordConfirmInput = document.getElementById("newPasswordConfirmInput");

let currentStep = 1;
let matchedUserId = null;

if (forgotForm) {
  forgotForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (currentStep === 1) {
      const loginId = forgotLoginId.value.trim();
      if (!loginId) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "아이디 또는 이메일을 입력해 주세요.";
        forgotLoginId.focus();
        return;
      }

      submitBtn.disabled = true;
      forgotMessage.style.color = "#4f46e5";
      forgotMessage.textContent = "계정 확인 중...";

      try {
        const res = await fetch("/api/auth/forgot-password/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ login_id: loginId })
        });
        const data = await res.json();

        if (data.success) {
          matchedUserId = data.user_id;
          currentStep = 2;
          step1Box.style.display = "none";
          step2Box.style.display = "block";
          forgotSub.textContent = `${data.username}님의 비밀번호 변경`;
          forgotMessage.style.color = "#10b981";
          forgotMessage.textContent = data.message;
          submitBtn.disabled = false;
          submitBtn.textContent = "🔒 비밀번호 변경하기";
          authCodeInput.focus();
        } else {
          forgotMessage.style.color = "#ef4444";
          forgotMessage.textContent = data.message || "등록되지 않은 아이디입니다.";
          submitBtn.disabled = false;
        }
      } catch (err) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "서버 연동 중 오류가 발생했습니다.";
        submitBtn.disabled = false;
      }
    } else if (currentStep === 2) {
      const code = authCodeInput.value.trim();
      const newPw = newPasswordInput.value;
      const confirmPw = newPasswordConfirmInput.value;

      if (!code) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "인증번호 6자리를 입력해 주세요. (테스트: 123456)";
        authCodeInput.focus();
        return;
      }

      if (!newPw || newPw.length < 8) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "새 비밀번호는 8자 이상 입력해 주세요.";
        newPasswordInput.focus();
        return;
      }

      if (newPw !== confirmPw) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "새 비밀번호와 비밀번호 확인이 일치하지 않습니다.";
        newPasswordConfirmInput.focus();
        return;
      }

      submitBtn.disabled = true;
      forgotMessage.style.color = "#4f46e5";
      forgotMessage.textContent = "비밀번호 변경 처리 중...";

      try {
        const res = await fetch("/api/auth/forgot-password/reset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: matchedUserId,
            login_id: forgotLoginId.value.trim(),
            code: code,
            new_password: newPw
          })
        });
        const data = await res.json();

        if (data.success) {
          forgotMessage.style.color = "#10b981";
          forgotMessage.innerHTML = `<strong>${data.message}</strong>`;
          alert(data.message);
          window.location.href = "/";
        } else {
          forgotMessage.style.color = "#ef4444";
          forgotMessage.textContent = data.message || "비밀번호 변경에 실패했습니다.";
          submitBtn.disabled = false;
        }
      } catch (err) {
        forgotMessage.style.color = "#ef4444";
        forgotMessage.textContent = "서버 변경 처리 중 오류가 발생했습니다.";
        submitBtn.disabled = false;
      }
    }
  });
}
