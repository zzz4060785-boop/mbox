const schoolInput = document.getElementById("schoolInput");
const schoolList = document.getElementById("schoolList");
const currentSchoolType = document.getElementById("currentSchoolType");
const currentEnterYear = document.getElementById("currentEnterYear");
const currentMajor = document.getElementById("currentMajor");
const graduateSchoolInput = document.getElementById("graduateSchoolInput");
const graduateSchoolList = document.getElementById("graduateSchoolList");
const graduateSchoolType = document.getElementById("graduateSchoolType");
const graduateYear = document.getElementById("graduateYear");
const currentSchoolButton = document.getElementById("enterCurrentSchoolBtn");
const graduateSchoolButton = document.getElementById(
  "enterGraduateSchoolBtn",
);
const schoolMessage = document.getElementById("schoolMessage");
const scriptElement = document.currentScript;
const albumUrl = scriptElement.dataset.albumUrl;
const saveSchoolUrl = scriptElement.dataset.saveSchoolUrl;
const schoolSearchUrl = scriptElement.dataset.schoolSearchUrl;
/*
 * ================= 학교 직접 입력 모달 기능 시작 =================
 * 모달을 완전히 삭제할 때는 아래의 모달 요소 변수들과
 * 파일 하단의 "학교 직접 입력 모달 동작" 구간을 함께 삭제하세요.
 */
const schoolModal = document.getElementById("schoolModal");
const openSchoolModalButton = document.getElementById("openSchoolModalBtn");
const modalSchoolName = document.getElementById("modalSchoolName");
const modalSchoolList = document.getElementById("modalSchoolList");
const modalSchoolType = document.getElementById("modalSchoolType");
const modalSchoolYear = document.getElementById("modalSchoolYear");
const modalSchoolMajor = document.getElementById("modalSchoolMajor");
const schoolModalMessage = document.getElementById("schoolModalMessage");
const saveModalSchoolButton = document.getElementById("saveModalSchoolBtn");
/* ================== 학교 직접 입력 모달 요소 끝 ================== */

function setupAutocomplete(inputElement, listElement, typeElement) {
  let timerId;
  let requestController;

  inputElement.addEventListener("input", () => {
    const keyword = inputElement.value.trim();
    listElement.replaceChildren();
    window.clearTimeout(timerId);
    requestController?.abort();

    if (keyword.length < 2) return;

    timerId = window.setTimeout(async () => {
      requestController = new AbortController();
      const query = new URLSearchParams({
        q: keyword,
        type: typeElement.value,
      });

      try {
        const response = await fetch(`${schoolSearchUrl}?${query}`, {
          signal: requestController.signal,
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || "학교를 검색하지 못했습니다.");
        }

        result.schools.forEach((school) => {
          const item = document.createElement("li");
          item.textContent = school.address
            ? `${school.name} · ${school.address}`
            : school.name;
          item.addEventListener("click", () => {
            inputElement.value = school.name;
            if (!typeElement.value && school.type) {
              typeElement.value = school.type;
            }
            listElement.replaceChildren();
          });
          listElement.appendChild(item);
        });
      } catch (error) {
        if (error.name !== "AbortError") {
          listElement.replaceChildren();
        }
      }
    }, 300);
  });
}

function populateYearSelect(selectElement, defaultText) {
  const currentYear = new Date().getFullYear();
  selectElement.replaceChildren(new Option(defaultText, ""));

  for (let year = currentYear; year >= 1970; year -= 1) {
    selectElement.appendChild(new Option(`${year}년`, String(year)));
  }
}

async function enterAlbum(
  schoolName,
  schoolType,
  year,
  major = "",
  messageElement = schoolMessage,
  spaceName = "학교 공간",
) {
  const trimmedSchool = schoolName.trim();

  if (!trimmedSchool || !schoolType || !year) {
    messageElement.textContent =
      "학교명, 학교 구분, 연도를 모두 선택해 주세요.";
    return;
  }

  const schoolData = {
    school: trimmedSchool,
    type: schoolType,
    year,
  };

  if (major.trim()) {
    schoolData.major = major.trim();
  }

  messageElement.textContent = "학교 정보를 저장하는 중입니다.";

  try {
    const response = await fetch(saveSchoolUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(schoolData),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "학교 정보를 저장하지 못했습니다.");
    }

    /*
     * [학교 선택 완료 알림 문구 수정 위치]
     * 아래 alert 안의 문장을 바꾸면 학교 저장 후 안내 문구가 바뀝니다.
     * 알림창이 필요 없으면 window.alert(...) 부분만 삭제하세요.
     * 학교 저장에 성공했을 때 한 번만 표시됩니다.
     */
    window.alert(
      `${trimmedSchool} ${spaceName} 선택이 완료되었습니다.\n\n` +
        "내 정보란에서 관심 학교를 한 곳 더 추가할 수 있습니다.",
    );

    window.location.href = result.redirect_url || albumUrl;
  } catch (error) {
    messageElement.textContent = error.message;
    alert(`⚠️ ${error.message}`);
  }
}

setupAutocomplete(schoolInput, schoolList, currentSchoolType);
setupAutocomplete(
  graduateSchoolInput,
  graduateSchoolList,
  graduateSchoolType,
);
setupAutocomplete(modalSchoolName, modalSchoolList, modalSchoolType);
populateYearSelect(currentEnterYear, "입학년도 선택");
populateYearSelect(graduateYear, "졸업년도 선택");

/*
 * ================= 학교 직접 입력 모달 동작 시작 =================
 * "연도 선택"을 바꾸면 모달의 연도 기본 안내 문구가 변경됩니다.
 * 저장 전 검사 문구와 저장 중 문구도 이 구간에서 수정할 수 있습니다.
 * 모달을 삭제할 때는 이 시작 주석부터 아래 끝 주석까지 삭제하세요.
 */
populateYearSelect(modalSchoolYear, "연도 선택");

function openSchoolModal() {
  schoolModal.hidden = false;
  document.body.classList.add("school-modal-open");
  schoolModalMessage.textContent = "";
  modalSchoolName.focus();
}

function closeSchoolModal() {
    schoolModal.hidden = true;
    document.body.classList.remove("school-modal-open");
    modalSchoolList.replaceChildren();
}

openSchoolModalButton.addEventListener("click", openSchoolModal);
schoolInput?.addEventListener("click", openSchoolModal);
graduateSchoolInput?.addEventListener("click", openSchoolModal);

document.querySelectorAll("[data-close-school-modal]").forEach((button) => {
  button.addEventListener("click", closeSchoolModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !schoolModal.hidden) {
    closeSchoolModal();
  }
});

saveModalSchoolButton.addEventListener("click", async () => {
  const schoolName = modalSchoolName.value.trim();
  const schoolType = modalSchoolType.value;
  const schoolYear = modalSchoolYear.value;

  if (!schoolName || !schoolType || !schoolYear) {
    schoolModalMessage.textContent =
      "학교명, 학교 구분, 연도를 모두 입력해 주세요.";
    return;
  }

  schoolModalMessage.textContent = "학교 정보를 저장하는 중입니다.";
  saveModalSchoolButton.disabled = true;

  try {
    await enterAlbum(
      schoolName,
      schoolType,
      schoolYear,
      modalSchoolMajor.value,
      schoolModalMessage,
      "학교 공간",
    );
  } finally {
    saveModalSchoolButton.disabled = false;
  }
});
/* ================== 학교 직접 입력 모달 동작 끝 ================== */

currentSchoolButton.addEventListener("click", () => {
  enterAlbum(
    schoolInput.value,
    currentSchoolType.value,
    currentEnterYear.value,
    currentMajor.value,
    schoolMessage,
    "재학생 공간",
  );
});

graduateSchoolButton.addEventListener("click", () => {
  enterAlbum(
    graduateSchoolInput.value,
    graduateSchoolType.value,
    graduateYear.value,
    "",
    schoolMessage,
    "졸업생 공간",
  );
});
