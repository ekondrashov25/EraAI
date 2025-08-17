const API_BASE = 'http://localhost:8000';
let isConnected = false;
let isGenerating = false;
let currentGenerationController = null;

// Enhanced markdown parser for better formatting
function parseMarkdown(text) {
    // Handle code blocks with language specification (```language code```)
    text = text.replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
    
    // Handle inline code (`code`)
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Handle bold (**text** or __text__)
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Handle italic (*text* or _text_)
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Handle strikethrough (~~text~~)
    text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');
    
    // Handle headers (# Header)
    text = text.replace(/^###### (.*$)/gim, '<h6>$1</h6>');
    text = text.replace(/^##### (.*$)/gim, '<h5>$1</h5>');
    text = text.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Handle blockquotes (> text)
    text = text.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
    
    // Handle horizontal rules (--- or ***)
    text = text.replace(/^---$/gim, '<hr>');
    text = text.replace(/^\*\*\*$/gim, '<hr>');
    
    // Handle lists - more robust handling
    let lines = text.split('\n');
    let inList = false;
    let inOrderedList = false;
    let listItems = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const isUnorderedItem = line.match(/^[\*\-+]\s/);
        const isOrderedItem = line.match(/^\d+\.\s/);
        
        if (isUnorderedItem || isOrderedItem) {
            if (!inList) {
                inList = true;
                inOrderedList = isOrderedItem;
                listItems = [];
            }
            
            // Check if we're switching list types
            if ((isOrderedItem && !inOrderedList) || (isUnorderedItem && inOrderedList)) {
                // Close previous list
                if (listItems.length > 0) {
                    const listTag = inOrderedList ? 'ol' : 'ul';
                    lines[i - listItems.length] = `<${listTag}>${listItems.join('')}</${listTag}>`;
                    for (let j = i - listItems.length + 1; j < i; j++) {
                        lines[j] = '';
                    }
                }
                // Start new list
                inOrderedList = isOrderedItem;
                listItems = [];
            }
            
            const cleanText = line.replace(/^[\*\-+]\s/, '').replace(/^\d+\.\s/, '');
            listItems.push(`<li>${cleanText}</li>`);
        } else {
            if (inList && listItems.length > 0) {
                const listTag = inOrderedList ? 'ol' : 'ul';
                lines[i - listItems.length] = `<${listTag}>${listItems.join('')}</${listTag}>`;
                for (let j = i - listItems.length + 1; j < i; j++) {
                    lines[j] = '';
                }
                inList = false;
                inOrderedList = false;
                listItems = [];
            }
        }
    }
    
    // Handle any remaining list
    if (inList && listItems.length > 0) {
        const listTag = inOrderedList ? 'ol' : 'ul';
        const lastListIndex = lines.length - listItems.length;
        lines[lastListIndex] = `<${listTag}>${listItems.join('')}</${listTag}>`;
        for (let j = lastListIndex + 1; j < lines.length; j++) {
            lines[j] = '';
        }
    }
    
    // Clean up empty lines and normalize spacing
    lines = lines.filter(line => line.trim() !== '');
    
    text = lines.join('\n');
    
    // Handle line breaks more efficiently - only add <br> for actual line breaks
    // Remove excessive empty lines and normalize spacing
    text = text.replace(/\n\s*\n/g, '\n'); // Remove multiple consecutive empty lines
    text = text.replace(/\n\s*\n\s*\n/g, '\n'); // Remove triple+ empty lines
    text = text.replace(/\n/g, '<br>');
    text = text.replace(/<br>\s*<br>\s*<br>/g, '<br><br>'); // Limit consecutive <br> tags
    
    return text;
}

// Typing animation function
function typeMessage(element, text, speed = 35) {
    return new Promise((resolve) => {
        let index = 0;
        element.innerHTML = '';
        const messages = document.getElementById('messages');
        let scrollTimeout;
        let animationId;
        
        function typeChar() {
            if (index < text.length && isGenerating) {
                // Handle markdown parsing for the current chunk
                const currentText = text.substring(0, index + 1);
                element.innerHTML = parseMarkdown(currentText) + '<span class="typing-cursor">|</span>';
                index++;
                
                // Debounced scrolling - only scroll every few characters
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    messages.scrollTop = messages.scrollHeight;
                }, 150);
                
                animationId = setTimeout(typeChar, speed);
            } else if (index >= text.length) {
                // Remove cursor when done
                element.innerHTML = parseMarkdown(text);
                // Final scroll to ensure we're at the bottom
                setTimeout(() => {
                    messages.scrollTop = messages.scrollHeight;
                }, 50);
                resolve();
            }
            // If isGenerating becomes false, the animation stops naturally
        }
        
        typeChar();
        
        // Return a function to cancel the animation
        return () => {
            if (animationId) {
                clearTimeout(animationId);
            }
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
        };
    });
}

function showLoading() {
    const messages = document.getElementById('messages');
    
    // Create loading indicator dynamically
    const indicator = document.createElement('div');
    indicator.className = 'loading-indicator show';
    indicator.innerHTML = `
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    // Add to messages container
    messages.appendChild(indicator);
    
    // Smooth scroll to show the loading indicator
    setTimeout(() => {
        messages.scrollTop = messages.scrollHeight;
    }, 50);
}

function hideLoading() {
    const indicator = document.querySelector('.loading-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Check API connection on load
window.onload = async function() {
    // Set current time for initial message
    const initialTimestamp = document.getElementById('initial-timestamp');
    if (initialTimestamp) {
        const now = new Date();
        initialTimestamp.textContent = now.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    await checkConnection();
};

async function checkConnection() {
    try {
        console.log('Checking API connection...');
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            updateStatus('Connected to MCP AI Assistant');
            isConnected = true;
            console.log('API connection successful');
        } else {
            updateStatus('API not ready');
            console.log('API not ready');
        }
    } catch (error) {
        updateStatus('Cannot connect to API. Make sure simple_web_api.py is running on port 8000');
        console.error('Connection error:', error);
        console.log('API connection failed, but continuing...');
    }
}

function updateStatus(message) {
    // Status element was removed, so we'll just log the message
    console.log('Status:', message);
}

function addMessage(role, content, animate = false) {
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // Add timestamp
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
    });
    
    // Create content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    messageDiv.appendChild(contentDiv);
    

    
    // Add timestamp
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    timestampDiv.textContent = timeString;
    messageDiv.appendChild(timestampDiv);
    
    messages.appendChild(messageDiv);
    
    // Only scroll immediately for non-animated messages
    if (!animate) {
        messages.scrollTop = messages.scrollHeight;
    }
    
    // Handle animation for assistant messages
    if (animate && role === 'assistant') {
        return typeMessage(contentDiv, content);
    } else {
        contentDiv.innerHTML = parseMarkdown(content);
        return Promise.resolve();
    }
}

function quickAction(action) {
    const input = document.getElementById('message-input');
    input.value = action;
    sendMessage();
}



async function sendMessage() {
    const input = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const stopButton = document.getElementById('stop-button');
    const message = input.value.trim();
    
    console.log('Send message called with:', message);
    
    if (!message) {
        console.log('No message to send');
        return;
    }
    
    // Set generation state
    isGenerating = true;
    currentGenerationController = new AbortController();
    
    // Disable input and show stop button
    input.disabled = true;
    sendButton.style.display = 'none';
    stopButton.style.display = 'flex';
    
    // Add user message
    addMessage('user', message);
    input.value = '';
    
    // Show loading indicator
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                use_rag: true,
                use_functions: true,
                temperature: 0.7
            }),
            signal: currentGenerationController.signal
        });
        
        const data = await response.json();
        
        if (data.error) {
            hideLoading();
            addMessage('error', `Error: ${data.error.message || 'Unknown error'}`);
        } else if (data.result && data.result.content) {
            const assistantMessage = data.result.content[0].text;
            hideLoading(); // Hide loading before starting typing animation
            await addMessage('assistant', assistantMessage, true); // Enable typing animation
        } else {
            hideLoading();
            addMessage('error', 'Unexpected response format');
        }
        
    } catch (error) {
        console.error('Error:', error);
        if (error.name === 'AbortError') {
            console.log('Request was aborted by user');
        } else {
            addMessage('error', 'Failed to send message. Check if the API is running.');
        }
    } finally {
        // Reset generation state
        isGenerating = false;
        currentGenerationController = null;
        
        // Reset UI
        hideLoading();
        input.disabled = false;
        sendButton.style.display = 'flex';
        stopButton.style.display = 'none';
        input.focus();
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function stopGeneration() {
    if (isGenerating && currentGenerationController) {
        currentGenerationController.abort();
        isGenerating = false;
        currentGenerationController = null;
        
        // Hide stop button and show send button
        document.getElementById('stop-button').style.display = 'none';
        document.getElementById('send-button').style.display = 'flex';
        
        // Re-enable input
        document.getElementById('message-input').disabled = false;
        
        // Hide loading indicator
        hideLoading();
        
        // Keep the partial message as-is, just remove the cursor
        const currentMessage = document.querySelector('.message.assistant:last-child .message-content');
        if (currentMessage) {
            // Remove the typing cursor but keep the partial text
            const textWithCursor = currentMessage.innerHTML;
            const textWithoutCursor = textWithCursor.replace('<span class="typing-cursor">|</span>', '');
            currentMessage.innerHTML = textWithoutCursor;
        }
    }
}



function toggleQuickActions(event) {
    // Prevent event bubbling if called from button
    if (event) {
        event.stopPropagation();
    }
    
    const content = document.getElementById('quick-actions-content');
    const toggleIcon = document.querySelector('.toggle-icon');
    const isHidden = content.style.display === 'none';
    
    if (isHidden) {
        content.style.display = 'block';
        toggleIcon.textContent = '▼';
        content.style.animation = 'slideDown 0.3s ease-out';
    } else {
        content.style.display = 'none';
        toggleIcon.textContent = '▶';
    }
}

async function addKnowledge() {
    const text = prompt('Enter text to add to knowledge base:');
    if (!text) return;
    
    try {
        const response = await fetch(`${API_BASE}/add_knowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texts: [text] })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error.message || 'Unknown error'}`);
        } else {
            alert('Knowledge added successfully!');
        }
    } catch (error) {
        alert('Failed to add knowledge. Check if the API is running.');
    }
}

async function searchKnowledge() {
    const query = prompt('Enter search query:');
    if (!query) return;
    
    try {
        const response = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error.message || 'Unknown error'}`);
        } else if (data.result && data.result.content) {
            const results = data.result.content[0].text;
            alert(`Search Results:\n\n${results}`);
        } else {
            alert('No results found');
        }
    } catch (error) {
        alert('Failed to search. Check if the API is running.');
    }
}

async function getSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/system_info`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error.message || 'Unknown error'}`);
        } else if (data.result && data.result.content) {
            const info = data.result.content[0].text;
            alert(`System Information:\n\n${info}`);
        }
    } catch (error) {
        alert('Failed to get system info. Check if the API is running.');
    }
}

async function getHistory() {
    try {
        const response = await fetch(`${API_BASE}/conversation_history`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error.message || 'Unknown error'}`);
        } else if (data.result && data.result.content) {
            const history = data.result.content[0].text;
            alert(`Conversation History:\n\n${history}`);
        }
    } catch (error) {
        alert('Failed to get history. Check if the API is running.');
    }
}

async function clearHistory() {
    if (!confirm('Are you sure you want to clear the conversation history?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/clear_history`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error.message || 'Unknown error'}`);
        } else {
            alert('History cleared successfully!');
            // Clear the messages display
            document.getElementById('messages').innerHTML = `
                <div class="message assistant">
                    <div class="message-content">
                        Привет! Я - Эра, ваш личный Al-помощник по криптовалютам и экономике. Я всегда готова помочь вам с аналитикой токенов, генерированием торговых идей, объяснением принципов работы рынка и предоставлением знаний в области криптоэкономики. Задайте мне вопрос или воспользуйтесь подсказками Quick Actions.                    </div>
                    <div class="message-timestamp">${new Date().toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true 
                    })}</div>
                </div>
            `;
        }
    } catch (error) {
        alert('Failed to clear history. Check if the API is running.');
    }
}