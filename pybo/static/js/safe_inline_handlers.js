/* Execute legacy event attributes without allowing arbitrary JavaScript.
 * CSP blocks the browser's native attribute execution; this dispatcher only
 * invokes explicitly approved UI functions and parses inert primitive args.
 */
(() => {
  "use strict";
  if (window.__friendarySafeHandlersLoaded) return;
  window.__friendarySafeHandlersLoaded = true;
  const allowed = new Set([
    "acceptFriend", "addComment", "addReply", "cancelProfileMessage",
    "chooseProfileImage", "closeAlbum", "closeContactAdminConfirm",
    "closeEventNotice", "closeFriendList", "closeGameZoneLock",
    "closeHoguShopLock", "closeLanguageConfirm", "closeMessageModal",
    "closePeopleFinder", "closeSchoolManager", "closeSentMessageModal",
    "closeStarDetail", "closeUserActionModal", "confirmConnectionMove",
    "deleteAllReceivedMessages", "deleteAllSentMessages", "deletePhoto",
    "deleteReceivedMessage", "deleteSentMessage", "handleExecutiveSingleUpload",
    "handlePayment", "leaveRegisteredSchool", "loadPeople",
    "loadProfileConnections", "openAlbum", "openAlumniNews",
    "openBottomGallery", "openBottomMeeting", "openBottomNews",
    "openBottomSupport", "openContactAdminConfirm", "openEventPhotos",
    "openFriendList", "openGameZoneLock", "openHoguShopLock",
    "openLanguageConfirm", "openMessageModal", "openPeopleFinder",
    "openProfilePopup", "openSarangdalStatusModal", "openSchoolManager",
    "openSentMessageModal", "openUserProfile", "saveProfileSettings",
    "selectExecutiveSlot", "selectItem", "sendClassroomInvite",
    "sendProfileMessage", "sendReply", "showReplyForm", "showReplySection",
    "toggleDislike", "toggleLike", "toggleProfileConnections",
    "triggerFileInput", "uploadAiPhoto", "uploadPhoto",
  ]);

  function splitArgs(source) {
    const values = [];
    let current = "", quote = "", escaped = false;
    for (const char of source) {
      if (escaped) { current += char; escaped = false; continue; }
      if (char === "\\") { current += char; escaped = true; continue; }
      if (quote) { current += char; if (char === quote) quote = ""; continue; }
      if (char === "'" || char === '"') { quote = char; current += char; continue; }
      if (char === ",") { values.push(current.trim()); current = ""; continue; }
      current += char;
    }
    if (quote) throw new Error("Unclosed event argument");
    if (current.trim()) values.push(current.trim());
    return values;
  }

  function parseArg(value, element, event) {
    if (value === "this") return element;
    if (value === "event") return event;
    if (value === "this.href") return element.href;
    if (value === "this.textContent.trim()") return element.textContent.trim();
    if (/^-?\d+(?:\.\d+)?$/.test(value)) return Number(value);
    if (value === "true") return true;
    if (value === "false") return false;
    if (value === "null") return null;
    if ((value.startsWith("'") && value.endsWith("'")) ||
        (value.startsWith('"') && value.endsWith('"'))) {
      return value.slice(1, -1).replace(/\\(['"\\])/g, "$1");
    }
    throw new Error("Unsupported event argument");
  }

  function invoke(statement, element, event) {
    statement = statement.trim().replace(/^return\s+/, "");
    if (!statement || statement === "false") return statement !== "false";
    if (statement === "event.stopPropagation()") { event.stopPropagation(); return true; }
    statement = statement.replace(/^window\.confirm/, "confirm");
    const match = statement.match(/^([A-Za-z_$][\w$]*)\((.*)\)$/s);
    if (!match) throw new Error("Unsupported event statement");
    const name = match[1];
    if (name !== "confirm" && !allowed.has(name)) throw new Error("Blocked event function");
    const args = splitArgs(match[2]).map((arg) => parseArg(arg, element, event));
    const fn = name === "confirm" ? window.confirm : window[name];
    if (typeof fn !== "function") throw new Error(`Unavailable UI function: ${name}`);
    return fn.apply(window, args);
  }

  for (const eventName of ["click", "change", "submit", "input"]) {
    document.addEventListener(eventName, (event) => {
      const attribute = `on${eventName}`;
      const element = event.target.closest?.(`[${attribute}]`);
      if (!element) return;
      try {
        const statements = element.getAttribute(attribute).split(";").map((part) => part.trim()).filter(Boolean);
        for (const statement of statements) {
          if (invoke(statement, element, event) === false) {
            event.preventDefault();
            break;
          }
        }
      } catch (error) {
        event.preventDefault();
        console.error("Blocked unsafe inline event handler", error);
      }
    }, true);
  }
})();
