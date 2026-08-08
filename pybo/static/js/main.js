// 페이지가 완전히 로드된 후 실행
document.addEventListener("DOMContentLoaded", function () {
  // 1. 일반 로그인 폼 제어
  const loginForm = document.querySelector("form");
  if (loginForm) {
    loginForm.addEventListener("submit", function (e) {
      // HTML에서 name="login"으로 바꿨으므로 email 대신 login으로 가져옵니다.
      const loginValue = this.login.value;
      const passwordValue = this.password.value;

      if (!loginValue || !passwordValue) {
        alert("아이디(이메일)와 비밀번호를 입력해주세요!");
        e.preventDefault();
      }
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
