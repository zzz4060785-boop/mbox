document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("gameZoneStatus");

  document.querySelectorAll(".game-card").forEach((card) => {
    card.addEventListener("click", () => {
      document
        .querySelectorAll(".game-card")
        .forEach((item) => item.classList.remove("selected"));
      card.classList.add("selected");
      status.textContent = `${card.dataset.gameName} 게임은 현재 준비 중입니다.`;
    });
  });
});
