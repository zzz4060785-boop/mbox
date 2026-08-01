const goSchoolButton = document.getElementById("goSchoolBtn");

if (goSchoolButton) {
  goSchoolButton.addEventListener("click", () => {
    window.location.href = goSchoolButton.dataset.url;
  });
}
