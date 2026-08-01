const targetUserName = document.getElementById("targetUserName");
const userFeed = document.getElementById("userFeed");
const userAlbumMessage = document.getElementById("userAlbumMessage");
const userAlbumScript = document.currentScript;
const mainAlbumUrl = userAlbumScript.dataset.albumUrl;
const userName = new URLSearchParams(window.location.search).get("user");

function createFeedCard(photoText, description) {
  const card = document.createElement("article");
  card.className = "feed-card";

  const imagePlaceholder = document.createElement("div");
  imagePlaceholder.className = "mock-img";
  imagePlaceholder.textContent = photoText;

  const info = document.createElement("div");
  info.className = "feed-info";
  info.textContent = description;

  card.append(imagePlaceholder, info);
  return card;
}

function loadUserPhotos(name) {
  userFeed.replaceChildren();

  if (name === "홍길") {
    userFeed.append(
      createFeedCard(
        "📸 홍길이의 축구 일상 사진",
        "⚽️ 동아리 주말 경기에서 한 컷!",
      ),
      createFeedCard(
        "📸 홍길이가 먹은 맛있는 떡볶이",
        "🔥 학교 앞 분식집 엽떡 존맛탱",
      ),
    );
    return;
  }

  userFeed.append(
    createFeedCard(
      "📸 등록된 사진이 없습니다.",
      `${name} 님의 첫 게시글을 기다리고 있어요.`,
    ),
  );
}

if (!userName) {
  targetUserName.textContent = "사용자 정보를 찾을 수 없습니다.";
  userAlbumMessage.textContent = "잘못된 접근입니다. 앨범으로 돌아갑니다.";

  setTimeout(() => {
    window.location.href = mainAlbumUrl;
  }, 1200);
} else {
  targetUserName.textContent = `✨ ${userName} 님의 앨범`;
  loadUserPhotos(userName);
}
