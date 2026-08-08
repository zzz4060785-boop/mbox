(() => {
  let resolvePending = null;

  function ensureModal() {
    let modal = document.getElementById("friendaryConfirmModal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.id = "friendaryConfirmModal";
    modal.className = "friendary-confirm-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="friendary-confirm-backdrop" data-confirm-cancel></div>
      <section class="friendary-confirm-box" role="dialog" aria-modal="true" aria-labelledby="friendaryConfirmMessage">
        <div class="friendary-confirm-icon" aria-hidden="true">💝</div>
        <p id="friendaryConfirmMessage"></p>
        <div class="friendary-confirm-actions">
          <button type="button" class="friendary-confirm-cancel" data-confirm-cancel>취소</button>
          <button type="button" class="friendary-confirm-accept" data-confirm-accept>지급하기</button>
        </div>
      </section>`;
    document.body.appendChild(modal);

    const finish = (accepted) => {
      modal.hidden = true;
      document.body.classList.remove("friendary-modal-open");
      const resolve = resolvePending;
      resolvePending = null;
      resolve?.(accepted);
    };
    modal.querySelectorAll("[data-confirm-cancel]").forEach((element) => {
      element.addEventListener("click", () => finish(false));
    });
    modal.querySelector("[data-confirm-accept]").addEventListener("click", () => finish(true));
    return modal;
  }

  window.friendaryConfirm = (message) => {
    if (resolvePending) resolvePending(false);
    const modal = ensureModal();
    modal.querySelector("#friendaryConfirmMessage").textContent = message;
    modal.hidden = false;
    document.body.classList.add("friendary-modal-open");
    modal.querySelector("[data-confirm-accept]").focus();
    return new Promise((resolve) => {
      resolvePending = resolve;
    });
  };

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-confirm-message]");
    if (!form || form.dataset.confirmed === "true") return;
    event.preventDefault();
    if (await window.friendaryConfirm(form.dataset.confirmMessage)) {
      form.dataset.confirmed = "true";
      form.requestSubmit();
    }
  });
})();
