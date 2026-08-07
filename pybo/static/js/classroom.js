window.FRIENDARY_SHARED_CLASSROOM = true;

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(location.search);
  let roomId = Number(params.get("room")) || null;
  const legacyTargetId = Number(params.get("chat_user")) || null;
  let roomState = null;
  let lastMessageId = 0;
  let pollTimer = null;
  const bubbleTimers = new Map();
  const status = document.getElementById("myHomeStatus");
  const targetName = document.getElementById("chatTargetName");
  const input = document.getElementById("classroomChatInput");
  const sendButton = document.getElementById("classroomChatSendBtn");
  const leaveButton = document.getElementById("classroomLeaveBtn");
  const inviteButton = document.getElementById("classroomInviteModalBtn");
  const inviteModal = document.getElementById("classroomInviteModal");
  const inviteList = document.getElementById("classroomInviteList");

  async function request(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "교실 요청을 처리하지 못했습니다.");
    return data;
  }

  function showBubble(slot, text) {
    const bubble = document.getElementById(`speechBubble${slot}`);
    if (!bubble) return;
    bubble.textContent = text;
    bubble.hidden = false;
    bubble.style.display = "block";
    clearTimeout(bubbleTimers.get(slot));
    bubbleTimers.set(slot, setTimeout(() => {
      bubble.hidden = true;
      bubble.style.display = "none";
    }, 5500));
  }

  function renderParticipants(room) {
    roomState = room;
    const bySlot = new Map(room.participants.map((person) => [person.slot, person]));
    for (let slot = 1; slot <= 8; slot += 1) {
      const element = document.getElementById(`avatarSlot${slot}`);
      if (!element) continue;
      const person = bySlot.get(slot);
      element.hidden = !person;
      if (!person) continue;
      element.dataset.userId = String(person.user_id);
      const name = element.querySelector(".avatar-name-tag");
      if (name) name.textContent = `${person.username}${person.is_me ? " (나)" : person.joined ? "" : " (초대 중)"}`;
      let avatar = element.querySelector("img");
      if (!avatar) {
        avatar = document.createElement("img");
        element.appendChild(avatar);
      }
      avatar.src = person.avatar_url;
      avatar.alt = `${person.username} 아바타`;
      element.classList.toggle("is-invited", !person.joined);
    }
    targetName.textContent = `${room.participants.length}/${room.capacity}명`;
    inviteButton.hidden = !room.is_owner || room.participants.length >= room.capacity;
    leaveButton.hidden = false;
  }

  async function refreshRoom() {
    if (!roomId) return;
    const data = await request(`/api/social/classroom/${roomId}`);
    renderParticipants(data.room);
  }

  async function refreshMessages() {
    if (!roomId || !roomState) return;
    const data = await request(`/api/social/classroom/${roomId}/messages?after=${lastMessageId}`);
    for (const message of data.messages) {
      lastMessageId = Math.max(lastMessageId, message.id);
      const person = roomState.participants.find((item) => item.user_id === message.sender_id);
      if (person) showBubble(person.slot, message.content);
    }
  }

  async function enterRoom(id) {
    roomId = Number(id);
    const data = await request(`/api/social/classroom/${roomId}/join`, { method: "POST" });
    renderParticipants(data.room);
    history.replaceState({}, document.title, `/my-home?room=${roomId}`);
    status.textContent = "같은 교실에 입장했습니다. 아바타 말풍선으로 대화해 보세요.";
    await refreshMessages();
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        await refreshRoom();
        await refreshMessages();
      } catch (error) {
        status.textContent = error.message;
      }
    }, 2500);
  }

  async function startWithFriend(targetId) {
    const data = await request("/api/social/classroom/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_id: targetId }),
    });
    await enterRoom(data.room_id);
  }

  async function sendMessage() {
    const content = input.value.trim();
    if (!roomId) {
      status.textContent = "먼저 접속 중인 1촌을 교실로 초대해 주세요.";
      return;
    }
    if (!content) return;
    sendButton.disabled = true;
    try {
      const data = await request(`/api/social/classroom/${roomId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      input.value = "";
      lastMessageId = Math.max(lastMessageId, data.message_id);
      const me = roomState.participants.find((item) => item.is_me);
      if (me) showBubble(me.slot, content);
    } catch (error) {
      status.textContent = error.message;
    } finally {
      sendButton.disabled = false;
      input.focus();
    }
  }

  sendButton?.addEventListener("click", sendMessage);
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.isComposing) sendMessage();
  });
  leaveButton?.addEventListener("click", async () => {
    if (!roomId) return;
    try {
      await request(`/api/social/classroom/${roomId}/leave`, { method: "POST" });
      clearInterval(pollTimer);
      location.href = "/my-home";
    } catch (error) {
      status.textContent = error.message;
    }
  });

  function closeInviteModal() {
    if (inviteModal) inviteModal.hidden = true;
  }
  document.getElementById("classroomInviteCloseBtn")?.addEventListener("click", closeInviteModal);
  document.getElementById("classroomInviteCloseBackdrop")?.addEventListener("click", closeInviteModal);

  inviteButton?.addEventListener("click", async () => {
    inviteModal.hidden = false;
    inviteList.innerHTML = "<p>접속 중인 1촌을 확인하는 중...</p>";
    try {
      const data = await request("/api/social/presence", { method: "POST" });
      const currentIds = new Set((roomState?.participants || []).map((item) => item.user_id));
      const friends = data.friends.filter((friend) => !currentIds.has(friend.user_id));
      if (!friends.length) {
        inviteList.innerHTML = "<p>추가로 초대할 수 있는 접속 중인 1촌이 없습니다.</p>";
        return;
      }
      inviteList.replaceChildren();
      friends.forEach((friend) => {
        const row = document.createElement("div");
        row.className = "classroom-invite-item";
        const label = document.createElement("strong");
        label.textContent = friend.username;
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "📢 초대하기";
        button.addEventListener("click", async () => {
          button.disabled = true;
          try {
            if (!roomId) await startWithFriend(friend.user_id);
            else {
              await request(`/api/social/classroom/${roomId}/invite`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_id: friend.user_id }),
              });
              await refreshRoom();
            }
            closeInviteModal();
            status.textContent = `${friend.username}님에게 교실 초대를 보냈습니다.`;
          } catch (error) {
            status.textContent = error.message;
            button.disabled = false;
          }
        });
        row.append(label, button);
        inviteList.appendChild(row);
      });
    } catch (error) {
      inviteList.textContent = error.message;
    }
  });

  if (roomId) enterRoom(roomId).catch((error) => { status.textContent = error.message; });
  else if (legacyTargetId) startWithFriend(legacyTargetId).catch((error) => { status.textContent = error.message; });
  else {
    targetName.textContent = "교실 상대 선택 안 됨";
    leaveButton.hidden = true;
  }
});
