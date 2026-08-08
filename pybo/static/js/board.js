const boardScript = document.currentScript;
const boardUrl = boardScript.dataset.boardUrl;

document.addEventListener("DOMContentLoaded", () => {
  // 에디터 및 폼 관련
  const editor = document.getElementById("editor");
  const hiddenContent = document.getElementById("hiddenContent");
  // base.html의 로그아웃 form이 아니라 게시글 작성 form을 정확히 선택합니다.
  const form = document.getElementById("boardWriteForm");

  // 툴바 엘리먼트 (이벤트 위임을 위해 부모 컨테이너 선택)
  const toolbar = document.querySelector(".editor-toolbar");
  const fontSelect = toolbar?.querySelector("select:nth-of-type(1)");
  const sizeSelect = toolbar?.querySelector("select:nth-of-type(2)");

  // 태그 관련 엘리먼트
  const tagContainer = document.getElementById("tagContainer");
  const tagInput = document.getElementById("tagInput");
  const hiddenTags = document.getElementById("hiddenTags");
  let tags = [];

  // 파일 업로드 관련 엘리먼트
  const fileInputs = document.querySelectorAll(
    '.file-input-wrap input[type="file"]',
  );

  // 사용자의 마지막 커서 위치를 기억하기 위한 변수
  let savedRange = null;

  // 커서 위치를 저장하는 함수
  function saveSelection() {
    const sel = window.getSelection();
    if (sel.rangeCount > 0) {
      const range = sel.getRangeAt(0);
      // 커서가 에디터 내부에 있을 때만 저장
      if (editor && editor.contains(range.commonAncestorContainer)) {
        savedRange = range.cloneRange(); // 참조 꼬임 방지를 위한 스냅샷 복사
      }
    }
  }

  // 저장된 커서 위치를 다시 에디터로 복원하는 함수
  function restoreSelection() {
    if (savedRange) {
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
    }
  }

  /**
   * [개선] 프로 레벨의 안전한 서식 적용 함수
   * surroundContents의 한계를 extractContents와 insertNode의 조합으로 극복하여 태그 꼬임 에러를 원천 차단합니다.
   */
  function applyStyleToSelection(styleProperty, value) {
    restoreSelection(); // 버튼 클릭으로 풀린 커서 복원

    const sel = window.getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return; // 선택 영역이 없으면 무시

    const range = sel.getRangeAt(0);

    // 1. 스타일을 입힐 span 태그 생성
    const span = document.createElement("span");
    span.style[styleProperty] = value;

    // 2. 선택된 콘텐츠를 안전하게 잘라내어(extract) span 내부로 이동 (태그 깨짐 방지)
    const fragment = range.extractContents();
    span.appendChild(fragment);

    // 3. 원래 위치에 완성된 span 노드 삽입
    range.insertNode(span);

    // 4. 서식 적용 후 사용자가 드래그했던 영역을 다시 깔끔하게 선택해 줌
    sel.removeAllRanges();
    const newRange = document.createRange();
    newRange.selectNodeContents(span);
    sel.addRange(newRange);

    // 5. 변경된 최종 커서 상태 저장
    saveSelection();
  }

  // 사용자가 에디터에서 타이핑하거나 클릭할 때 커서 위치 기록
  if (editor) {
    editor.addEventListener("keyup", saveSelection);
    editor.addEventListener("click", saveSelection);
  }

  /* ==========================================================================
      [1] 에디터 툴바 기능 구현 (이벤트 위임 및 현대적 방식 적용)
     ========================================================================== */
  if (toolbar) {
    // [개선] 툴바 내부 클릭 시 포커스 탈취를 전역에서 차단 (mousedown 이벤트 가로채기)
    toolbar.addEventListener("mousedown", (e) => {
      // select 박스나 버튼 등을 누를 때 에디터 포커스가 풀리는 현상 방지
      e.preventDefault();
    });

    // 1. 폰트 변경 처리
    fontSelect?.addEventListener("change", () => {
      applyStyleToSelection("fontFamily", fontSelect.value);
    });

    // 2. 폰트 사이즈 변경 처리
    sizeSelect?.addEventListener("change", () => {
      applyStyleToSelection("fontSize", sizeSelect.value);
    });

    // 3. [개선] 이벤트 위임(Event Delegation)을 이용한 툴바 버튼 핸들링
    toolbar.addEventListener("click", (e) => {
      const btn = e.target.closest(".toolbar-btn");
      if (!btn) return; // 툴바의 빈 공간을 누른 경우는 무시 (꺼져)

      const style = btn.getAttribute("style") || "";
      const color = btn.style.color;

      if (style.includes("underline")) {
        applyStyleToSelection("textDecoration", "underline");
      } else if (color === "red" || style.includes("color: red")) {
        applyStyleToSelection("color", "#ef4444");
      } else {
        applyStyleToSelection("fontWeight", "bold");
      }
    });
  }

  /* ==========================================================================
      [2] 태그 시스템 기능 구현
     ========================================================================== */
  function renderTags() {
    if (!tagContainer || !tagInput) return;

    const existingItems = tagContainer.querySelectorAll(".tag-item");
    existingItems.forEach((item) => item.remove());

    tags.forEach((tag, index) => {
      const tagItem = document.createElement("div");
      tagItem.className = "tag-item";
      tagItem.append(document.createTextNode(`#${tag}`));
      const deleteButton = document.createElement("span");
      deleteButton.className = "tag-delete";
      deleteButton.dataset.index = String(index);
      deleteButton.textContent = "×";
      tagItem.appendChild(deleteButton);
      tagContainer.insertBefore(tagItem, tagInput);
    });

    if (hiddenTags) hiddenTags.value = tags.join(",");
  }

  function addTag(value) {
    const cleanedValue = value.replace(/,/g, "").trim();
    if (cleanedValue !== "" && !tags.includes(cleanedValue)) {
      tags.push(cleanedValue);
      renderTags();
    }
    if (tagInput) tagInput.value = "";
  }

  if (tagInput) {
    tagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addTag(tagInput.value);
      }
    });

    tagInput.addEventListener("input", () => {
      if (tagInput.value.includes(",")) {
        addTag(tagInput.value);
      }
    });
  }

  if (tagContainer) {
    tagContainer.addEventListener("click", (e) => {
      if (e.target.classList.contains("tag-delete")) {
        const indexToRemove = parseInt(e.target.getAttribute("data-index"), 10);
        tags.splice(indexToRemove, 1);
        renderTags();
        if (tagInput) tagInput.focus();
      } else {
        if (tagInput) tagInput.focus();
      }
    });
  }

  /* ==========================================================================
      [5] 이미지 파일 첨부 시 에디터 연동 프리뷰 구현
     ========================================================================== */
  if (fileInputs.length > 0 && editor) {
    fileInputs.forEach((input) => {
      input.addEventListener("change", (e) => {
        const file = e.target.files[0];

        if (file && file.type.match("image.*")) {
          const reader = new FileReader();

          reader.onload = (event) => {
            const wrapper = document.createElement("div");
            wrapper.innerHTML = `
              <br>
              <img src="${event.target.result}" style="max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0;" alt="첨부 이미지">
              <br>
            `;

            const fragment = document.createDocumentFragment();
            while (wrapper.firstChild) {
              fragment.appendChild(wrapper.firstChild);
            }

            editor.focus();

            const sel = window.getSelection();
            if (savedRange) {
              sel.removeAllRanges();
              sel.addRange(savedRange);

              savedRange.insertNode(fragment);
              savedRange.collapse(false);
            } else {
              editor.appendChild(fragment);
            }

            saveSelection();
          };

          reader.readAsDataURL(file);
        }
      });
    });
  }

  /* ==========================================================================
      [3] 폼 전송 시 동기화 처리
     ========================================================================== */
  if (form) {
    form.addEventListener("submit", (e) => {
      if (tagInput && tagInput.value.trim() !== "") {
        addTag(tagInput.value);
      }

      if (hiddenContent && editor) {
        const contentCopy = editor.cloneNode(true);
        contentCopy.querySelectorAll("img").forEach((image) => {
          image.replaceWith(document.createTextNode("[첨부 이미지]"));
        });
        hiddenContent.value = contentCopy.innerHTML;

        if (
          editor.textContent.trim() === "" &&
          editor.querySelectorAll("img").length === 0
        ) {
          alert("내용을 입력해주세요.");
          e.preventDefault();
        }
      }
    });
  }

  /* ==========================================================================
  [4] 태그 클릭 시 관련 페이지 이동 기능
========================================================================== */
  const tagLinks = document.querySelectorAll(".tag-link-item");

  // tagLinks가 존재할 때만 loop를 돌도록 안전하게 감싸거나, querySelectorAll은 빈 노드(NodeList)를 반환하므로 그냥 두어도 무방하지만
  // 아래와 같이 조건문을 명시해주면 매끄럽습니다.
  if (tagLinks.length > 0) {
    tagLinks.forEach((tagItem) => {
      tagItem.addEventListener("click", (e) => {
        const tagName = e.currentTarget.getAttribute("data-tag");

        if (tagName) {
          const encodedTag = encodeURIComponent(tagName);
          location.href = `${boardUrl}?search=${encodedTag}`;
        }
      });
    });
  }

}); // <-- DOMContentLoaded 닫는 중괄호
