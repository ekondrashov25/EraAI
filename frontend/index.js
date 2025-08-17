const API_BASE = 'http://localhost:8000';
let isConnected = false;
let isGenerating = false;
let currentGenerationController = null;

// Conversation state tracking
let conversationStarted = false;
let relatedQuestions = [];
let isShowingRelatedQuestions = false;
let currentQuestionIndex = 0;

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

async function fetchRelatedQuestions() {
    try {
        const response = await fetch(`${API_BASE}/related_questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.error) {
            console.error('Error fetching related questions:', data.error);
            return null;
        } else if (data.result && data.result.content) {
            const content = data.result.content[0];
            if (content.text === 'related_questions' || content.text === 'default_questions') {
                return content.questions || [];
            }
        }
        
        return null;
    } catch (error) {
        console.error('Failed to fetch related questions:', error);
        return null;
    }
}

function updateQuickActionsDisplay() {
    const quickActionsContent = document.getElementById('quick-actions-content');
    const quickActionsHeader = document.querySelector('.quick-actions-header h3');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeToggleText = modeToggleBtn.querySelector('.mode-toggle-text');
    
    // Check if panel is collapsed
    const isPanelCollapsed = quickActionsContent.style.display === 'none';
    
    // Show/hide mode toggle button based on conversation state and panel visibility
    if (conversationStarted && relatedQuestions.length > 0 && !isPanelCollapsed) {
        modeToggleBtn.style.display = 'flex';
    } else {
        modeToggleBtn.style.display = 'none';
        if (!conversationStarted || relatedQuestions.length === 0) {
            isShowingRelatedQuestions = false;
        }
    }
    
    if (isShowingRelatedQuestions && relatedQuestions.length > 0) {
        // Show related questions in compact carousel
        quickActionsHeader.textContent = 'Related Questions';
        modeToggleText.textContent = 'Show Quick Actions';
        
        console.log(`Displaying question ${currentQuestionIndex + 1} of ${relatedQuestions.length}`);
        const currentQuestion = relatedQuestions[currentQuestionIndex];
        const questionHTML = `
            <div class="related-question-carousel">
                <button class="carousel-arrow carousel-arrow-left" onclick="navigateQuestion(-1)" ${currentQuestionIndex === 0 ? 'disabled' : ''}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <button class="related-question-btn-compact" onclick="quickAction('${currentQuestion.replace(/'/g, "\\'")}')">
                    <div class="related-question-icon-compact">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                            <path d="M12 17h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="related-question-text-compact">${currentQuestion}</div>
                    <div class="related-question-arrow-compact">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                </button>
                <button class="carousel-arrow carousel-arrow-right" onclick="navigateQuestion(1)" ${currentQuestionIndex === relatedQuestions.length - 1 ? 'disabled' : ''}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
            <div class="carousel-indicators">
                ${relatedQuestions.map((_, index) => `
                    <div class="carousel-dot ${index === currentQuestionIndex ? 'active' : ''}" onclick="goToQuestion(${index})"></div>
                `).join('')}
            </div>
        `;
        
        quickActionsContent.innerHTML = questionHTML;
    } else {
        // Show default quick actions
        quickActionsHeader.textContent = 'Quick Actions';
        if (conversationStarted && relatedQuestions.length > 0) {
            modeToggleText.textContent = 'Show Related Questions';
        }
        
        quickActionsContent.innerHTML = `
            <div class="quick-actions-grid">
                <button class="quick-action-btn" onclick="quickAction('Анализ BTC')">
                    <div class="quick-action-icon" style="background: #10B981;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 3v18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M18 17V9M12 17V5M6 17v-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="quick-action-text">Анализ BTC</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('Обзор рынка')">
                    <div class="quick-action-icon" style="background: #3B82F6;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="3" y="3" width="7" height="7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <rect x="14" y="3" width="7" height="7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <rect x="14" y="14" width="7" height="7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <rect x="3" y="14" width="7" height="7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="quick-action-text">Обзор рынка</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('Торговые идеи')">
                    <div class="quick-action-icon" style="background: #F59E0B;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="quick-action-text">Торговые идеи</div>
                </button>
                <button class="quick-action-btn" onclick="quickAction('Что такое DeFi')">
                    <div class="quick-action-icon" style="background: #8B5CF6;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="quick-action-text">Что такое DeFi</div>
                </button>
            </div>
        `;
    }
}

function getQuestionColor(index) {
    const colors = ['#10B981', '#3B82F6', '#F59E0B', '#8B5CF6'];
    return colors[index % colors.length];
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
    
    // Track conversation state
    if (!conversationStarted) {
        conversationStarted = true;
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
            
            // Fetch related questions after assistant responds
            if (conversationStarted) {
                try {
                    const questions = await fetchRelatedQuestions();
                    if (questions && questions.length > 0) {
                        relatedQuestions = questions;
                        currentQuestionIndex = 0; // Reset to first question
                        isShowingRelatedQuestions = true;
                        updateQuickActionsDisplay();
                    }
                } catch (error) {
                    console.error('Failed to fetch related questions:', error);
                }
            }
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
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const isHidden = content.style.display === 'none';
    
    if (isHidden) {
        content.style.display = 'block';
        toggleIcon.textContent = '▼';
        content.style.animation = 'slideDown 0.3s ease-out';
        // Show mode toggle button if we have related questions
        if (conversationStarted && relatedQuestions.length > 0) {
            modeToggleBtn.style.display = 'flex';
        }
    } else {
        content.style.display = 'none';
        toggleIcon.textContent = '▶';
        // Hide mode toggle button when panel is collapsed
        modeToggleBtn.style.display = 'none';
    }
}

function toggleMode(event) {
    // Prevent event bubbling
    if (event) {
        event.stopPropagation();
    }
    
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeToggleText = modeToggleBtn.querySelector('.mode-toggle-text');
    
    if (isShowingRelatedQuestions) {
        // Switch to quick actions
        isShowingRelatedQuestions = false;
        modeToggleText.textContent = 'Related Questions';
        updateQuickActionsDisplay();
    } else {
        // Switch to related questions
        isShowingRelatedQuestions = true;
        modeToggleText.textContent = 'Quick Actions';
        updateQuickActionsDisplay();
    }
}

function navigateQuestion(direction) {
    const newIndex = currentQuestionIndex + direction;
    console.log(`Navigating: current=${currentQuestionIndex}, direction=${direction}, new=${newIndex}, total=${relatedQuestions.length}`);
    if (newIndex >= 0 && newIndex < relatedQuestions.length) {
        // Add smooth slide animation
        const carousel = document.querySelector('.related-question-carousel');
        if (carousel) {
            carousel.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            // Use translateX for horizontal movement, direction determines left/right
            carousel.style.transform = `translateX(${-direction * 100}%)`;
            
            setTimeout(() => {
                currentQuestionIndex = newIndex;
                updateQuickActionsDisplay();
                carousel.style.transition = 'none';
                carousel.style.transform = 'translateX(0)';
                setTimeout(() => {
                    carousel.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                }, 10);
            }, 250);
        } else {
            currentQuestionIndex = newIndex;
            updateQuickActionsDisplay();
        }
    }
}

function goToQuestion(index) {
    if (index >= 0 && index < relatedQuestions.length && index !== currentQuestionIndex) {
        const direction = index > currentQuestionIndex ? 1 : -1;
        const carousel = document.querySelector('.related-question-carousel');
        if (carousel) {
            carousel.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            // Use translateX for horizontal movement
            carousel.style.transform = `translateX(${-direction * 100}%)`;
            
            setTimeout(() => {
                currentQuestionIndex = index;
                updateQuickActionsDisplay();
                carousel.style.transition = 'none';
                carousel.style.transform = 'translateX(0)';
                setTimeout(() => {
                    carousel.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                }, 10);
            }, 250);
        } else {
            currentQuestionIndex = index;
            updateQuickActionsDisplay();
        }
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
            // Reset conversation state
            conversationStarted = false;
            relatedQuestions = [];
            isShowingRelatedQuestions = false;
            currentQuestionIndex = 0;
            
            // Clear the messages display
            document.getElementById('messages').innerHTML = `
                <div class="message assistant">
                    <div class="message-content">
                        Привет! Я - Эра, ваш личный AI-помощник по криптовалютам и экономике. Я всегда готова помочь вам с аналитикой токенов, генерированием торговых идей, объяснением принципов работы рынка и предоставлением знаний в области криптоэкономики. Задайте мне вопрос или воспользуйтесь подсказками Quick Actions.                    </div>
                    <div class="message-timestamp">${new Date().toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true 
                    })}</div>
                </div>
            `;
            
            // Reset quick actions to default
            updateQuickActionsDisplay();
        }
    } catch (error) {
        alert('Failed to clear history. Check if the API is running.');
    }
}