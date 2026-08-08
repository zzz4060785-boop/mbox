(() => {
  const root = document.querySelector(".admin-dashboard");
  if (!root) return;

  const byId = (id) => document.getElementById(id);
  const rows = byId("onlineUserRows");
  const empty = byId("onlineEmpty");
  const refreshButton = byId("refreshOnlineUsers");
  const replyList = byId("adminReplyList");
  const replyEmpty = byId("replyEmpty");
  const replyBadge = byId("replyBadge");
  const broadcastForm = byId("broadcastForm");
  const broadcastContent = byId("broadcastContent");
  const backButton = byId("adminBackButton");
  let timer = null;

  const formatDateTime = (value) =>
    new Intl.DateTimeFormat("ko-KR", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));

  const appendCell = (row, className, text = "") => {
    const cell = document.createElement("td");
    cell.className = className;
    cell.textContent = text;
    row.appendChild(cell);
    return cell;
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(url, {
      ...options,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!response.ok || data.success === false) throw new Error(data.message || "요청에 실패했습니다.");
    return data;
  };

  backButton.addEventListener("click", () => {
    if (window.history.length > 1 && document.referrer.startsWith(window.location.origin)) {
      window.history.back();
      return;
    }
    window.location.href = backButton.dataset.fallbackUrl;
  });

  const renderOnlineUsers = (users) => {
    rows.replaceChildren();
    empty.hidden = users.length > 0;
    users.forEach((user) => {
      const row = document.createElement("tr");
      const member = appendCell(row, "admin-member");
      const name = document.createElement("strong");
      const email = document.createElement("span");
      name.textContent = user.username;
      email.textContent = user.email;
      member.append(name, email);
      appendCell(row, "admin-school", user.school_name);
      appendCell(row, "admin-last-active", formatDateTime(user.last_active_at));
      const state = appendCell(row, "admin-state");
      const badge = document.createElement("span");
      badge.textContent = "접속 중";
      state.appendChild(badge);
      rows.appendChild(row);
    });
  };

  const refreshOnline = async () => {
    refreshButton.disabled = true;
    byId("refreshStatus").textContent = "접속 현황을 갱신하는 중입니다.";
    try {
      const data = await requestJson(root.dataset.onlineUrl);
      byId("onlineCount").textContent = data.online_count.toLocaleString("ko-KR");
      byId("todayLoginCount").textContent = data.logged_in_today.toLocaleString("ko-KR");
      byId("totalUserCount").textContent = data.total_users.toLocaleString("ko-KR");
      renderOnlineUsers(data.users);
      byId("refreshStatus").textContent = `${formatDateTime(data.generated_at)} 기준 · 10초마다 자동 갱신`;
    } catch (error) {
      byId("refreshStatus").textContent = error.message;
    } finally {
      refreshButton.disabled = false;
    }
  };

  const replyForm = (message) => {
    const form = document.createElement("form");
    form.className = "admin-inline-reply";
    const input = document.createElement("textarea");
    input.maxLength = 1000;
    input.rows = 3;
    input.placeholder = `${message.sender}님에게 답장하기`;
    input.required = true;
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "admin-primary-button";
    submit.textContent = "답장 보내기";
    const status = document.createElement("p");
    status.className = "admin-form-status";
    form.append(input, submit, status);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submit.disabled = true;
      try {
        const data = await requestJson(root.dataset.replyUrl, {
          method: "POST",
          body: JSON.stringify({ receiver_id: message.sender_id, content: input.value.trim() }),
        });
        input.value = "";
        status.textContent = data.message;
        status.className = "admin-form-status is-success";
      } catch (error) {
        status.textContent = error.message;
        status.className = "admin-form-status is-error";
      } finally {
        submit.disabled = false;
      }
    });
    return form;
  };

  const renderReplies = (messages) => {
    replyList.replaceChildren();
    replyEmpty.hidden = messages.length > 0;
    messages.forEach((message) => {
      const card = document.createElement("article");
      card.className = `admin-reply-card${message.is_read ? "" : " is-unread"}`;
      const header = document.createElement("header");
      const sender = document.createElement("div");
      const name = document.createElement("strong");
      const email = document.createElement("span");
      const time = document.createElement("time");
      name.textContent = message.sender;
      email.textContent = message.sender_email;
      sender.append(name, email);
      time.dateTime = message.created_at;
      time.textContent = formatDateTime(message.created_at);
      header.append(sender, time);
      const content = document.createElement("p");
      content.className = "admin-reply-content";
      content.textContent = message.content;
      card.append(header, content, replyForm(message));
      replyList.appendChild(card);
    });
  };

  const refreshReplies = async () => {
    try {
      const data = await requestJson(root.dataset.repliesUrl);
      renderReplies(data.messages);
      replyBadge.textContent = data.unread_count;
      replyBadge.hidden = data.unread_count === 0;
      byId("replyStatus").textContent = `최근 답변 ${data.messages.length.toLocaleString("ko-KR")}건`;
    } catch (error) {
      byId("replyStatus").textContent = error.message;
    }
  };

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("is-active", item === button));
      document.querySelectorAll("[data-panel]").forEach((panel) => {
        const active = panel.dataset.panel === button.dataset.tab;
        panel.hidden = !active;
        panel.classList.toggle("is-active", active);
      });
      if (button.dataset.tab === "replies") refreshReplies();
    });
  });

  broadcastContent.addEventListener("input", () => {
    byId("broadcastLength").textContent = `${broadcastContent.value.length} / 1000`;
  });
  broadcastForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = broadcastForm.querySelector("button[type='submit']");
    submit.disabled = true;
    try {
      const data = await requestJson(root.dataset.broadcastUrl, {
        method: "POST",
        body: JSON.stringify({ content: broadcastContent.value.trim() }),
      });
      broadcastContent.value = "";
      byId("broadcastLength").textContent = "0 / 1000";
      byId("broadcastStatus").textContent = data.message;
      byId("broadcastStatus").className = "admin-form-status is-success";
    } catch (error) {
      byId("broadcastStatus").textContent = error.message;
      byId("broadcastStatus").className = "admin-form-status is-error";
    } finally {
      submit.disabled = false;
    }
  });

  refreshButton.addEventListener("click", refreshOnline);
  byId("refreshReplies").addEventListener("click", refreshReplies);
  refreshOnline();
  refreshReplies();
  timer = window.setInterval(() => {
    refreshOnline();
    refreshReplies();
  }, 10000);
  window.addEventListener("pagehide", () => window.clearInterval(timer), { once: true });
})();
