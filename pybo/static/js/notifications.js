const notificationState = {
  items: [],
  unreadCount: 0,
};

async function notificationRequest(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
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
    list.appendChild(button);
  });
}

async function loadNotifications() {
  try {
    const data = await notificationRequest("/api/notifications");
    notificationState.items = data.notifications;
    notificationState.unreadCount = data.unread_count;
    updateNotificationBadge();
    renderNotifications();
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

async function markAllNotificationsRead() {
  try {
    await notificationRequest("/api/notifications/read-all", {
      method: "POST",
    });
    notificationState.unreadCount = 0;
    notificationState.items.forEach((item) => {
      item.is_read = true;
    });
    updateNotificationBadge();
    renderNotifications();
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
  readAll.addEventListener("click", markAllNotificationsRead);
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
