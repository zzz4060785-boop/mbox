/* 실제 DB와 연결된 개인 앨범·1촌·쪽지 기능 */
const mainAlbumScript = document.currentScript;
const currentUserId = Number(mainAlbumScript.dataset.currentUserId);
const currentUsername = mainAlbumScript.dataset.currentUsername;
const albumQuery = new URLSearchParams(window.location.search);
const userSchool = albumQuery.get("school") || "강남고등학교";
let currentReplyTargetId = null;
let currentReplyTargetName = "";
let selectedProfileUserId = null;
let selectedProfileUsername = "";
let currentConnectionPage = 1;

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value ?? "";
  return element.innerHTML;
}

function renderTaggedText(value) {
  const safeText = escapeHtml(value);
  return safeText.replace(
    /(^|[^\w가-힣])#([0-9A-Za-z가-힣_]{1,50})/g,
    (_, prefix, tag) =>
      `${prefix}<a class="hashtag-link" href="/tags/${encodeURIComponent(tag)}">#${tag}</a>`,
  );
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(data.message || "요청을 처리하지 못했습니다.");
  return data;
}

function closePhotoLightbox() {
  const lightbox = document.getElementById("photoLightbox");
  if (!lightbox) return;
  lightbox.hidden = true;
  lightbox.style.display = "none";
  lightbox.querySelector("img")?.removeAttribute("src");
  document.body.classList.remove("photo-lightbox-open");
}

function openPhotoLightbox(sourceImage) {
  let lightbox = document.getElementById("photoLightbox");
  if (!lightbox) {
    lightbox = document.createElement("div");
    lightbox.id = "photoLightbox";
    lightbox.className = "photo-lightbox";
    lightbox.hidden = true;
    lightbox.setAttribute("role", "dialog");
    lightbox.setAttribute("aria-modal", "true");
    lightbox.setAttribute("aria-label", "사진 확대 보기");
    lightbox.innerHTML = `
      <button type="button" class="photo-lightbox-close" aria-label="닫기">&times;</button>
      <img alt="확대된 앨범 사진">
    `;
    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox || event.target.closest(".photo-lightbox-close")) {
        closePhotoLightbox();
      }
    });
    document.body.appendChild(lightbox);
  }

  const enlargedImage = lightbox.querySelector("img");
  enlargedImage.src = sourceImage.currentSrc || sourceImage.src;
  enlargedImage.alt = sourceImage.alt;
  lightbox.hidden = false;
  lightbox.style.display = "grid";
  document.body.classList.add("photo-lightbox-open");
  lightbox.querySelector(".photo-lightbox-close").focus();
}

document.addEventListener("click", (event) => {
  const image = event.target.closest(".feed-card > img");
  if (image) openPhotoLightbox(image);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closePhotoLightbox();
});

window.addEventListener("DOMContentLoaded", async () => {
  const schoolName = document.getElementById("school-name");
  if (schoolName) schoolName.textContent = userSchool;

  initializeEventNotice();
  initializeOnlineFriends();

  document
    .getElementById("fileInput")
    ?.addEventListener("change", uploadSelectedPhoto);
  document
    .getElementById("aiFileInput")
    ?.addEventListener("change", transformSelectedPhoto);
  document
    .getElementById("profileImageInput")
    ?.addEventListener("change", uploadProfileImage);
  document
    .getElementById("replyInput")
    ?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") sendReply();
    });
  document
    .getElementById("isProfilePublic")
    ?.addEventListener("change", updatePrivacyDependency);
  refreshSocialBadges();

  // 태그 결과에서 특정 사진/댓글로 돌아오면 앨범을 열고 해당 카드로 이동합니다.
  const taggedPhotoId = albumQuery.get("photo");
  if (taggedPhotoId) {
    await openAlbum();
    document
      .querySelector(`.feed-card[data-photo-id="${Number(taggedPhotoId)}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // 다른 게시판의 작성자 이름에서 들어오면 해당 인맥 프로필을 엽니다.
  const profileUserId = Number(albumQuery.get("profile_user"));
  if (profileUserId) await openUserProfile(profileUserId);

  // 쪽지 알림을 눌러 들어온 경우 받은 쪽지함을 바로 엽니다.
  if (albumQuery.get("open") === "messages") await openMessageModal();
});

/* 내 정보 */
async function openProfilePopup() {
  document.getElementById("profilePopup").style.display = "block";
  const status = document.getElementById("privacyStatus");
  status.textContent = "공개 설정을 불러오는 중입니다…";
  try {
    const data = await api("/api/social/settings");
    document.getElementById("profileName").value = data.profile.username;
    document.getElementById("profileSchoolInput").value =
      data.profile.school_name;
    document.getElementById("profileSchoolYear").value =
      data.profile.school_year;
    document.getElementById("profileAge").value = data.profile.age ?? "";
    document.getElementById("profileGender").value = data.profile.gender;
    document.getElementById("profileNationality").value =
      data.profile.nationality;
    document.getElementById("profileHobby").value = data.profile.hobby;
    document.getElementById("tagPermission").value =
      data.settings.tag_permission;
    document.getElementById("allowAlbumComments").checked =
      data.settings.allow_album_comments;
    document.getElementById("allowConnectionDiscovery").checked =
      data.settings.allow_connection_discovery;
    document.getElementById("allowMessages").checked =
      data.settings.allow_messages;
    document.getElementById("isProfilePublic").checked =
      data.settings.is_profile_public;
    document.getElementById("allowFriendSearch").checked =
      data.settings.allow_friend_search;
    status.textContent = "";
    updatePrivacyDependency();
  } catch (error) {
    status.textContent = error.message;
  }
}

function closeProfilePopup() {
  document.getElementById("profilePopup").style.display = "none";
}

function updatePrivacyDependency() {
  const isPublic = document.getElementById("isProfilePublic").checked;
  document
    .querySelectorAll(
      "#allowAlbumComments, #allowConnectionDiscovery, #allowMessages, #allowFriendSearch, #tagPermission",
    )
    .forEach((control) => {
      control.disabled = !isPublic;
    });
  document
    .querySelector(".privacy-settings")
    ?.classList.toggle("all-private", !isPublic);
}

async function saveProfileSettings() {
  const username = document.getElementById("profileName").value.trim();
  if (username.length < 2 || username.length > 50) {
    document.getElementById("privacyStatus").textContent =
      "이름은 2자 이상 50자 이하로 입력해 주세요.";
    return;
  }

  const isPublic = document.getElementById("isProfilePublic").checked;
  if (
    !isPublic &&
    !confirm(
      "전체 공개를 끄면 1촌을 포함한 모든 사용자에게 내 프로필과 앨범이 숨겨집니다.\n계속할까요?",
    )
  ) {
    return;
  }
  const status = document.getElementById("privacyStatus");
  status.textContent = "설정을 저장하는 중입니다…";
  try {
    const data = await api("/api/social/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        school_name: document.getElementById("profileSchoolInput").value,
        school_year: document.getElementById("profileSchoolYear").value,
        age: document.getElementById("profileAge").value,
        gender: document.getElementById("profileGender").value,
        nationality: document.getElementById("profileNationality").value,
        hobby: document.getElementById("profileHobby").value,
        tag_permission: document.getElementById("tagPermission").value,
        allow_album_comments:
          document.getElementById("allowAlbumComments").checked,
        allow_connection_discovery: document.getElementById(
          "allowConnectionDiscovery",
        ).checked,
        allow_messages: document.getElementById("allowMessages").checked,
        allow_friend_search:
          document.getElementById("allowFriendSearch").checked,
        is_profile_public: isPublic,
      }),
    });
    status.textContent = data.message;
    document.getElementById("profileName").value = data.username;
    mainAlbumScript.dataset.currentUsername = data.username;
    setTimeout(closeProfilePopup, 500);
  } catch (error) {
    status.textContent = error.message;
  }
}

/* 앨범 */
async function openAlbum() {
  const notificationCenter = document.getElementById("notificationCenter");
  const notificationSlot = document.getElementById("albumNotificationSlot");
  if (notificationCenter && notificationSlot) {
    notificationSlot.appendChild(notificationCenter);
  }
  document.querySelector(".album-page")?.classList.add("album-feed-open");
  document.getElementById("albumWrap").style.display = "block";
  await Promise.all([loadAlbumFeed(), loadAiImageQuota()]);
}

function closeAlbum() {
  document.getElementById("albumWrap").style.display = "none";
  document.querySelector(".album-page")?.classList.remove("album-feed-open");
  const notificationCenter = document.getElementById("notificationCenter");
  const mobileWrap = document.querySelector(".mobile-wrap");
  const logoutForm = mobileWrap?.querySelector(":scope > .logout-form");
  if (notificationCenter && mobileWrap) {
    mobileWrap.insertBefore(
      notificationCenter,
      logoutForm || mobileWrap.firstChild,
    );
  }
}

function uploadPhoto() {
  document.getElementById("fileInput").click();
}

function uploadAiPhoto() {
  const button = document.querySelector(".ai-upload-btn");
  const userLimit = Number(button?.dataset.userLimit || 2);
  const agreed = confirm(
    `AI 사진 변환은 한 사람당 월 ${userLimit}회까지 사용할 수 있습니다.\n` +
      "지금 저희사이트가 가난합니다 회원수 많아지면 월 0회로 막아드릴께요.\n\n" +
      "사진을 선택하시겠습니까?",
  );
  if (!agreed) return;
  document.getElementById("aiFileInput").click();
}

async function loadAiImageQuota() {
  const quota = document.getElementById("aiImageQuota");
  const button = document.querySelector(".ai-upload-btn");
  if (!quota || !button) return;
  try {
    const data = await api("/api/album/ai-image/status");
    quota.textContent = `이번 달 AI 변환: ${data.user_remaining}/${data.user_limit}회 사용 가능`;
    button.dataset.userLimit = String(data.user_limit);
    button.disabled = data.user_remaining < 1 || data.global_remaining < 1;
  } catch (error) {
    quota.textContent = "AI 변환 사용량을 확인할 수 없습니다.";
  }
}

async function transformSelectedPhoto(event) {
  const file = event.target.files[0];
  if (!file) return;
  const styleSelect = document.getElementById("aiImageStyle");
  const styleLabel = styleSelect.options[styleSelect.selectedIndex].text;
  const button = document.querySelector(".ai-upload-btn");
  const userLimit = Number(button?.dataset.userLimit || 2);
  if (
    !confirm(
      `선택한 사진을 ${styleLabel}으로 변환하여 앨범에 올릴까요?\n월 ${userLimit}회 한도에서 1회가 사용됩니다.`,
    )
  ) {
    event.target.value = "";
    return;
  }

  const status = document.getElementById("albumStatus");
  const formData = new FormData();
  formData.append("image", file);
  formData.append("style", styleSelect.value);
  formData.append(
    "caption",
    document.getElementById("photoCaption").value.trim(),
  );
  formData.append("school", userSchool);
  status.textContent = "AI가 사진을 변환하고 있습니다. 잠시만 기다려 주세요...";
  button.disabled = true;

  try {
    await api("/api/album/ai-image", { method: "POST", body: formData });
    document.getElementById("photoCaption").value = "";
    status.textContent = "AI 변환 사진이 앨범에 올라갔습니다 ✨";
    await loadAlbumFeed();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    event.target.value = "";
    await loadAiImageQuota();
  }
}

async function uploadSelectedPhoto(event) {
  const file = event.target.files[0];
  if (!file) return;

  // 사진을 고른 것만으로 업로드하지 않고 사용자에게 한 번 더 확인합니다.
  if (!confirm(`선택한 "${file.name}" 사진을 앨범에 올릴까요?`)) {
    event.target.value = "";
    document.getElementById("albumStatus").textContent =
      "사진 올리기를 취소했습니다.";
    return;
  }

  const status = document.getElementById("albumStatus");
  const formData = new FormData();
  formData.append("image", file);
  formData.append(
    "caption",
    document.getElementById("photoCaption").value.trim(),
  );
  formData.append("school", userSchool);
  status.textContent = "사진을 안전하게 저장하는 중입니다…";

  try {
    await api("/api/album/photos", { method: "POST", body: formData });
    document.getElementById("photoCaption").value = "";
    event.target.value = "";
    status.textContent = "사진이 앨범에 올라갔습니다 ✨";
    await loadAlbumFeed();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function loadAlbumFeed(ownerId = null) {
  const feed = document.getElementById("albumFeed");
  feed.innerHTML = '<p class="feed-empty">사진을 불러오는 중입니다…</p>';
  try {
    const suffix = ownerId ? `?user_id=${ownerId}` : "";
    const data = await api(`/api/album/feed${suffix}`);
    if (!data.photos.length) {
      feed.innerHTML =
        '<p class="feed-empty">아직 올라온 사진이 없습니다.<br>첫 추억을 남겨보세요.</p>';
      return;
    }
    feed.innerHTML = data.photos.map(photoCardHtml).join("");
  } catch (error) {
    feed.innerHTML = `<p class="feed-empty error">${escapeHtml(error.message)}</p>`;
  }
}

function photoCardHtml(photo) {
  const comments = photo.comments.length
    ? photo.comments
        .map((comment) =>
          renderCommentTree(comment, photo.id, 0, photo.comments_allowed),
        )
        .join("")
    : '<p class="no-comments">아직 댓글이 없습니다. 첫 댓글을 남겨보세요.</p>';

  return `
    <article class="feed-card" data-photo-id="${photo.id}">
      <div class="feed-card-header">
        <button class="feed-owner" onclick="openUserProfile(${photo.owner.id})">
          <span class="mini-avatar">${escapeHtml(photo.owner.username.slice(0, 1))}</span>
          <span>
            <strong>${escapeHtml(photo.owner.username)}</strong>
            <small>${escapeHtml(photo.created_at)}</small>
          </span>
        </button>
        ${
          photo.owner.id === currentUserId
            ? `<button class="photo-delete-btn" onclick="deletePhoto(${photo.id})">삭제</button>`
            : ""
        }
      </div>
      <img src="${escapeHtml(photo.image_url)}" alt="${escapeHtml(photo.owner.username)}님의 앨범 사진">
      <div class="feed-body">
        ${photo.caption ? `<p class="photo-caption">${renderTaggedText(photo.caption)}</p>` : ""}
        <div class="reaction-row">
          <button class="like-btn ${photo.liked ? "liked" : ""}" onclick="toggleLike(${photo.id}, this)">
            💗 사랑달 <span>${photo.like_count}</span>
          </button>
          <button class="dislike-btn ${photo.disliked ? "disliked" : ""}" onclick="toggleDislike(${photo.id}, this)">
            ${photo.disliked ? "👎" : "👎🏻"} 싫어요 <span>${photo.dislike_count}</span>
          </button>
        </div>
        <div class="comment-list">${comments}</div>
        ${
          photo.comments_allowed
            ? `<div class="comment-compose">
              <input type="text" class="comment-input" maxlength="500" placeholder="댓글과 #태그를 남겨주세요">
              <button class="comment-btn" onclick="addComment(${photo.id}, this)">등록</button>
            </div>`
            : '<p class="comments-disabled">사진 주인이 댓글 작성을 허용하지 않았습니다.</p>'
        }
      </div>
    </article>`;
}

function renderCommentTree(comment, photoId, depth, commentsAllowed) {
  const replies = comment.replies?.length
    ? comment.replies
        .map((reply) =>
          renderCommentTree(reply, photoId, depth + 1, commentsAllowed),
        )
        .join("")
    : "";
  return `
    <div class="comment-branch" style="--comment-depth:${Math.min(depth, 6)}">
      <div class="album-comment">
        <div class="comment-line">
          <button class="comment-user" onclick="openUserProfile(${comment.user_id})">
            ${escapeHtml(comment.username)}
          </button>
          <span>${renderTaggedText(comment.content)}</span>
        </div>
        ${
          commentsAllowed
            ? `<button class="reply-open-btn" onclick="showReplyForm(this)">↳ 답글</button>
             <div class="reply-compose">
               <input type="text" maxlength="500" placeholder="${escapeHtml(comment.username)}님께 답글·#태그 남기기">
               <button onclick="addReply(${photoId}, ${comment.id}, this)">등록</button>
             </div>`
            : ""
        }
      </div>
      ${replies}
    </div>`;
}

function showReplyForm(button) {
  const compose = button.nextElementSibling;
  compose.classList.toggle("open");
  if (compose.classList.contains("open"))
    compose.querySelector("input").focus();
}

async function addReply(photoId, parentId, button) {
  const compose = button.closest(".reply-compose");
  const input = compose.querySelector("input");
  const content = input.value.trim();
  if (!content) return;
  button.disabled = true;
  try {
    await api(`/api/album/photos/${photoId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, parent_id: parentId }),
    });
    await loadAlbumFeed();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

async function deletePhoto(photoId) {
  // 실수로 누른 경우를 막기 위해 삭제 전에도 확인창을 표시합니다.
  if (
    !confirm("이 사진을 앨범에서 삭제할까요?\n사랑달과 댓글도 함께 삭제됩니다.")
  )
    return;
  try {
    const data = await api(`/api/album/photos/${photoId}`, {
      method: "DELETE",
    });
    document.getElementById("albumStatus").textContent = data.message;
    await loadAlbumFeed();
  } catch (error) {
    alert(error.message);
  }
}

async function toggleLike(photoId, button) {
  button.disabled = true;
  try {
    const data = await api(`/api/album/photos/${photoId}/like`, {
      method: "POST",
    });
    updateReactionButtons(button.closest(".feed-card"), data);
    if (data.message) {
      const status = document.getElementById("albumStatus");
      if (status) status.textContent = data.message;
    }
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

async function toggleDislike(photoId, button) {
  button.disabled = true;
  try {
    const data = await api(`/api/album/photos/${photoId}/dislike`, {
      method: "POST",
    });
    updateReactionButtons(button.closest(".feed-card"), data);
    if (data.message) {
      const status = document.getElementById("albumStatus");
      if (status) status.textContent = data.message;
    }
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

function updateReactionButtons(card, data) {
  const likeButton = card.querySelector(".like-btn");
  const dislikeButton = card.querySelector(".dislike-btn");
  likeButton.classList.toggle("liked", data.liked);
  dislikeButton.classList.toggle("disliked", data.disliked);
  likeButton.innerHTML = `💗 사랑달 <span>${data.like_count}</span>`;
  dislikeButton.innerHTML = `${data.disliked ? "👎" : "👎🏻"} 싫어요 <span>${data.dislike_count}</span>`;
}

async function addComment(photoId, button) {
  const card = button.closest(".feed-card");
  const input = card.querySelector(".comment-input");
  const content = input.value.trim();
  if (!content) return;
  button.disabled = true;
  try {
    await api(`/api/album/photos/${photoId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    input.value = "";
    await loadAlbumFeed();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

/* 사용자 아이디 클릭: 1촌 상태·쪽지·친구 신청 */
async function openUserProfile(userId) {
  selectedProfileUserId = userId;
  try {
    const data = await api(`/api/social/users/${userId}`);
    selectedProfileUsername = data.user.username;
    document.getElementById("profileUsername").textContent = data.user.username;
    document.getElementById("profileSchool").textContent =
      data.user.school_name;
    renderProfileAvatar(data.user, data.relationship.status === "self");
    document.getElementById("relationshipLabel").textContent =
      data.relationship.label;
    document.getElementById("profileConnectionCount").textContent =
      data.connection_count;
    document.getElementById("connectionPanel").hidden = true;
    document.getElementById("connectionToggleIcon").textContent = "펼치기 ▾";
    document.getElementById("profileConnections").innerHTML = "";
    document.getElementById("connectionPagination").innerHTML = "";
    document.getElementById("profileMessageCompose").style.display = "none";

    const buttons = document.getElementById("userActionButtons");
    buttons.innerHTML = "";
    if (data.relationship.status !== "self") {
      if (data.relationship.status === "none") {
        buttons.appendChild(
          actionButton("👥 1촌 신청하기", () => requestFriend(data.user.id)),
        );
      } else if (data.relationship.status === "received") {
        buttons.appendChild(
          actionButton("✨ 1촌 수락하기", () =>
            acceptFriend(data.relationship.friendship_id),
          ),
        );
      }
      if (data.relationship.status === "accepted") {
        const removeButton = actionButton("1촌 삭제", () =>
          removeFriend(
            data.relationship.friendship_id,
            data.user.username,
            false,
          ),
        );
        removeButton.classList.add("danger-action");
        buttons.appendChild(removeButton);
      }
      if (data.permissions.allow_messages) {
        buttons.appendChild(actionButton("📩 쪽지 보내기", openProfileMessage));
      } else {
        const disabledMessageButton = actionButton(
          "🔕 쪽지 수신 꺼짐",
          () => {},
        );
        disabledMessageButton.disabled = true;
        buttons.appendChild(disabledMessageButton);
      }
      buttons.appendChild(
        actionButton("📸 이 사람 앨범 보기", async () => {
          closeUserActionModal();
          await openAlbum();
          await loadAlbumFeed(data.user.id);
        }),
      );
    }
    document.getElementById("userActionModal").style.display = "block";
  } catch (error) {
    alert(error.message);
  }
}

function renderProfileAvatar(user, isSelf) {
  const avatar = document.getElementById("profileAvatar");
  const hint = document.getElementById("profileImageHint");
  avatar.textContent = user.profile_image_url ? "" : user.username.slice(0, 1);
  avatar.style.backgroundImage = user.profile_image_url
    ? `url("${user.profile_image_url}")`
    : "";
  avatar.classList.toggle("editable", isSelf);
  avatar.disabled = !isSelf;
  hint.textContent = isSelf ? "대표사진을 누르면 등록·교체할 수 있어요" : "";
}

function chooseProfileImage() {
  if (selectedProfileUserId !== currentUserId) return;
  document.getElementById("profileImageInput").click();
}

async function uploadProfileImage(event) {
  const file = event.target.files[0];
  if (!file || selectedProfileUserId !== currentUserId) return;
  if (!confirm(`"${file.name}" 사진을 내 대표사진으로 사용할까요?`)) {
    event.target.value = "";
    return;
  }
  const formData = new FormData();
  formData.append("image", file);
  try {
    const data = await api("/api/social/profile-image", {
      method: "POST",
      body: formData,
    });
    alert(data.message);
    event.target.value = "";
    await openUserProfile(currentUserId);
  } catch (error) {
    alert(error.message);
  }
}

function openProfileMessage() {
  document.getElementById("profileMessageCompose").style.display = "block";
  document.getElementById("profileMessageInput").focus();
}

function cancelProfileMessage() {
  document.getElementById("profileMessageCompose").style.display = "none";
  document.getElementById("profileMessageInput").value = "";
}

async function sendProfileMessage() {
  const input = document.getElementById("profileMessageInput");
  const content = input.value.trim();
  if (!content) {
    alert("쪽지 내용을 입력해 주세요.");
    return;
  }
  try {
    const data = await api("/api/social/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        receiver_id: selectedProfileUserId,
        content,
      }),
    });
    alert(data.message);
    cancelProfileMessage();
  } catch (error) {
    alert(error.message);
  }
}

async function toggleProfileConnections() {
  const panel = document.getElementById("connectionPanel");
  if (!panel.hidden) {
    panel.hidden = true;
    document.getElementById("connectionToggleIcon").textContent = "펼치기 ▾";
    return;
  }
  panel.hidden = false;
  document.getElementById("connectionToggleIcon").textContent = "접기 ▴";
  await loadProfileConnections(1);
}

async function loadProfileConnections(page) {
  currentConnectionPage = page;
  const container = document.getElementById("profileConnections");
  container.innerHTML =
    '<p class="empty-connections">1촌 목록을 불러오는 중입니다…</p>';
  try {
    const data = await api(
      `/api/social/users/${selectedProfileUserId}/connections?page=${page}`,
    );
    container.innerHTML = data.connections.length
      ? data.connections
          .map(
            (connection) => `
          <button type="button" onclick="confirmConnectionMove(${connection.id}, this)">
            ${
              connection.profile_image_url
                ? `<span class="connection-avatar image" style="background-image:url('${escapeHtml(connection.profile_image_url)}')"></span>`
                : `<span class="connection-avatar">${escapeHtml(connection.username.slice(0, 1))}</span>`
            }
            <span>
              <strong>${escapeHtml(connection.username)}</strong>
              <small>${escapeHtml(connection.school_name)}</small>
            </span>
            <em>${relationshipShortLabel(connection.relationship.status)}</em>
          </button>`,
          )
          .join("")
      : '<p class="empty-connections">아직 공개된 1촌이 없습니다.</p>';
    renderConnectionPagination(data.pagination);
  } catch (error) {
    container.innerHTML = `<p class="empty-connections">${escapeHtml(error.message)}</p>`;
  }
}

function renderConnectionPagination(pagination) {
  const nav = document.getElementById("connectionPagination");
  if (pagination.pages <= 1) {
    nav.innerHTML = "";
    return;
  }
  nav.innerHTML = `
    <button ${pagination.has_prev ? "" : "disabled"} onclick="loadProfileConnections(${pagination.page - 1})">이전</button>
    <span>${pagination.page} / ${pagination.pages} 페이지 · 총 ${pagination.total}명</span>
    <button ${pagination.has_next ? "" : "disabled"} onclick="loadProfileConnections(${pagination.page + 1})">다음</button>`;
}

function legacyConfirmConnectionMove(userId, clickedElement) {
  const username =
    clickedElement.querySelector("strong")?.textContent?.trim() || "선택한 1촌";
  const shouldMove = confirm(
    `${username}님의 인맥 프로필로 이동할까요?\n\n확인: 프로필로 이동\n취소: 현재 화면 유지`,
  );
  if (shouldMove) openUserProfile(userId);
}

function closeConnectionChoice() {
  const modal = document.getElementById("connectionChoiceModal");
  if (modal) modal.hidden = true;
}

async function openConnectionMessage(userId) {
  closeConnectionChoice();
  const data = await api(`/api/social/users/${userId}`);
  if (!data.permissions.allow_messages) {
    alert("상대방이 쪽지 수신을 허용하지 않았습니다.");
    return;
  }
  await openUserProfile(userId);
  openProfileMessage();
}

function confirmConnectionMove(userId, clickedElement) {
  const username =
    clickedElement.querySelector("strong")?.textContent?.trim() || "선택한 1촌";
  const friendshipId = clickedElement.closest("[data-friendship-id]")?.dataset
    .friendshipId;
  let modal = document.getElementById("connectionChoiceModal");

  if (!modal) {
    modal = document.createElement("div");
    modal.id = "connectionChoiceModal";
    modal.className = "connection-choice-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="connection-choice-box" role="dialog" aria-modal="true" aria-labelledby="connectionChoiceTitle">
        <p id="connectionChoiceTitle"></p>
        <button type="button" data-action="chat" style="background:#2f80ed;color:#fff;font-weight:700;">💬 1:1 교실 대화하기</button>
        <button type="button" data-action="message">📩 쪽지 보내기</button>
        <button type="button" data-action="profile">👤 프로필 보기</button>
        <button type="button" class="danger" data-action="delete">1촌 삭제</button>
        <button type="button" data-action="cancel">취소</button>
      </div>`;
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeConnectionChoice();
    });
    document.body.appendChild(modal);
  }

  modal.querySelector("p").textContent = `${username}님과 무엇을 할까요?`;
  const chatButton = modal.querySelector('[data-action="chat"]');
  const messageButton = modal.querySelector('[data-action="message"]');
  const profileButton = modal.querySelector('[data-action="profile"]');
  const deleteButton = modal.querySelector('[data-action="delete"]');
  const cancelButton = modal.querySelector('[data-action="cancel"]');

  deleteButton.hidden = !friendshipId;

  chatButton.onclick = () => {
    closeConnectionChoice();
    window.location.href = `/my-home?chat_user=${userId}`;
  };
  messageButton.onclick = () => openConnectionMessage(userId);
  profileButton.onclick = () => {
    closeConnectionChoice();
    openUserProfile(userId);
  };
  deleteButton.onclick = () => {
    closeConnectionChoice();
    removeFriend(Number(friendshipId), username);
  };
  cancelButton.onclick = closeConnectionChoice;
  modal.hidden = false;
  chatButton.focus();
}

function relationshipShortLabel(status) {
  const labels = {
    self: "나",
    accepted: "나와 1촌",
    sent: "신청 보냄",
    received: "신청 도착",
  };

  return labels[status] || "";
}

function actionButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function closeUserActionModal() {
  document.getElementById("userActionModal").style.display = "none";
}

async function requestFriend(userId) {
  try {
    const data = await api(`/api/social/friends/${userId}/request`, {
      method: "POST",
    });
    alert(data.message);
    await openUserProfile(userId);
    await refreshSocialBadges();
  } catch (error) {
    alert(error.message);
  }
}

async function acceptFriend(friendshipId) {
  try {
    const data = await api(`/api/social/friends/${friendshipId}/accept`, {
      method: "POST",
    });
    alert(data.message);
    if (selectedProfileUserId) await openUserProfile(selectedProfileUserId);
    if (document.getElementById("friendListModal").style.display === "block") {
      await openFriendList();
    }
    await refreshSocialBadges();
  } catch (error) {
    alert(error.message);
  }
}

/* 1촌 목록 */
async function removeFriend(friendshipId, username, returnToList = true) {
  if (!confirm(`${username}님과의 1촌 관계를 삭제할까요?`)) return;
  try {
    const data = await api(`/api/social/friends/${friendshipId}`, {
      method: "DELETE",
    });
    alert(data.message);
    if (returnToList) {
      await openFriendList();
    } else {
      closeUserActionModal();
    }
    await refreshSocialBadges();
    await refreshOnlineFriends();
  } catch (error) {
    alert(error.message);
  }
}

async function refreshSocialBadges() {
  try {
    const [friendData, messageData] = await Promise.all([
      api("/api/social/friends"),
      api("/api/social/messages"),
    ]);
    const count = document.getElementById("friend-count");
    count.textContent = friendData.friends.length;
    count.style.display = friendData.friends.length ? "inline-block" : "none";
    const badge = document.getElementById("msg-badge");
    badge.style.display = messageData.unread_count ? "inline" : "none";
  } catch (_) {
    // 배지 조회 실패는 주요 화면 사용을 막지 않습니다.
  }
}

async function openFriendList() {
  const modal = document.getElementById("friendListModal");
  const container = document.getElementById("friendListContainer");
  const requestSection = document.getElementById("friendRequestSection");
  const requestContainer = document.getElementById("friendRequestContainer");
  try {
    const data = await api("/api/social/friends");
    const requests = data.requests
      .map(
        (item) => `
      <div class="friend-item request">
        <button onclick="confirmConnectionMove(${item.user_id}, this)"><strong>${escapeHtml(item.username)}</strong></button>
        <span>1촌 신청 도착</span>
        <button onclick="acceptFriend(${item.friendship_id})">수락</button>
      </div>`,
      )
      .join("");
    const friends = data.friends
      .map(
        (item) => `
      <div class="friend-item accepted" data-friendship-id="${item.friendship_id}">
        <button onclick="confirmConnectionMove(${item.user_id}, this)"><strong>${escapeHtml(item.username)}</strong></button>
        <span>✨ 함께 추억을 나누는 1촌</span>
      </div>`,
      )
      .join("");
    container.innerHTML =
      friends || '<p class="empty-msg">아직 수락된 1촌이 없습니다.</p>';
    requestSection.hidden = !requests;
    requestContainer.innerHTML = requests;
    data.friends.forEach((item) => {
      const row = container.querySelector(
        `.friend-item.accepted[data-friendship-id="${item.friendship_id}"]`,
      );
      if (!row) return;
      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "friend-remove-btn";
      removeButton.textContent = "1촌 삭제";
      removeButton.addEventListener("click", () =>
        removeFriend(item.friendship_id, item.username),
      );
      row.appendChild(removeButton);
    });
    modal.style.display = "block";
  } catch (error) {
    alert(error.message);
  }
}

async function openSchoolManager() {
  const modal = document.getElementById("schoolManagerModal");
  const list = document.getElementById("registeredSchoolList");
  const limit = document.getElementById("schoolLeaveLimit");
  modal.style.display = "block";
  list.innerHTML = '<p class="empty-msg">등록 학교를 불러오는 중입니다…</p>';
  try {
    const data = await api("/api/my-schools");
    limit.textContent = `학교는 최대 ${data.limit}개 · 이번 달 삭제 가능 ${data.leave_remaining}회`;
    list.innerHTML = data.schools.length
      ? data.schools
          .map(
            (school) => `
        <div class="registered-school-item">
          <a href="${escapeHtml(school.url)}">
            <strong>${escapeHtml(school.school_name)}</strong>
            <small>${escapeHtml(school.school_year)}년 · ${escapeHtml(school.school_type)}</small>
          </a>
          <button type="button" onclick="leaveRegisteredSchool(${school.id}, '${escapeHtml(school.school_name)}')">
            기존학교 삭제
          </button>
        </div>`,
          )
          .join("")
      : '<p class="empty-msg">등록된 학교가 없습니다.</p>';
    document.querySelector(".school-add-link").hidden =
      data.schools.length >= data.limit;
  } catch (error) {
    list.innerHTML = `<p class="empty-msg">${escapeHtml(error.message)}</p>`;
  }
}

function closeSchoolManager() {
  document.getElementById("schoolManagerModal").style.display = "none";
}

async function leaveRegisteredSchool(membershipId, schoolName) {
  const warning =
    `${schoolName}에서 탈퇴할까요?\n\n` +
    "이 학교에서 작성한 게시글, 댓글, 사랑별 글, 앨범 사진과 첨부파일이 모두 삭제되며 복구할 수 없습니다.";
  if (!confirm(warning)) return;
  try {
    const data = await api(`/api/my-schools/${membershipId}`, {
      method: "DELETE",
    });
    alert(data.message);
    window.location.href = data.redirect_url;
  } catch (error) {
    alert(error.message);
  }
}

function closeFriendList() {
  document.getElementById("friendListModal").style.display = "none";
}

/* 전체 사용자 찾기: 모든 이름은 같은 인맥 프로필 창으로 연결됩니다. */
function openPeopleFinder() {
  const modal = document.getElementById("peopleFinderModal");
  const container = document.getElementById("peopleListContainer");

  modal.style.display = "block";

  container.innerHTML =
    '<p class="empty-msg">검색 조건을 입력한 뒤 검색해 주세요.</p>';
}

function closePeopleFinder() {
  document.getElementById("peopleFinderModal").style.display = "none";
}

async function loadPeople() {
  const query = document.getElementById("peopleSearchInput").value.trim();
  const age = document.getElementById("peopleAgeInput").value.trim();
  const school = document.getElementById("peopleSchoolInput").value.trim();
  const gender = document.getElementById("peopleGenderInput").value;
  const container = document.getElementById("peopleListContainer");

  // 검색 조건이 하나도 없으면 전체 회원을 불러오지 않습니다.
  if (!query && !age && !school && !gender) {
    container.innerHTML =
      '<p class="empty-msg">이름, 나이, 학교, 성별 중 하나 이상 입력해 주세요.</p>';
    return;
  }

  container.innerHTML =
    '<p class="empty-msg">사람을 찾는 중입니다…</p>';

  try {
    const params = new URLSearchParams();

    if (query) {
      params.set("q", query);
    }

    if (age) {
      params.set("age", age);
    }

    if (school) {
      params.set("school", school);
    }

    if (gender) {
      params.set("gender", gender);
    }

    const data = await api(
      `/api/social/users?${params.toString()}`
    );

    const users = Array.isArray(data.users) ? data.users : [];

    container.innerHTML = users.length
      ? users
          .map((user) => {
            const username = user.username || "사용자";
            const schoolName = user.school_name || "학교 미등록";
            const ageText = user.age
              ? `${user.age}세`
              : "나이 미등록";
            const relationshipStatus =
              user.relationship?.status || "";

            return `
              <button
                type="button"
                class="person-row"
                onclick="openUserProfile(${user.id})"
              >
                <span class="connection-avatar">
                  ${escapeHtml(username.slice(0, 1))}
                </span>

                <span>
                  <strong>${escapeHtml(username)}</strong>
                  <small>
                    ${escapeHtml(schoolName)}
                    · ${escapeHtml(ageText)}
                    · ${escapeHtml(genderLabel(user.gender))}
                  </small>
                </span>

                ${
                  relationshipStatus
                    ? `<em>${escapeHtml(
                        relationshipShortLabel(
                          relationshipStatus
                        )
                      )}</em>`
                    : ""
                }
              </button>
            `;
          })
          .join("")
      : '<p class="empty-msg">조건에 맞는 사용자가 없습니다.</p>';
  } catch (error) {
    container.innerHTML = `
      <p class="empty-msg">
        ${escapeHtml(
          error.message || "사용자 검색 중 오류가 발생했습니다."
        )}
      </p>
    `;
  }
}

function genderLabel(gender) {
  return (
    { male: "남성", female: "여성", other: "기타" }[gender] || "성별 미등록"
  );
}

/* 쪽지 */
async function openMessageModal() {
  const modal = document.getElementById("messageModal");
  const list = document.getElementById("messageList");
  modal.style.display = "block";
  try {
    const data = await api("/api/social/messages");
    document.getElementById("deleteAllReceivedButton").disabled = !data.messages.length;
    list.innerHTML = data.messages.length
      ? data.messages
          .map(
            (message) => `
          <div class="msg-item ${message.is_read ? "" : "unread"}"
            onclick="openUserProfile(${message.sender_id})">
            <button type="button" class="msg-sender"
              title="${escapeHtml(message.sender)}님에게 답장하기"
              onclick="event.stopPropagation(); showReplySection(${message.sender_id}, this.textContent.trim())">
              ${escapeHtml(message.sender)}
            </button>
            <span>${escapeHtml(message.content)}</span>
            <div class="sent-message-meta">
              <small>${escapeHtml(message.created_at)}</small>
              <button type="button" onclick="event.stopPropagation(); deleteReceivedMessage(${message.id})">삭제</button>
            </div>
          </div>`,
          )
          .join("")
      : '<p class="empty-msg">받은 쪽지가 없습니다.</p>';
    await api("/api/social/messages/read", { method: "POST" });
    await refreshSocialBadges();
  } catch (error) {
    list.innerHTML = `<p class="empty-msg">${escapeHtml(error.message)}</p>`;
  }
}

function closeMessageModal() {
  document.getElementById("messageModal").style.display = "none";
  document.getElementById("replySection").style.display = "none";
  document.getElementById("replyInput").value = "";
  currentReplyTargetId = null;
  currentReplyTargetName = "";
}

async function deleteReceivedMessage(messageId) {
  if (!window.confirm("이 받은 쪽지를 삭제할까요? 보낸 사람의 보낸 쪽지함에서도 삭제됩니다.")) return;
  try {
    await api(`/api/social/messages/received/${messageId}`, { method: "DELETE" });
    await openMessageModal();
  } catch (error) {
    alert(error.message);
  }
}

async function deleteAllReceivedMessages() {
  if (!window.confirm("받은 쪽지를 모두 삭제할까요? 보낸 사람의 보낸 쪽지함에서도 삭제되며 복구할 수 없습니다.")) return;
  try {
    const data = await api("/api/social/messages/received", { method: "DELETE" });
    alert(data.message);
    await openMessageModal();
  } catch (error) {
    alert(error.message);
  }
}

async function openSentMessageModal() {
  const modal = document.getElementById("sentMessageModal");
  const list = document.getElementById("sentMessageList");
  closeMessageModal();
  modal.style.display = "block";
  list.innerHTML = '<p class="empty-msg">불러오는 중...</p>';
  try {
    const data = await api("/api/social/messages/sent");
    document.getElementById("deleteAllSentButton").disabled = !data.messages.length;
    list.innerHTML = data.messages.length
      ? data.messages
          .map(
            (message) => `
          <div class="msg-item sent" onclick="openUserProfile(${message.receiver_id})">
            <strong>To. ${escapeHtml(message.receiver)}</strong>
            <span>${escapeHtml(message.content)}</span>
            <div class="sent-message-meta">
              <small>${escapeHtml(message.created_at)} · ${message.is_read ? "읽음" : "안 읽음"}</small>
              <button type="button" onclick="event.stopPropagation(); deleteSentMessage(${message.id})">삭제</button>
            </div>
          </div>`,
          )
          .join("")
      : '<p class="empty-msg">보낸 쪽지가 없습니다.</p>';
  } catch (error) {
    list.innerHTML = `<p class="empty-msg">${escapeHtml(error.message)}</p>`;
  }
}

function closeSentMessageModal() {
  document.getElementById("sentMessageModal").style.display = "none";
}

async function deleteSentMessage(messageId) {
  if (!window.confirm("이 보낸 쪽지를 삭제할까요? 상대방의 받은 쪽지함에서도 삭제됩니다.")) return;
  try {
    await api(`/api/social/messages/sent/${messageId}`, { method: "DELETE" });
    await openSentMessageModal();
  } catch (error) {
    alert(error.message);
  }
}

async function deleteAllSentMessages() {
  if (!window.confirm("보낸 쪽지를 모두 삭제할까요? 상대방의 받은 쪽지함에서도 삭제되며 복구할 수 없습니다.")) return;
  try {
    const data = await api("/api/social/messages/sent", { method: "DELETE" });
    alert(data.message);
    await openSentMessageModal();
  } catch (error) {
    alert(error.message);
  }
}

async function showReplySection(userId, username = "") {
  if (!username) {
    try {
      const data = await api(`/api/social/users/${userId}`);
      username = data.user.username;
    } catch (error) {
      alert(error.message);
      return;
    }
  }
  currentReplyTargetId = userId;
  currentReplyTargetName = username;
  document.getElementById("messageModal").style.display = "block";
  document.getElementById("replyTo").textContent = `To. ${username}`;
  document.getElementById("replySection").style.display = "block";
  document.getElementById("replyInput").focus();
}

async function sendReply() {
  const input = document.getElementById("replyInput");
  const content = input.value.trim();
  if (!currentReplyTargetId || !content) return;
  try {
    const data = await api("/api/social/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ receiver_id: currentReplyTargetId, content }),
    });
    input.value = "";
    alert(data.message);
    closeMessageModal();
  } catch (error) {
    alert(error.message);
  }
}

window.addEventListener("click", (event) => {
  if (event.target.classList.contains("profile-popup")) {
    event.target.style.display = "none";
  }
});

/* 공지사항 오늘 안 보기 기능 */
const EVENT_NOTICE_STORAGE_KEY = "eventNoticeHiddenDate";

function getLocalDateKey() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function initializeEventNotice() {
  const popup = document.getElementById("eventNoticePopup");
  const checkbox = document.getElementById("hideEventNoticeToday");

  if (!popup || !checkbox) return;

  const today = getLocalDateKey();
  const hiddenDate = localStorage.getItem(EVENT_NOTICE_STORAGE_KEY);

  if (hiddenDate === today) {
    popup.style.display = "none";
    return;
  }

  popup.style.display = "flex";

  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      localStorage.setItem(EVENT_NOTICE_STORAGE_KEY, today);
    } else {
      localStorage.removeItem(EVENT_NOTICE_STORAGE_KEY);
    }
  });
}

function closeEventNotice() {
  const popup = document.getElementById("eventNoticePopup");
  const checkbox = document.getElementById("hideEventNoticeToday");

  if (checkbox?.checked) {
    localStorage.setItem(EVENT_NOTICE_STORAGE_KEY, getLocalDateKey());
  }

  if (popup) {
    popup.style.display = "none";
  }
}

let onlineFriendsTimer = null;

function initializeOnlineFriends() {
  refreshOnlineFriends();
  onlineFriendsTimer = window.setInterval(refreshOnlineFriends, 30000);
}

async function refreshOnlineFriends() {
  const list = document.getElementById("onlineFriendList");
  const count = document.getElementById("onlineFriendCount");
  if (!list || !count || document.hidden) return;

  try {
    const data = await api("/api/social/presence", { method: "POST" });
    count.textContent = data.friends.length;
    list.innerHTML = data.friends.length
      ? data.friends
          .map(
            (friend) => `
              <button type="button" class="online-friend-item"
                data-friendship-id="${friend.friendship_id}"
                onclick="confirmConnectionMove(${friend.user_id}, this)">
                <span class="online-friend-dot" aria-hidden="true"></span>
                <strong>${escapeHtml(friend.username)}</strong>
              </button>`,
          )
          .join("")
      : '<p class="online-friends-empty">접속 중인 1촌이 없습니다.</p>';
  } catch (error) {
    console.error("Failed to refresh online friends:", error);
    list.innerHTML =
      '<p class="online-friends-empty">접속 상태를 확인할 수 없습니다.</p>';
  }
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshOnlineFriends();
});
