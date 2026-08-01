document.addEventListener("DOMContentLoaded", () => {
  const status = document.getElementById("hoguShopStatus");

  document.querySelectorAll(".hogu-shop-item").forEach((item) => {
    item.addEventListener("click", () => {
      document
        .querySelectorAll(".hogu-shop-item")
        .forEach((button) => button.classList.remove("selected"));
      item.classList.add("selected");
      status.textContent = `${item.dataset.itemName}를 선택했습니다.`;
    });
  });
});
