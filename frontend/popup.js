// Vanilla JavaScript popup UI - FIXED VERSION
document.addEventListener('DOMContentLoaded', function() {
  const root = document.getElementById('root');
  const API_BASE = 'http://localhost:8000';
  
  let state = 'idle'; // idle | loading | extracted | processed
  let conversation = null;
  let processedContext = null;
  let error = null;

  const extractConversation = async () => {
    state = 'loading';
    error = null;
    render();
    
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const url = tab.url;
      
      let provider = 'unknown';
      if (url.includes('chatgpt.com') || url.includes('chat.openai.com')) {
        provider = 'chatgpt';
      } else if (url.includes('claude.ai')) {
        provider = 'claude';
      } else if (url.includes('gemini.google.com')) {
        provider = 'gemini';
      }

      chrome.tabs.sendMessage(tab.id, { action: 'getConversation' }, (response) => {
        if (chrome.runtime.lastError) {
          error = `Failed to extract: ${chrome.runtime.lastError.message}`;
          state = 'idle';
          render();
          return;
        }
        
        if (response && response.messages && response.messages.length > 0) {
          conversation = response;
          state = 'extracted';
          render();
        } else {
          error = 'No conversation found. Please ensure you have an active chat open.';
          state = 'idle';
          render();
        }
      });
    } catch (err) {
      error = `Error: ${err.message}`;
      state = 'idle';
      render();
    }
  };

  const processContext = async () => {
    state = 'loading';
    error = null;
    render();

    try {
      const payload = {
        conversation_input: {
          session_id: conversation.sessionId,
          user_message: conversation.messages[conversation.messages.length - 1].content,
          conversation_history: conversation.messages
        },
        target_provider: conversation.provider,
        retrieve_context: true,
        apply_policies: true
      };

      console.log('Sending payload:', payload);

      const response = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend error:', errorText);
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();
      console.log('Backend response:', data);
      
      processedContext = data;
      state = 'processed';
      render();
    } catch (err) {
      console.error('Process error:', err);
      error = `Failed to process: ${err.message}. Is backend running on ${API_BASE}?`;
      state = 'extracted';
      render();
    }
  };

  const copyToClipboard = (text) => {
    if (!text || text.trim() === '') {
      alert('No content to copy');
      return;
    }
    
    console.log('Copying to clipboard:', text.substring(0, 100) + '...');
    
    navigator.clipboard.writeText(text).then(() => {
      // Show success feedback
      const copyBtn = document.getElementById('copyBtn');
      if (copyBtn) {
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '✅ Copied!';
        copyBtn.style.background = '#4caf50';
        setTimeout(() => {
          copyBtn.innerHTML = originalText;
          copyBtn.style.background = '#1a1a1a';
        }, 2000);
      }
    }).catch(err => {
      console.error('Clipboard error:', err);
      error = 'Failed to copy to clipboard';
      render();
    });
  };

  const openInNewChat = () => {
    const urls = {
      chatgpt: 'https://chat.openai.com/',
      claude: 'https://claude.ai/new',
      gemini: 'https://gemini.google.com/'
    };
    const url = urls[conversation.provider] || urls.chatgpt;
    chrome.tabs.create({ url: url });
  };

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  const render = () => {
    let content = '';

    // Header
    content += `
      <div style="background: #1a1a1a; color: #fff; padding: 16px 20px; border-bottom: 1px solid #e0e0e0;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="font-size: 24px;">🧠</div>
          <div>
            <h1 style="margin: 0; font-size: 16px; font-weight: 600;">Agentic Memory</h1>
            <p style="margin: 0; font-size: 12px; opacity: 0.7;">Cognitive continuity across sessions</p>
          </div>
        </div>
      </div>
    `;

    content += `<div style="flex: 1; overflow-y: auto; padding: 20px;">`;

    // Error Display
    if (error) {
      content += `
        <div style="background: #fee; border: 1px solid #fcc; border-radius: 6px; padding: 12px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
          <span style="color: #d32f2f; font-size: 18px;">⚠️</span>
          <span style="color: #d32f2f; font-size: 13px;">${escapeHtml(error)}</span>
        </div>
      `;
    }

    // Idle State
    if (state === 'idle') {
      content += `
        <div style="text-align: center; padding: 40px 20px;">
          <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;">🧠</div>
          <h2 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">Ready to Extract Context</h2>
          <p style="margin: 0 0 24px 0; color: #666; font-size: 13px;">Extract conversation from ChatGPT, Claude, or Gemini</p>
          <button id="extractBtn" style="background: #1a1a1a; color: white; border: none; border-radius: 6px; padding: 12px 24px; font-size: 14px; font-weight: 500; cursor: pointer;">
            🧠 Extract Conversation
          </button>
        </div>
      `;
    }

    // Loading State
    if (state === 'loading') {
      content += `
        <div style="text-align: center; padding: 60px 20px;">
          <div style="display: inline-block; font-size: 40px; animation: spin 1s linear infinite;">⏳</div>
          <p style="color: #666; font-size: 13px; margin-top: 16px;">${conversation ? 'Processing context...' : 'Extracting conversation...'}</p>
        </div>
      `;
    }

    // Extracted State
    if (state === 'extracted' && conversation) {
      content += `
        <div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <span style="font-size: 16px;">✓</span>
            <h3 style="margin: 0; font-size: 14px; font-weight: 600;">Conversation Extracted</h3>
          </div>
          <div style="font-size: 13px; color: #666; line-height: 1.6;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span>Provider:</span>
              <strong style="color: #1a1a1a; text-transform: capitalize;">${escapeHtml(conversation.provider)}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span>Messages:</span>
              <strong style="color: #1a1a1a;">${conversation.messages.length}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span>Session ID:</span>
              <code style="font-size: 11px; background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${escapeHtml(conversation.sessionId.slice(0, 12))}...</code>
            </div>
          </div>
        </div>
        <button id="processBtn" style="width: 100%; background: #1a1a1a; color: white; border: none; border-radius: 6px; padding: 12px; font-size: 14px; font-weight: 500; cursor: pointer;">
          🧠 Process Context
        </button>
      `;
    }

    // Processed State - FIXED
    if (state === 'processed' && processedContext) {
      // Extract the correct structure from backend response
      const renderedContext = processedContext.rendered_context || {};
      const systemPrompt = renderedContext.system_prompt || '';
      const userPrompt = renderedContext.user_prompt || '';
      const storedMemories = processedContext.stored_memories || [];
      const metadata = processedContext.metadata || {};
      
      content += `
        <div style="background: #f0f7ff; border: 1px solid #90caf9; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
          <h3 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600;">✅ Context Processed</h3>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px;">
            <div>
              <div style="color: #666; margin-bottom: 4px;">Memories Stored</div>
              <div style="font-size: 20px; font-weight: 700;">${storedMemories.length}</div>
            </div>
            <div>
              <div style="color: #666; margin-bottom: 4px;">Provider</div>
              <div style="font-size: 16px; font-weight: 600; text-transform: capitalize;">${escapeHtml(conversation.provider)}</div>
            </div>
          </div>
        </div>
      `;

      // System Prompt
      if (systemPrompt && systemPrompt.trim()) {
        content += `
          <details open style="background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; cursor: pointer;">
            <summary style="font-weight: 600; font-size: 13px; user-select: none; cursor: pointer;">📋 System Prompt (${systemPrompt.length} chars)</summary>
            <pre style="background: #fafafa; padding: 12px; border-radius: 4px; font-size: 11px; line-height: 1.5; overflow-x: auto; margin-top: 8px; white-space: pre-wrap; word-break: break-word; margin: 8px 0 0 0;">${escapeHtml(systemPrompt)}</pre>
          </details>
        `;
      }

      // User Prompt (if different from system)
      if (userPrompt && userPrompt.trim() && userPrompt !== systemPrompt) {
        content += `
          <details style="background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; cursor: pointer;">
            <summary style="font-weight: 600; font-size: 13px; user-select: none; cursor: pointer;">💬 User Context (${userPrompt.length} chars)</summary>
            <pre style="background: #fafafa; padding: 12px; border-radius: 4px; font-size: 11px; line-height: 1.5; overflow-x: auto; margin-top: 8px; white-space: pre-wrap; word-break: break-word; margin: 8px 0 0 0;">${escapeHtml(userPrompt.substring(0, 500))}${userPrompt.length > 500 ? '...' : ''}</pre>
          </details>
        `;
      }

      // Memories breakdown
      if (storedMemories.length > 0) {
        const memoryTypes = {};
        storedMemories.forEach(m => {
          const type = m.type || 'unknown';
          memoryTypes[type] = (memoryTypes[type] || 0) + 1;
        });

        content += `
          <details open style="background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; cursor: pointer;">
            <summary style="font-weight: 600; font-size: 13px; user-select: none; cursor: pointer;">🧠 Memory Breakdown</summary>
            <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              ${Object.entries(memoryTypes).map(([type, count]) => `
                <div style="background: #f5f5f5; padding: 8px; border-radius: 4px;">
                  <div style="font-size: 11px; color: #666; text-transform: capitalize;">${escapeHtml(type)}</div>
                  <div style="font-size: 18px; font-weight: 600;">${count}</div>
                </div>
              `).join('')}
            </div>
          </details>
        `;
      }

      // Copy buttons with different options
      content += `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px;">
          <button id="copySystemBtn" style="background: #1a1a1a; color: white; border: none; border-radius: 6px; padding: 12px; font-size: 13px; font-weight: 500; cursor: pointer;">
            📋 Copy System Prompt
          </button>
          <button id="copyFullBtn" style="background: #1a1a1a; color: white; border: none; border-radius: 6px; padding: 12px; font-size: 13px; font-weight: 500; cursor: pointer;">
            📦 Copy Full Context
          </button>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 8px;">
          <button id="copyJsonBtn" style="flex: 1; background: white; color: #1a1a1a; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; font-size: 13px; font-weight: 500; cursor: pointer;">
            🔧 Copy JSON
          </button>
          <button id="chatBtn" style="flex: 1; background: white; color: #1a1a1a; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; font-size: 13px; font-weight: 500; cursor: pointer;">
            🔗 Open Chat
          </button>
        </div>
      `;
    }

    content += `</div>`;

    // Footer
    const containerHtml = `
      <div style="width: 420px; min-height: 500px; max-height: 600px; background: #fafafa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1a1a1a; display: flex; flex-direction: column;">
        ${content}
        <div style="border-top: 1px solid #e0e0e0; padding: 12px 20px; background: #fff; font-size: 11px; color: #999; text-align: center;">
          Backend: ${API_BASE.includes('localhost') ? '🟢 Local' : '🔴 Remote'}
        </div>
      </div>
    `;

    root.innerHTML = containerHtml;

    // Attach event listeners
    const extractBtn = document.getElementById('extractBtn');
    if (extractBtn) extractBtn.addEventListener('click', extractConversation);

    const processBtn = document.getElementById('processBtn');
    if (processBtn) processBtn.addEventListener('click', processContext);

    // FIXED: Multiple copy options
    const copySystemBtn = document.getElementById('copySystemBtn');
    if (copySystemBtn) {
      copySystemBtn.addEventListener('click', () => {
        const renderedContext = processedContext.rendered_context || {};
        const systemPrompt = renderedContext.system_prompt || '';
        if (systemPrompt) {
          copyToClipboard(systemPrompt);
        } else {
          alert('No system prompt available');
        }
      });
    }

    const copyFullBtn = document.getElementById('copyFullBtn');
    if (copyFullBtn) {
      copyFullBtn.addEventListener('click', () => {
        const renderedContext = processedContext.rendered_context || {};
        const systemPrompt = renderedContext.system_prompt || '';
        const userPrompt = renderedContext.user_prompt || '';
        const fullContext = `=== SYSTEM PROMPT ===\n${systemPrompt}\n\n=== USER CONTEXT ===\n${userPrompt}`;
        copyToClipboard(fullContext);
      });
    }

    const copyJsonBtn = document.getElementById('copyJsonBtn');
    if (copyJsonBtn) {
      copyJsonBtn.addEventListener('click', () => {
        const jsonStr = JSON.stringify(processedContext, null, 2);
        copyToClipboard(jsonStr);
      });
    }

    const chatBtn = document.getElementById('chatBtn');
    if (chatBtn) chatBtn.addEventListener('click', openInNewChat);
  };

  // Initial render
  render();
});