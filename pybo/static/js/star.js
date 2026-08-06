/* =========================================================
   ⭐ 사랑별(Star) 5개 구역 & 중앙 사랑달 DB 현황 모달 (star.js)
   ========================================================= */

const ZONE_INFO = {
  restaurant: {
    title: "1구역: 맛집 & 핫플",
    icon: "🍜",
    tag: "동창 추천 맛집",
    desc: "동창들이 직접 다녀오고 추천한 최고의 맛집과 핫플레이스 공간입니다.",
    url: "#",
  },
  cafe: {
    title: "2구역: 카페 & 문화",
    icon: "☕",
    tag: "분위기 카페·문화",
    desc: "분위기 좋은 스페셜티 카페, 디저트 숍 및 모임 공간입니다.",
    url: "#",
  },
  alumni: {
    title: "3구역: 동창 가게 & 사업",
    icon: "🏬",
    tag: "우리 동창 업체",
    desc: "동창들이 운영하는 매장 및 사업체를 함께 응원하고 방문하는 공간입니다.",
    url: "#",
  },
  travel: {
    title: "4구역: 명소 & 여행 스팟",
    icon: "🏞️",
    tag: "추억 여행지",
    desc: "동창들과 함께 힐링하기 좋은 주변 여행지 및 인근 명소 공간입니다.",
    url: "#",
  },
  other: {
    title: "5구역: 추억 이야기 & 소통",
    icon: "💖",
    tag: "자유 이야기",
    desc: "동창들의 자유로운 소식, 일상 추억 및 따뜻한 소통 공간입니다.",
    url: "#",
  },
};

function handleStarZoneClick(event, category) {
  selectStarZone(category);
  return false;
}

/* 중앙 사랑별 버튼 클릭 시 호출: 모든 사용자의 DB 실시간 사랑달 현황을 조회하여 모달 표시 */
async function openSarangdalStatusModal() {
  const modal = document.getElementById("starDetailModal");
  const modalTitle = document.getElementById("modalZoneTitle");
  const modalIcon = document.getElementById("modalZoneIcon");
  const modalTag = document.getElementById("modalZoneTag");
  const modalBody = document.getElementById("modalZoneBody");

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
          (최근 지급 월: ${data.last_month})
        </div>
      </div>
    `;
  } catch (error) {
    modalBody.innerHTML = `
      <div style="text-align:center; padding: 20px; color:#d33;">
        <p>⚠️ 사랑달 정보를 가져오지 못했습니다.</p>
        <p style="font-size:0.8rem; color:#777;">${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function selectStarZone(category) {
  const info = ZONE_INFO[category] || ZONE_INFO.other;
  const modal = document.getElementById("starDetailModal");
  const modalTitle = document.getElementById("modalZoneTitle");
  const modalIcon = document.getElementById("modalZoneIcon");
  const modalTag = document.getElementById("modalZoneTag");
  const modalBody = document.getElementById("modalZoneBody");

  modalTitle.textContent = info.title;
  modalIcon.textContent = info.icon;
  modalTag.textContent = info.tag;

  modalBody.innerHTML = `
    <div class="zone-info-card" style="background:#fff8e1; padding:14px; border-radius:14px; margin-bottom:14px; text-align:center;">
      <p style="margin:0 0 6px; font-weight:700; color:#d35400;">${info.tag}</p>
      <p style="margin:0 0 10px; font-size:0.82rem; color:#555;">${info.desc}</p>
      <a href="#" onclick="alert('추후 확장 예정 구역입니다 ✨'); return false;" class="zone-go-btn" style="display:inline-block; padding:8px 16px; background:#f57f17; color:#fff; font-weight:800; border-radius:10px; text-decoration:none; font-size:0.85rem;">
        ✨ ${info.tag} 구역 (확장 예정)
      </a>
    </div>
    <div id="starCategoryList">
      <p class="loading-msg">불러오는 중입니다...</p>
    </div>
  `;

  modal.hidden = false;
  createStarParticles();
  loadCategoryPosts(category);
}

function closeStarDetail() {
  const modal = document.getElementById("starDetailModal");
  if (modal) modal.hidden = true;
}

async function loadCategoryPosts(category) {
  const container = document.getElementById("starCategoryList");
  if (!container) return;

  try {
    const response = await fetch(`/api/recommendations?category=${category}`);
    if (!response.ok) {
      throw new Error("추천 목록을 불러오지 못했습니다.");
    }
    const data = await response.json();
    const posts = data.posts || [];

    if (!posts.length) {
      container.innerHTML = `
        <div style="text-align:center; padding:16px 0; color:#95a5a6;">
          <p style="font-size:1.6rem; margin-bottom:4px;">🌟</p>
          <p style="margin:0; font-size:0.8rem;">사랑별 5대 구역 전용 확장 공간 준비 중입니다 ✨</p>
        </div>
      `;
      return;
    }

    container.innerHTML = posts
      .map(
        (post) => `
      <a href="#" onclick="alert('추후 확장 예정입니다 ✨'); return false;" class="star-post-item" style="display:block; text-decoration:none; border:1px solid #ffe082; padding:10px; border-radius:10px; margin-bottom:8px; background:#fff;">
        <h4 style="margin:0 0 4px; font-size:0.9rem; color:#2c3e50;">${escapeHtml(post.title)}</h4>
        <p style="margin:0; font-size:0.8rem; color:#555;">${escapeHtml(post.content)}</p>
      </a>
    `,
      )
      .join("");
  } catch (_) {
    const info = ZONE_INFO[category] || ZONE_INFO.other;
    container.innerHTML = `
      <div style="text-align:center; padding:12px; color:#777; font-size:0.8rem;">
        ✨ ${info.tag} 구역 확장 준비 중입니다.
      </div>
    `;
  }
}

function createStarParticles() {
  const container = document.querySelector(".star-container");
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
