console.log('[Agentic Memory] Background service worker loaded');

chrome.runtime.onInstalled.addListener(() => {
  console.log('[Agentic Memory] Extension installed');
  
  // Set default settings
  chrome.storage.local.set({
    apiBase: 'http://localhost:8000',
    autoExtract: false
  });
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSettings') {
    chrome.storage.local.get(['apiBase', 'autoExtract'], (result) => {
      sendResponse(result);
    });
    return true;
  }
  
  if (request.action === 'saveSettings') {
    chrome.storage.local.set(request.settings, () => {
      sendResponse({ success: true });
    });
    return true;
  }
});