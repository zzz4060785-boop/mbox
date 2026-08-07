// 페이지가 완전히 로드된 후 실행
document.addEventListener("DOMContentLoaded", function () {
  // 1. 일반 로그인 폼 제어
  const loginForm = document.querySelector("form");
  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const loginValue = this.login ? this.login.value.trim() : "";
      const passwordValue = this.password ? this.password.value : "";

      if (!loginValue || !passwordValue) {
        alert("아이디(이메일)와 비밀번호를 입력해주세요!");
        return;
      }

      const remember = this.remember ? this.remember.checked : false;

      fetch("/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          login: loginValue,
          password: passwordValue,
          remember: remember,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success && data.redirect_url) {
            window.location.replace(data.redirect_url);
          } else {
            let msgBox = document.querySelector(".login-form-messages");
            if (!msgBox) {
              msgBox = document.createElement("div");
              msgBox.className = "login-form-messages";
              msgBox.setAttribute("role", "alert");
              const checkWrap = document.querySelector(".check-wrap");
              if (checkWrap && checkWrap.parentNode) {
                checkWrap.parentNode.insertBefore(msgBox, checkWrap.nextSibling);
              } else {
                loginForm.appendChild(msgBox);
              }
            }
            msgBox.innerHTML = `<p class="login-form-message">${data.message || "아이디 또는 비밀번호를 확인해 주세요."}</p>`;
          }
        })
        .catch((err) => {
          console.error("Login fetch error:", err);
          alert("로그인 처리 중 오류가 발생했습니다. 다시 시도해 주세요.");
        });
    });
  }

  // 2. 소셜 로그인 버튼 연결 (HTML에 추가한 ID로 정확하게 찾기)

  // 구글 로그인
  const googleBtn = document.getElementById("google-login");
  if (googleBtn) {
    googleBtn.addEventListener("click", function () {
      location.href = googleBtn.dataset.url;
    });
  }

  // 카카오 로그인
  const kakaoBtn = document.getElementById("kakao-login");
  if (kakaoBtn) {
    kakaoBtn.addEventListener("click", function () {
      location.href = kakaoBtn.dataset.url;
    });
  }

  // 네이버 로그인
  const naverBtn = document.getElementById("naver-login");
  if (naverBtn) {
    naverBtn.addEventListener("click", function () {
      location.href = naverBtn.dataset.url;
    });
  }
});
