document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".foreign-friends-search");

  form?.addEventListener("submit", (event) => {
    const hasCondition = [...form.elements].some(
      (field) => field.name && String(field.value).trim(),
    );
    if (!hasCondition) {
      event.preventDefault();
      form.querySelector('input[name="nationality"]')?.focus();
    }
  });
});
