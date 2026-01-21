(function() {
  console.log('[Agentic Memory] Gemini content script loaded');

  function extractConversation() {
    const messages = [];
    
    // Gemini's DOM structure
    const messageElements = document.querySelectorAll('[class*="message"], [class*="query"], [class*="response"]');
    
    messageElements.forEach(element => {
      const isUser = element.getAttribute('class')?.includes('query') || 
                     element.getAttribute('class')?.includes('user');
      
      const content = element.innerText || element.textContent || '';
      
      if (content.trim()) {
        messages.push({
          role: isUser ? 'user' : 'assistant',
          content: content.trim()
        });
      }
    });

    const sessionId = generateSessionId();

    return {
      provider: 'gemini',
      sessionId: sessionId,
      messages: messages,
      timestamp: new Date().toISOString(),
      url: window.location.href
    };
  }

  function generateSessionId() {
    let sessionId = localStorage.getItem('agenticMemorySession');
    if (!sessionId) {
      sessionId = 'gemini-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('agenticMemorySession', sessionId);
    }
    return sessionId;
  }

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
    return true;
  });
})();
