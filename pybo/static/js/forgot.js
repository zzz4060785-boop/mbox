const forgotForm = document.getElementById("forgotForm");
const forgotLoginId = document.getElementById("forgotLoginId");
const forgotMessage = document.getElementById("forgotMessage");

if (forgotForm) {
  forgotForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!forgotLoginId.value.trim()) {
      forgotMessage.textContent = "아이디를 입력해 주세요.";
      forgotLoginId.focus();
      return;
    }

    forgotMessage.textContent =
      "비밀번호 재설정 기능은 다음 단계에서 연결할 예정입니다.";
  });
}
