/* Background service worker
   - Registers a right-click context menu so users can analyze selected text.
*/

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "tonecheck-analyze",
    title: 'Check tone with Tonecheck: "%s"',
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "tonecheck-analyze" && info.selectionText) {
    chrome.storage.local.set({ pendingText: info.selectionText }, () => {
      chrome.action.openPopup?.().catch(() => {
        // openPopup is not available on all browsers/contexts; fall back silently.
      });
    });
  }
});
