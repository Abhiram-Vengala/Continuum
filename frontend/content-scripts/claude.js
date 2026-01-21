function extractConversation() {
  const messages = [];
  
  // Strategy 1: Look for conversation container
  const conversationDiv = document.querySelector('[data-testid="conversation-content"]') ||
                          document.querySelector('main');
  
  if (!conversationDiv) {
    return { provider: 'claude', messages: [], error: 'No conversation found' };
  }
  
  // Strategy 2: Find message groups
  const messageGroups = conversationDiv.querySelectorAll('[data-testid*="message"]');
  
  messageGroups.forEach(group => {
    // Check for user/assistant indicators
    const isUser = group.querySelector('[data-testid="user-message"]') !== null;
    const content = group.querySelector('.font-claude-message')?.textContent?.trim() ||
                    group.textContent?.trim();
    
    if (content) {
      messages.push({
        role: isUser ? 'user' : 'assistant',
        content
      });
    }
  });
  
  // Strategy 3: If no messages found, try alternative selectors
  if (messages.length === 0) {
    // Fallback implementation
  }
  
  return {
    provider: 'claude',
    sessionId: generateSessionId(),
    messages,
    timestamp: new Date().toISOString(),
    url: window.location.href
  };
}