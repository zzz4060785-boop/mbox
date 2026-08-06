// =================================================================
// 1. 📷 [1번~5번 앨범] 모든 슬롯의 이미지 경로 마스터 레지스트리
// =================================================================
const faceScript = document.currentScript;
const uploadPhotoUrl = faceScript.dataset.uploadUrl;
const commentsUrlTemplate = faceScript.dataset.commentsUrl;

function getCommentsUrl(roomId) {
  return commentsUrlTemplate.replace(/\/0$/, `/${roomId}`);
}

const executivePhotoRegistry = {
  // ─── 1번째 졸업사진 좌표 매핑 (1~8번) ───
  "grad-face1": "/static/images/myface.jpg",
  "grad-face2": "/static/images/myface.jpg",
  "grad-face3": "/static/images/myface.jpg",
  "grad-face4": "/static/images/myface.jpg",
  "grad-face5": "/static/images/myface.jpg",
  "grad-face6": "/static/images/myface.jpg",
  "grad-face7": "/static/images/myface.jpg",
  "grad-face8": "/static/images/myface.jpg",

  // ─── 2번째 졸업사진 좌표 매핑 (1~7번) ───
  "grad-face_male1": "/static/images/myface_male.jpg",
  "grad-face_male2": "/static/images/myface_male.jpg",
  "grad-face_male3": "/static/images/myface_male.jpg",
  "grad-face_male4": "/static/images/myface_male.jpg",
  "grad-face_male5": "/static/images/myface_male.jpg",
  "grad-face_male6": "/static/images/myface_male.jpg",
  "grad-face_male7": "/static/images/myface_male.jpg",

  // ─── 3번째 졸업사진 좌표 매핑 (1~8번) ───
  "grad-face_female1": "/static/images/myface_female.jpg",
  "grad-face_female2": "/static/images/myface_female.jpg",
  "grad-face_female3": "/static/images/myface_female.jpg",
  "grad-face_female4": "/static/images/myface_female.jpg",
  "grad-face_female5": "/static/images/myface_female.jpg",
  "grad-face_female6": "/static/images/myface_female.jpg",
  "grad-face_female7": "/static/images/myface_female.jpg",
  "grad-face_female8": "/static/images/myface_female.jpg",

  // ─── 4번째 졸업사진 좌표 매핑 (1~8번) ───
  grad_face_male_outing1: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing2: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing3: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing4: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing5: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing6: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing7: "/static/images/myface_male_outting.jpg",
  grad_face_male_outing8: "/static/images/myface_male_outting.jpg",

  // ─── 5번째 졸업사진 좌표 매핑 (1~8번) ───
  female_outing1: "/static/images/myface_female.jpg",
  female_outing2: "/static/images/myface_female.jpg",
  female_outing3: "/static/images/myface_female.jpg",
  female_outing4: "/static/images/myface_female.jpg",
  female_outing5: "/static/images/myface_female.jpg",
  female_outing6: "/static/images/myface_female.jpg",
  female_outing7: "/static/images/myface_female.jpg",
  female_outing8: "/static/images/myface_female.jpg",
};

// 1. 현재 임원이 선택한 슬롯 정보를 저장할 전역 변수
let currentSelectedSlot = null;

// 2. 앨범 내 얼굴 슬롯을 클릭했을 때 실행할 함수 (선택 및 노란색 테두리 하이라이트 표시)
function selectExecutiveSlot(element, slotName) {
  // 기존에 선택된 슬롯이 있다면 하이라이트 제거
  if (currentSelectedSlot) {
    currentSelectedSlot.classList.remove("face-selected-highlight");
  }

  // 새로운 슬롯 선택 및 노란색 테두리 하이라이트 추가
  currentSelectedSlot = element;
  currentSelectedSlot.classList.add("face-selected-highlight");

  // UI 상단 패널의 텍스트 변경 (임원 모드일 때 엘리먼트가 존재하므로 방어 코드 추가)
  const displayPanel = document.getElementById("selectedSlotDisplay");
  if (displayPanel) {
    displayPanel.innerText = `선택된 슬롯: ${slotName}`;
  }
}

// 3. [📸 사진 선택하여 넣기] 버튼 클릭 시 확인창을 띄우고 파일 선택창을 열어주는 함수
function triggerFileInput() {
  if (!currentSelectedSlot) {
    alert("⚠️ 먼저 변경할 얼굴 슬롯을 클릭해 주세요!");
    return;
  }
  if (confirm("사진을 올리시겠습니까?")) {
    const uploader = document.getElementById("executiveSingleUploader");
    if (uploader) uploader.click();
  }
}

// 임원급 이상만 사진 단일 업로드 및 미리보기 핸들러
function handleExecutiveSingleUpload() {
  const uploader = document.getElementById("executiveSingleUploader");

  if (!uploader || uploader.files.length === 0) return;

  const file = uploader.files[0];

  // 업로드 도중 전역 currentSelectedSlot이 변경되는 상황 방지
  const selectedSlot = currentSelectedSlot;

  if (!file || !selectedSlot) {
    alert("사진을 적용할 슬롯을 먼저 선택해 주세요.");
    uploader.value = "";
    return;
  }

  // 허용할 이미지 MIME 타입
  const ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
  ];

  // 이미지 형식 검증
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    alert("JPG, PNG, WEBP, GIF 이미지만 업로드할 수 있습니다.");
    uploader.value = "";
    return;
  }

  // 파일 크기 제한: 5MB
  const MAX_FILE_SIZE = 5 * 1024 * 1024;

  if (file.size > MAX_FILE_SIZE) {
    alert("이미지는 5MB 이하만 업로드할 수 있습니다.");
    uploader.value = "";
    return;
  }

  // 슬롯 식별자 가져오기
  const slotClass = selectedSlot.getAttribute("data-slot-class");

  if (!slotClass) {
    alert("선택한 슬롯의 식별 정보를 찾을 수 없습니다.");
    uploader.value = "";
    return;
  }

  // 업로드 실패 시 복구하기 위해 기존 이미지 주소 저장
  const imgTag = selectedSlot.querySelector(".user-face");
  const previousImageUrl = imgTag ? imgTag.src : null;

  // 선택한 이미지 즉시 미리보기
  const reader = new FileReader();

  reader.onload = function (event) {
    if (imgTag) {
      imgTag.src = event.target.result;
    }
  };

  reader.onerror = function () {
    alert("이미지 파일을 읽는 중 오류가 발생했습니다.");
  };

  reader.readAsDataURL(file);

  // Flask 서버로 보낼 multipart/form-data 구성
  const formData = new FormData();

  formData.append("image", file);
  formData.append("slot_class", slotClass);

  fetch(uploadPhotoUrl, {
    method: "POST",

    // FormData 사용 시 Content-Type은 직접 지정하지 않음
    // 브라우저가 multipart boundary까지 자동으로 설정함
    body: formData,
  })
    .then(async (response) => {
      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error("서버 응답이 올바른 JSON 형식이 아닙니다.");
      }

      if (!response.ok) {
        throw new Error(
          data.message ||
            data.error ||
            `서버 요청에 실패했습니다. (${response.status})`,
        );
      }

      return data;
    })
    .then((data) => {
      if (data.status !== "success") {
        throw new Error(
          data.message || data.error || "서버에서 이미지 저장에 실패했습니다.",
        );
      }

      if (!data.uploaded_image_url) {
        throw new Error("서버에서 업로드된 이미지 주소를 반환하지 않았습니다.");
      }

      // 마스터 레지스트리 동기화
      savePhotoToSlot(slotClass, data.uploaded_image_url);

      // 임시 Base64 이미지에서 서버의 실제 이미지 주소로 확정
      if (imgTag) {
        imgTag.src = data.uploaded_image_url;
      }

      console.log(
        "[업로드 완료] Flask 서버 저장 및 마스터 레지스트리가 동기화되었습니다.",
      );
    })
    .catch((error) => {
      console.error("Upload Error:", error);

      // 서버 업로드 실패 시 기존 이미지로 복구
      if (imgTag && previousImageUrl) {
        imgTag.src = previousImageUrl;
      }

      alert(
        error.message ||
          "이미지 업로드 중 오류가 발생했습니다. 다시 시도해 주세요.",
      );
    })
    .finally(() => {
      // 동일한 파일을 다시 선택할 수 있도록 초기화
      uploader.value = "";
    });
}

// 📌 임원이 체크한 슬롯에 새 이미지 경로를 저장하고 화면을 바꾸는 함수
function savePhotoToSlot(slotClass, uploadedImagePath) {
  // 1. 레지스트리 데이터 갱신
  if (slotClass in executivePhotoRegistry) {
    executivePhotoRegistry[slotClass] = uploadedImagePath;
    console.log(`[경로 변경] ${slotClass} -> ${uploadedImagePath}`);
  }

  // 2. 화면 이미지 요소(src) 실시간 반영
  const slotImg = document.querySelector(
    `[data-slot-class="${slotClass}"] .user-face`,
  );
  if (slotImg) {
    slotImg.src = uploadedImagePath;
  } else {
    console.error(
      `[오류] data-slot-class="${slotClass}" 내부의 이미지를 찾을 수 없습니다.`,
    );
  }
}

// 💬 댓글 독립 작동 시스템 기능 함수 (Flask 연동)
function setupCommentSystem(inputId, btnId, listId, roomId) {
  const input = document.getElementById(inputId);
  const btn = document.getElementById(btnId);
  const list = document.getElementById(listId);

  // 필요한 HTML 요소가 없으면 종료
  if (!input || !btn || !list) {
    console.warn("댓글 시스템에 필요한 요소를 찾지 못했습니다.", {
      inputId,
      btnId,
      listId,
    });
    return;
  }

  let isSubmitting = false;

  async function addComment() {
    const text = input.value.trim();

    // 빈 댓글이나 중복 요청 방지
    if (!text || isSubmitting) return;

    isSubmitting = true;
    btn.disabled = true;

    try {
      const response = await fetch(getCommentsUrl(roomId), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: text,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "댓글 등록에 실패했습니다.");
      }

      if (data.status === "success") {
        const li = document.createElement("li");
        li.className = "comment-item";

        // 서버에서 돌려준 값을 사용
        li.textContent = data.comment.text;

        list.appendChild(li);

        input.value = "";
        input.focus();
      }
    } catch (error) {
      console.error("댓글 등록 오류:", error);
      alert(error.message);
    } finally {
      isSubmitting = false;
      btn.disabled = false;
    }
  }

  // 버튼 클릭으로 댓글 등록
  btn.addEventListener("click", addComment);

  // Enter 키로 댓글 등록
  input.addEventListener("keydown", (event) => {
    if (event.isComposing) return;

    if (event.key === "Enter") {
      event.preventDefault();
      addComment();
    }
  });
}

// =================================================================
// 3. 🌟 실제 화면에 존재하는 모든 앨범 댓글창(1번~5번) 기능 활성화
// =================================================================
setupCommentSystem("commentInput1", "submitBtn1", "commentList1", 1);
setupCommentSystem("commentInput2", "submitBtn2", "commentList2", 2);
setupCommentSystem("commentInput3", "submitBtn3", "commentList3", 3);
setupCommentSystem("commentInput4", "submitBtn4", "commentList4", 4);
setupCommentSystem("commentInput5", "submitBtn5", "commentList5", 5);

const photoRegistryData = document.getElementById("photoRegistryData");
if (photoRegistryData) {
  const savedPhotos = JSON.parse(photoRegistryData.textContent || "{}");
  Object.entries(savedPhotos).forEach(([slotClass, imagePath]) => {
    savePhotoToSlot(slotClass, imagePath);
  });
}

const DESIGN_BASE_WIDTH = 430;

function applyResponsiveFaceCoordinates() {
  const facesDataElement = document.getElementById("facesData");
  if (!facesDataElement) return;

  let facesData = {};
  try {
    facesData = JSON.parse(facesDataElement.textContent || "{}");
  } catch (e) {
    return;
  }

  const albumSections = document.querySelectorAll(".album-section");

  Object.entries(facesData).forEach(([albumNumber, coordinates]) => {
    const section = albumSections[Number(albumNumber) - 1];
    if (!section) return;

    const photoWrap = section.querySelector(".photo-wrap") || section;
    const currentWidth = photoWrap.offsetWidth || DESIGN_BASE_WIDTH;
    const scale = currentWidth / DESIGN_BASE_WIDTH;

    const faceSlots = section.querySelectorAll("[data-slot-class]");
    coordinates.forEach((coordinate) => {
      const slot = faceSlots[coordinate.grad_face_num - 1];
      if (!slot) return;

      const baseTop = parseFloat(coordinate.top);
      const baseLeft = parseFloat(coordinate.left);

      if (!isNaN(baseTop) && !isNaN(baseLeft)) {
        slot.dataset.baseTop = baseTop;
        slot.dataset.baseLeft = baseLeft;
        slot.style.top = `${Math.round(baseTop * scale)}px`;
        slot.style.left = `${Math.round(baseLeft * scale)}px`;
        slot.style.transform = `translate(-50%, -50%) scale(${scale})`;
      }
    });
  });
}

// -----------------------------------------------------------------
// 4. 🎯 얼굴 드래그 앤 드롭 위치 조정 기능 (터치 / 마우스 반응형 지원)
// -----------------------------------------------------------------
function enableFaceDragMode() {
  document.querySelectorAll("[data-slot-class]").forEach((slot) => {
    slot.style.cursor = "move";
    slot.style.touchAction = "none";

    slot.onpointerdown = (event) => {
      event.preventDefault();

      const section = slot.closest(".album-section");
      if (!section) return;

      const photoWrap = section.querySelector(".photo-wrap") || section;
      const currentWidth = photoWrap.offsetWidth || DESIGN_BASE_WIDTH;
      const scale = currentWidth / DESIGN_BASE_WIDTH;

      const sectionRect = section.getBoundingClientRect();
      const scaleX = sectionRect.width ? section.offsetWidth / sectionRect.width : 1;

      const startX = event.clientX;
      const startY = event.clientY;

      const currentLeft = parseFloat(slot.style.left) || 0;
      const currentTop = parseFloat(slot.style.top) || 0;

      if (slot.setPointerCapture) {
        try {
          slot.setPointerCapture(event.pointerId);
        } catch (e) {
          console.warn("setPointerCapture failed:", e);
        }
      }

      let lastBaseLeft = parseFloat(slot.dataset.baseLeft) || Math.round(currentLeft / (scale || 1));
      let lastBaseTop = parseFloat(slot.dataset.baseTop) || Math.round(currentTop / (scale || 1));

      slot.onpointermove = (moveEvent) => {
        const deltaX = (moveEvent.clientX - startX) * scaleX;
        const deltaY = (moveEvent.clientY - startY) * scaleX;

        const newCurrentLeft = currentLeft + deltaX;
        const newCurrentTop = currentTop + deltaY;

        slot.style.left = `${Math.round(newCurrentLeft)}px`;
        slot.style.top = `${Math.round(newCurrentTop)}px`;

        lastBaseLeft = Math.round(newCurrentLeft / (scale || 1));
        lastBaseTop = Math.round(newCurrentTop / (scale || 1));
      };

      slot.onpointerup = () => {
        slot.onpointermove = null;
        if (slot.releasePointerCapture && slot.hasPointerCapture && slot.hasPointerCapture(event.pointerId)) {
          try {
            slot.releasePointerCapture(event.pointerId);
          } catch (e) {}
        }

        slot.dataset.baseLeft = lastBaseLeft;
        slot.dataset.baseTop = lastBaseTop;

        console.log(
          slot.dataset.slotClass,
          "left:",
          `${lastBaseLeft}px`,
          "top:",
          `${lastBaseTop}px`
        );
      };
    };
  });

  console.log("얼굴 드래그 모드가 켜졌습니다.");
}

// 개발자 및 임원을 위한 전역 접근 제어
window.enableFaceDragMode = enableFaceDragMode;
window.applyResponsiveFaceCoordinates = applyResponsiveFaceCoordinates;

window.logAllFaceCoordinates = function () {
  const result = {};
  document.querySelectorAll(".album-section").forEach((section, idx) => {
    const albumId = idx + 1;
    result[albumId] = [];
    section.querySelectorAll("[data-slot-class]").forEach((slot, sIdx) => {
      const baseTop = slot.dataset.baseTop || parseFloat(slot.style.top) || 0;
      const baseLeft = slot.dataset.baseLeft || parseFloat(slot.style.left) || 0;
      result[albumId].push({
        grad_face_num: sIdx + 1,
        top: `${Math.round(baseTop)}px`,
        left: `${Math.round(baseLeft)}px`,
      });
    });
  });
  console.log("=== 현재 모든 얼굴 슬롯 좌표 (기준 430px) ===");
  console.log(JSON.stringify(result, null, 2));
  return result;
};

// DOM 준비 시 자동 활성화 (임원 드래그 방지: enableFaceDragMode 자동 실행 제외)
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    applyResponsiveFaceCoordinates();
  });
} else {
  applyResponsiveFaceCoordinates();
}

window.addEventListener("resize", applyResponsiveFaceCoordinates);
window.addEventListener("orientationchange", applyResponsiveFaceCoordinates);

