/* =========================================================
   ⭐ 사랑별(Star) 중앙 사랑달 DB 현황 모달 (star.js)
   ========================================================= */

/* 중앙 사랑별 버튼 클릭 시 호출: 모든 사용자의 DB 실시간 사랑달 현황을 조회하여 모달 표시 */
async function openSarangdalStatusModal() {
  const modal = document.getElementById("starDetailModal");
  const modalTitle = document.getElementById("modalZoneTitle");
  const modalIcon = document.getElementById("modalZoneIcon");
  const modalTag = document.getElementById("modalZoneTag");
  const modalBody = document.getElementById("modalZoneBody");

  if (!modal) return;

  modalTitle.textContent = "나의 사랑달 DB 현황";
  modalIcon.textContent = "✨";
  modalTag.textContent = "실시간 DB 연동";

  modalBody.innerHTML = `
    <div style="text-align:center; padding:20px 0;">
      <p class="loading-msg">DB에서 사랑달 정보를 불러오는 중입니다...</p>
    </div>
  `;

  modal.hidden = false;
  createStarParticles();

  try {
    const response = await fetch("/api/sarangdal/status");
    if (!response.ok) {
      throw new Error("사랑달 정보를 불러올 수 없습니다.");
    }
    const data = await response.json();

    modalBody.innerHTML = `
      <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe082 100%); padding: 16px; border-radius: 16px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(255, 152, 0, 0.15);">
        <h3 style="margin: 0 0 10px; font-size: 1rem; color: #e65100; text-align: center;">
          💖 <strong>${escapeHtml(data.username)}님</strong>의 사랑달 현황
        </h3>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
          <div style="background: #ffffff; padding: 12px 8px; border-radius: 12px; text-align: center; border: 1.5px solid #ffb74d;">
            <span style="font-size: 0.75rem; color: #795548; font-weight: 700; display: block; margin-bottom: 2px;">현재 보유</span>
            <strong style="font-size: 1.3rem; color: #d35400;">${data.current_balance}개</strong>
          </div>
          <div style="background: #ffffff; padding: 12px 8px; border-radius: 12px; text-align: center; border: 1.5px solid #ff8f00;">
            <span style="font-size: 0.75rem; color: #795548; font-weight: 700; display: block; margin-bottom: 2px;">사진이 받은 사랑달</span>
            <strong style="font-size: 1.3rem; color: #e65100;">${data.total_received}개</strong>
          </div>
        </div>

        <div style="background: #ffffff; padding: 10px 12px; border-radius: 12px; text-align: center; border: 1px solid #ffe082; margin-bottom: 10px;">
          <span style="font-size: 0.78rem; color: #555;">내가 동창들에게 선물한 누적 사랑달: </span>
          <strong style="font-size: 0.95rem; color: #e91e63;">${data.total_given}개</strong>
        </div>

        <div style="font-size: 0.72rem; color: #666; text-align: center; line-height: 1.4; background: rgba(255, 255, 255, 0.7); padding: 8px; border-radius: 10px;">
          💡 <strong>자동 지급 규칙</strong>: 매달 1일마다 1개씩 자동 충전됩니다.<br>
          (최근 지급 월: ${escapeHtml(data.last_month)})
        </div>
      </div>
    `;
    modalBody.firstElementChild?.insertAdjacentHTML(
      "beforeend",
      `<div class="sarangdal-policy-note">
        매월 사랑달 1개를 무료로 지급합니다.<br>
        사용하지 않은 사랑달과 구매한 사랑달은 소멸되지 않고 계속 누적됩니다.
      </div>`,
    );
  } catch (error) {
    modalBody.innerHTML = `
      <div style="text-align:center; padding: 20px; color:#d33;">
        <p>⚠️ 사랑달 정보를 가져오지 못했습니다.</p>
        <p style="font-size:0.8rem; color:#777;">${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function closeStarDetail() {
  const modal = document.getElementById("starDetailModal");
  if (modal) modal.hidden = true;
}

function createStarParticles() {
  const container = document.querySelector(".star-layout-section .star-container");
  if (!container) return;

  for (let i = 0; i < 8; i++) {
    const particle = document.createElement("span");
    particle.textContent = "✨";
    particle.style.cssText = `
      position: absolute;
      left: ${Math.random() * 80 + 10}%;
      top: ${Math.random() * 80 + 10}%;
      font-size: ${Math.random() * 1 + 0.6}rem;
      pointer-events: none;
      z-index: 20;
      animation: particleFloat 1s ease-out forwards;
    `;
    container.appendChild(particle);
    setTimeout(() => particle.remove(), 1000);
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeStarDetail();
  }
});
