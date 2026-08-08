(() => {
  const button = document.getElementById("adminQuickAccessButton");
  if (!button) return;
  button.addEventListener("click", () => {
    window.location.href = button.dataset.url;
  });
})();
