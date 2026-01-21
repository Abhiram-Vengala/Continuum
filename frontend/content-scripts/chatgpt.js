(function() {
  console.log('[Agentic Memory] ChatGPT content script loaded');

  function extractConversation() {
    const messages = [];
    
    // ChatGPT's DOM structure (as of 2025)
    // Look for message containers
    const messageElements = document.querySelectorAll('[data-message-author-role]');
    
    messageElements.forEach(element => {
      const role = element.getAttribute('data-message-author-role');
      
      // Try multiple selectors for content
      let content = '';
      const contentElement = element.querySelector('.markdown, .whitespace-pre-wrap, [class*="markdown"]');
      
      if (contentElement) {
        content = contentElement.innerText || contentElement.textContent || '';
      }
      
      if (content.trim()) {
        messages.push({
          role: role === 'user' ? 'user' : 'assistant',
          content: content.trim()
        });
      }
    });

    // Extract session ID from URL
    const urlMatch = window.location.pathname.match(/\/c\/([^/]+)/);
    const sessionId = urlMatch ? urlMatch[1] : generateSessionId();

    return {
      provider: 'chatgpt',
      sessionId: sessionId,
      messages: messages,
      timestamp: new Date().toISOString(),
      url: window.location.href
    };
  }

  function generateSessionId() {
    // Generate from URL or create new one
    let sessionId = localStorage.getItem('agenticMemorySession');
    if (!sessionId) {
      sessionId = 'chatgpt-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('agenticMemorySession', sessionId);
    }
    return sessionId;
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getConversation') {
      try {
        const conversation = extractConversation();
        console.log('[Agentic Memory] Extracted conversation:', conversation);
        sendResponse(conversation);
      } catch (error) {
        console.error('[Agentic Memory] Extraction error:', error);
        sendResponse({ error: error.message });
      }
    }
    return true; // Keep channel open for async response
  });
})();