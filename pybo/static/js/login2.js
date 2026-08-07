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

const login2Form = document.getElementById("loginForm");
if (login2Form) {
  login2Form.addEventListener("submit", function (e) {
    e.preventDefault();

    const loginId = this.login_id ? this.login_id.value.trim() : "";
    const password = this.password ? this.password.value : "";
    const saveInfo = this.save_info ? this.save_info.checked : false;

    if (!loginId || !password) {
      alert("아이디 또는 이메일과 비밀번호를 입력해주세요!");
      return;
    }

    fetch("/login2", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        login_id: loginId,
        password: password,
        save_info: saveInfo,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.redirect_url) {
          window.location.replace(data.redirect_url);
        } else {
          let flashArea = document.querySelector(".login-flash-area");
          if (!flashArea) {
            flashArea = document.createElement("div");
            flashArea.className = "login-flash-area";
            login2Form.parentNode.insertBefore(flashArea, login2Form);
          }
          flashArea.innerHTML = `<p class="login-flash-message">${data.message || "아이디 또는 비밀번호를 확인해 주세요."}</p>`;
        }
      })
      .catch((err) => {
        console.error("Login2 fetch error:", err);
        alert("로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.");
      });
  });
}

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
