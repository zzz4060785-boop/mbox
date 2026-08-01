const signupModal = document.getElementById("signupModal");
const openSignupBtn = document.getElementById("openSignupBtn");
const closeSignupBtn = document.getElementById("closeSignupBtn");

function openSignup() {
  if (!signupModal) return;
  signupModal.classList.add("is-open");
  signupModal.setAttribute("aria-hidden", "false");
}

function closeSignup() {
  if (!signupModal) return;
  signupModal.classList.remove("is-open");
  signupModal.setAttribute("aria-hidden", "true");
}

openSignupBtn?.addEventListener("click", openSignup);
closeSignupBtn?.addEventListener("click", closeSignup);

signupModal?.addEventListener("click", (event) => {
  if (event.target === signupModal) {
    closeSignup();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSignup();
  }
});

document.querySelectorAll(".social-login-btn").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.url) {
      window.location.href = button.dataset.url;
    }
  });
});

document.querySelector(".qr-btn")?.addEventListener("click", () => {
  alert("QR코드 로그인은 준비 중입니다.");
});
