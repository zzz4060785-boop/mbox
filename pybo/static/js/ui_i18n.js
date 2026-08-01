(function () {
  const language = window.FRIENDARY_LANGUAGE || "ko";
  const catalog = window.FRIENDARY_TRANSLATIONS || {};
  if (language === "ko" || !Object.keys(catalog).length) return;

  const protectedSelector = [
    "[data-no-translate]",
    ".post-content",
    ".comment-content",
    ".comment-item",
    ".notice-content",
    ".notice-post-content",
    ".recommend-content",
    ".recommend-comment__body",
    ".message-content",
    ".message-item",
    ".album-caption",
    ".photo-caption",
    "textarea",
    "script",
    "style",
  ].join(",");
  const entries = Object.entries(catalog).sort((a, b) => b[0].length - a[0].length);

  function isProtected(element) {
    return element?.closest?.(protectedSelector);
  }

  function translated(value) {
    if (!value || !/[가-힣]/.test(value)) return value;
    if (catalog[value]) return catalog[value];
    let result = value;
    for (const [source, target] of entries) {
      if (source.length < 2 || !result.includes(source)) continue;
      result = result.split(source).join(target);
    }
    return result;
  }

  function translateText(node) {
    if (!node.nodeValue?.trim() || isProtected(node.parentElement)) return;
    node.nodeValue = translated(node.nodeValue);
  }

  function translateElement(element) {
    if (!(element instanceof Element) || isProtected(element)) return;
    for (const attribute of ["placeholder", "title", "aria-label"]) {
      if (element.hasAttribute(attribute)) {
        element.setAttribute(attribute, translated(element.getAttribute(attribute)));
      }
    }
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(translateText);
  }

  function run() {
    translateElement(document.body);
    document.documentElement.lang = language;
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.TEXT_NODE) translateText(node);
        if (node.nodeType === Node.ELEMENT_NODE) translateElement(node);
      }
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once: true });
  } else {
    run();
  }
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
