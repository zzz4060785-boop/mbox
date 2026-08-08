const notificationState = {
  items: [],
  unreadCount: 0,
  selectedIds: new Set(),
};

async function notificationRequest(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    throw new Error("알림을 불러오지 못했습니다.");
  }
  return response.json();
}

function updateNotificationBadge() {
  const badge = document.getElementById("notificationBadge");
  const count = notificationState.unreadCount;
  badge.textContent = count > 99 ? "99+" : String(count);
  badge.hidden = count === 0;
}

function renderNotifications() {
  const list = document.getElementById("notificationList");
  list.replaceChildren();

  if (!notificationState.items.length) {
    const empty = document.createElement("p");
    empty.className = "notification-empty";
    empty.textContent = "새 알림이 없습니다.";
    list.appendChild(empty);
    return;
  }

  notificationState.items.forEach((item) => {
    const row = document.createElement("div");
    row.className = `notification-row${item.is_read ? "" : " unread"}`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "notification-checkbox";
    checkbox.checked = notificationState.selectedIds.has(item.id);
    checkbox.setAttribute("aria-label", `${item.title} 삭제 선택`);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) notificationState.selectedIds.add(item.id);
      else notificationState.selectedIds.delete(item.id);
    });

    const button = document.createElement("button");
    button.type = "button";
    button.className = `notification-item${item.is_read ? "" : " unread"}`;
    button.addEventListener("click", () => openNotification(item));

    const title = document.createElement("strong");
    title.textContent = item.title;
    const message = document.createElement("span");
    message.textContent = item.message;
    const time = document.createElement("time");
    time.dateTime = item.created_at;
    time.textContent = item.created_at.replace("T", " ");

    button.append(title, message, time);
    row.append(checkbox, button);
    list.appendChild(row);
  });
}

function closeClassroomSummonModal() {
  const modal = document.getElementById("classroomSummonModal");
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("friendary-modal-open");
}

function showClassroomSummonModal(item) {
  let modal = document.getElementById("classroomSummonModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "classroomSummonModal";
    modal.className = "classroom-summon-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="classroom-summon-backdrop" data-summon-dismiss></div>
      <section class="classroom-summon-box" role="dialog" aria-modal="true" aria-labelledby="classroomSummonTitle">
        <div class="classroom-summon-icon" aria-hidden="true">📢</div>
        <h2 id="classroomSummonTitle">내 교실로 초대</h2>
        <p id="classroomSummonMessage"></p>
        <div class="classroom-summon-actions">
          <button type="button" class="classroom-summon-later" data-summon-dismiss>나중에</button>
          <button type="button" class="classroom-summon-enter">교실 입장</button>
        </div>
      </section>`;
    modal.querySelectorAll("[data-summon-dismiss]").forEach((element) => {
      element.addEventListener("click", closeClassroomSummonModal);
    });
    document.body.appendChild(modal);
  }

  modal.querySelector("#classroomSummonMessage").textContent = item.message;
  modal.querySelector(".classroom-summon-enter").onclick = () => openNotification(item);
  modal.hidden = false;
  document.body.classList.add("friendary-modal-open");
  modal.querySelector(".classroom-summon-enter").focus();
}

function showNewestClassroomSummon() {
  const invite = notificationState.items.find((item) =>
    item.kind === "classroom_invite"
    && !item.is_read
    && sessionStorage.getItem(`classroom-summon-shown-${item.id}`) !== "1"
  );
  const existingModal = document.getElementById("classroomSummonModal");
  if (!invite || (existingModal && !existingModal.hidden)) return;
  sessionStorage.setItem(`classroom-summon-shown-${invite.id}`, "1");
  showClassroomSummonModal(invite);
}

async function loadNotifications() {
  try {
    const data = await notificationRequest("/api/notifications");
    notificationState.items = data.notifications;
    const availableIds = new Set(data.notifications.map((item) => item.id));
    notificationState.selectedIds = new Set(
      [...notificationState.selectedIds].filter((id) => availableIds.has(id)),
    );
    notificationState.unreadCount = data.unread_count;
    updateNotificationBadge();
    renderNotifications();
    showNewestClassroomSummon();
  } catch (_) {
    // 일시적인 알림 조회 실패가 다른 화면 기능을 막지 않게 합니다.
  }
}

async function openNotification(item) {
  try {
    if (!item.is_read) {
      await notificationRequest(`/api/notifications/${item.id}/read`, {
        method: "POST",
      });
    }
  } finally {
    window.location.href = item.target_url;
  }
}

function closeNotificationDeleteModal() {
  const modal = document.getElementById("notificationDeleteModal");
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("friendary-modal-open");
}

function showNotificationDeleteModal() {
  let modal = document.getElementById("notificationDeleteModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "notificationDeleteModal";
    modal.className = "notification-delete-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="notification-delete-backdrop" data-notification-delete-close></div>
      <section class="notification-delete-box" role="dialog" aria-modal="true" aria-labelledby="notificationDeleteTitle">
        <div class="notification-delete-icon" aria-hidden="true">🗑️</div>
        <h2 id="notificationDeleteTitle">메시지를 삭제할까요?</h2>
        <p class="notification-delete-message"></p>
        <small>삭제하지 않은 메시지도 90일이 지나면 자동으로 삭제됩니다.</small>
        <div class="notification-delete-actions">
          <button type="button" class="notification-delete-cancel" data-notification-delete-close>취소</button>
          <button type="button" class="notification-delete-confirm">삭제</button>
        </div>
      </section>`;
    modal.querySelectorAll("[data-notification-delete-close]").forEach((element) => {
      element.addEventListener("click", closeNotificationDeleteModal);
    });
    document.body.appendChild(modal);
  }

  const count = notificationState.selectedIds.size;
  const confirmButton = modal.querySelector(".notification-delete-confirm");
  modal.querySelector(".notification-delete-message").textContent = count
    ? `체크한 메시지 ${count}개가 전부 삭제돼요. 체크하지 않은 메시지는 삭제되지 않아요.`
    : "삭제할 메시지를 먼저 체크해 주세요. 체크하지 않은 메시지는 삭제되지 않아요.";
  confirmButton.disabled = count === 0;
  confirmButton.onclick = deleteSelectedNotifications;
  modal.hidden = false;
  document.body.classList.add("friendary-modal-open");
  (count ? confirmButton : modal.querySelector(".notification-delete-cancel")).focus();
}

async function deleteSelectedNotifications() {
  const ids = [...notificationState.selectedIds];
  if (!ids.length) return;
  try {
    const data = await notificationRequest("/api/notifications", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    const deletedIds = new Set(ids);
    notificationState.items = notificationState.items.filter(
      (item) => !deletedIds.has(item.id),
    );
    notificationState.selectedIds.clear();
    notificationState.unreadCount = data.unread_count;
    updateNotificationBadge();
    renderNotifications();
    closeNotificationDeleteModal();
  } catch (_) {
    // 다음 자동 조회 때 서버 상태를 다시 반영합니다.
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const boardSlot = document.getElementById("boardNotificationSlot");
  const center = document.getElementById("notificationCenter");
  if (boardSlot && center) {
    boardSlot.appendChild(center);
  }

  const toggle = document.getElementById("notificationToggle");
  const panel = document.getElementById("notificationPanel");
  const readAll = document.getElementById("notificationReadAll");

  toggle.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) loadNotifications();
  });
  readAll.addEventListener("click", showNotificationDeleteModal);
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#notificationCenter")) {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadNotifications();
  });

  loadNotifications();
  window.setInterval(loadNotifications, 8000);
});
