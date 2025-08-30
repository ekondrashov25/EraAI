const API_BASE = 'http://localhost:8000';
let isConnected = false;
let isGenerating = false;
let currentGenerationController = null;

// Conversation state tracking
let conversationStarted = false;
let relatedQuestions = [];
let isShowingRelatedQuestions = false;
let currentQuestionIndex = 0;
let starterQuestions = [];
let starterLoading = true;
let quickActionsShown = false;

// Smooth auto-scroll helpers
const SCROLL_THROTTLE_MS = 120;
let lastScrollTs = 0;

function scrollToBottom(smooth = true) {
    const messages = document.getElementById('messages');
    if (!messages) return;
    try {
        if (smooth && messages.scrollTo) {
            messages.scrollTo({ top: messages.scrollHeight, behavior: 'smooth' });
        } else {
            messages.scrollTop = messages.scrollHeight;
        }
    } catch (_) {
        messages.scrollTop = messages.scrollHeight;
    }
}

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
    
    // Handle links [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Handle lists - more robust handling
    let lines = text.split('\n');
    let inList = false;
    let inOrderedList = false;
    let listItems = [];
    let orderedListCounter = 1;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const isUnorderedItem = line.match(/^[\*\-+]\s/);
        const isOrderedItem = line.match(/^(\d+)\.\s/);
        
        if (isUnorderedItem || isOrderedItem) {
            if (!inList) {
                inList = true;
                inOrderedList = isOrderedItem;
                listItems = [];
                orderedListCounter = 1;
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
                orderedListCounter = 1;
            }
            
            let cleanText;
            if (isOrderedItem) {
                // For ordered lists, preserve the original number
                const originalNumber = isOrderedItem[1];
                cleanText = line.replace(/^\d+\.\s/, '');
                listItems.push(`<li value="${originalNumber}">${cleanText}</li>`);
            } else {
                // For unordered lists, just remove the marker
                cleanText = line.replace(/^[\*\-+]\s/, '');
                listItems.push(`<li>${cleanText}</li>`);
            }
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
                orderedListCounter = 1;
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
    
    // Handle line breaks more efficiently - reduce excessive breaks
    // Remove multiple consecutive empty lines
    text = text.replace(/\n\s*\n/g, '\n');
    text = text.replace(/\n\s*\n\s*\n/g, '\n');
    
    // Only add <br> for single line breaks, not for empty lines
    text = text.replace(/\n/g, ' ');
    
    // Clean up excessive spaces
    text = text.replace(/\s+/g, ' ');
    text = text.trim();
    
    // Remove <br> tags that appear right after headers
    text = text.replace(/(<\/h[1-6]>)\s*<br>/g, '$1');
    
    // Remove <br> tags that appear right before headers
    text = text.replace(/<br>\s*(<h[1-6]>)/g, '$1');
    
    return text;
}

// Typing animation function
function typeMessage(element, text, speed = 12) {
    return new Promise((resolve) => {
        let index = 0;
        element.innerHTML = '';
        const messages = document.getElementById('messages');
        let animationId;
        
        function typeChar() {
            if (index < text.length && isGenerating) {
                // Handle markdown parsing for the current chunk
                const currentText = text.substring(0, index + 1);
                element.innerHTML = parseMarkdown(currentText) + '<span class="typing-cursor">|</span>';
                index++;
                
                // Throttled smooth auto-scroll while typing
                const now = Date.now();
                if (now - lastScrollTs > SCROLL_THROTTLE_MS) {
                    scrollToBottom(true);
                    lastScrollTs = now;
                }
                
                animationId = setTimeout(typeChar, speed);
            } else if (index >= text.length) {
                // Remove cursor when done
                element.innerHTML = parseMarkdown(text);
                // Final scroll to ensure we're at the bottom
                scrollToBottom(true);
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
        };
    });
}

function showLoading() {
    const messages = document.getElementById('messages');
    
    // Create loading indicator dynamically
    const indicator = document.createElement('div');
    indicator.className = 'loading-indicator show';
    
    // Array of thinking messages
    const thinkingMessages = [
        "Модель думает над ответом",
        "Ищем нужную информацию",
        "Анализируем данные",
        "Формируем ответ",
        "Проверяем источники",
        "Обрабатываем запрос"
    ];
    
    let currentMessageIndex = 0;
    
    // Function to update the message with smooth transition
    function updateMessage() {
        const thinkingText = indicator.querySelector('.thinking-text');
        if (thinkingText) {
            // Fade out current text
            thinkingText.style.opacity = '0';
            thinkingText.style.transform = 'translateY(5px)';
            
            setTimeout(() => {
                // Update text content
                thinkingText.textContent = thinkingMessages[currentMessageIndex];
                // Fade in new text
                thinkingText.style.opacity = '1';
                thinkingText.style.transform = 'translateY(0)';
            }, 150);
        } else {
            // Initial render
            indicator.innerHTML = `
                <div class="thinking-message">
                    <span class="thinking-text">${thinkingMessages[currentMessageIndex]}</span>
                    <span class="thinking-dots">...</span>
                </div>
            `;
        }
        
        // Move to next message
        currentMessageIndex = (currentMessageIndex + 1) % thinkingMessages.length;
    }
    
    // Show initial message
    updateMessage();
    
    // Change message every 2 seconds
    const messageInterval = setInterval(updateMessage, 2000);
    
    // Store interval ID to clear it later
    indicator.dataset.intervalId = messageInterval;
    
    // Add to messages container
    messages.appendChild(indicator);
    
    // Smooth scroll to show the loading indicator
    scrollToBottom(true);
}

function hideLoading() {
    const indicator = document.querySelector('.loading-indicator');
    if (indicator) {
        // Clear the interval if it exists
        if (indicator.dataset.intervalId) {
            clearInterval(parseInt(indicator.dataset.intervalId));
        }
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
    
    // Initialize textarea height
    const inputInit = document.getElementById('message-input');
    if (inputInit) {
        autoResize(inputInit);
    }
    
    // Start loading animation on toggle button
    startQuickActionsLoading();
    
    // Start the animated greeting immediately (do not wait for API calls)
    showInitialGreeting();
    
    // Fetch Quick Actions in the background
    starterLoading = true;
    const startTime = Date.now();
    console.log('Starting Quick Actions fetch at:', startTime);
    
    try {
        const starters = await fetchQuickActions();
        const fetchTime = Date.now();
        console.log('Quick Actions API response received at:', fetchTime, 'Duration:', fetchTime - startTime, 'ms');
        
        if (starters && starters.length > 0) {
            starterQuestions = starters;
            console.log('Quick Actions set:', starterQuestions);
            
            // Set loading to false first
            starterLoading = false;
            
            // Stop loading animation and show ready state
            showQuickActions();
            
            // Update display to show the actual questions
            updateQuickActionsDisplay();
            
            // Open panel smoothly after data is loaded and displayed
            setTimeout(() => {
                const openStart = Date.now();
                autoOpenQuickActionsPanel();
                const openEnd = Date.now();
                console.log('Panel opening took:', openEnd - openStart, 'ms');
            }, 100);
            
        } else {
            // If no data received, still stop loading but keep panel closed
            starterLoading = false;
            showQuickActions();
            console.log('No Quick Actions data received, keeping panel closed');
        }
    } catch (e) {
        console.error('Failed to load quick actions:', e);
        // Stop loading animation even on error
        starterLoading = false;
        showQuickActions();
    } finally {
        const endTime = Date.now();
        console.log('Quick Actions loading finished at:', endTime, 'Total duration:', endTime - startTime, 'ms');
        
        const finalTime = Date.now();
        console.log('Total operation took:', finalTime - startTime, 'ms');
    }
    
    // Observe size changes to keep pinned to bottom during generation
    const messagesEl = document.getElementById('messages');
    if (messagesEl && 'ResizeObserver' in window) {
        const ro = new ResizeObserver(() => {
            if (isGenerating) {
                scrollToBottom(true);
            }
        });
        ro.observe(messagesEl);
    }
    
    // Add click handler to hide keyboard when clicking on free area
    if (messagesEl) {
        messagesEl.addEventListener('click', function(event) {
            // Only hide keyboard if clicking on the messages container itself, not on interactive elements
            if (event.target === messagesEl || event.target.classList.contains('message')) {
                const input = document.getElementById('message-input');
                if (input && document.activeElement === input) {
                    input.blur();
                }
            }
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

function addMessage(role, content, animate = false, speed = null, className = null) {
    const messages = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    if (className) {
        messageDiv.classList.add(className);
    }
    
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
    
    // Add avatar for assistant messages
    if (role === 'assistant') {
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = 'img/icon.png';
        avatarImg.alt = 'Era AI';
        avatarDiv.appendChild(avatarImg);
        messageDiv.appendChild(avatarDiv);
    }
    
    messageDiv.appendChild(contentDiv);
    
    // Add timestamp
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    timestampDiv.textContent = timeString;
    messageDiv.appendChild(timestampDiv);
    
    messages.appendChild(messageDiv);
    // Keep view pinned to the newest message
    scrollToBottom(false);
    
    // Only scroll immediately for non-animated messages
    if (!animate) {
        scrollToBottom(false);
    }
    
    // Handle animation for assistant messages
    if (animate && role === 'assistant') {
        return typeMessage(contentDiv, content, speed);
    } else {
        contentDiv.innerHTML = parseMarkdown(content);
        return Promise.resolve();
    }
}

function setQuickActionsDisabled(disabled) {
    const content = document.getElementById('quick-actions-content');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const input = document.getElementById('message-input');
    
    if (content) {
        if (disabled) {
            content.classList.add('disabled-during-generation');
            // Hide the panel when model is typing
            content.style.display = 'none';
        } else {
            content.classList.remove('disabled-during-generation');
            // Keep panel hidden after generation - user must click to open
            content.style.display = 'none';
        }
    }
    if (modeToggleBtn) {
        modeToggleBtn.disabled = !!disabled;
    }
    
    // Also disable the main toggle button during generation
    const toggleBtn = document.getElementById('toggle-quick-actions');
    if (toggleBtn) {
        toggleBtn.disabled = !!disabled;
    }
    // Avoid input jumping by keeping its height stable while generating
    if (input) {
        if (disabled) {
            // Lock to base compact height so the field does not grow
            input.dataset.locked = '1';
            input.style.height = '48px';
            input.style.minHeight = '48px';
            input.style.maxHeight = '48px';
            input.style.overflowY = 'hidden';
            input.style.overflowX = 'hidden';
            input.style.paddingTop = '';
            input.style.paddingBottom = '';
        } else {
            input.style.height = '';
            input.style.minHeight = '48px';
            input.style.maxHeight = '160px';
            input.style.overflowY = 'hidden';
            input.style.overflowX = 'hidden';
            delete input.dataset.locked;
            autoResize(input);
        }
    }
    
    // Update button visibility immediately
    updateQuickActionsDisplay();
}



// Show loading gif, then type the initial greeting like a normal assistant response
async function showInitialGreeting() {
    const greeting = 'Привет! Я - Эра, твой личный AI-помощник по криптовалютам и экономике. Я всегда готова помочь вам с аналитикой токенов, генерированием торговых идей, объяснением принципов работы рынка и предоставлением знаний в области криптоэкономики. Задайте мне вопрос или воспользуйтесь подсказками Quick Actions.';
    const input = document.getElementById('message-input');
    if (input) {
        input.readOnly = true;
    }
    
    // Simulate generation state for typing animation without loading indicator
    isGenerating = true;
    setQuickActionsDisabled(true);
    await addMessage('assistant', greeting, true, 8, 'greeting-message');
    isGenerating = false;
    setQuickActionsDisabled(false);
    
    // Show Quick Actions after greeting is complete
    showQuickActions();
    
    if (input) {
        input.readOnly = false;
        input.focus();
    }
}

// Function to clean question text by removing hyphens and extra spaces
function cleanQuestionText(text) {
    if (!text) return '';
    return text
        .replace(/^[-–—\s]+/, '') // Remove leading hyphens and spaces
        .replace(/[-–—\s]+$/, '') // Remove trailing hyphens and spaces
        .replace(/\s+/g, ' ') // Replace multiple spaces with single space
        .trim();
}

function quickAction(action) {
    const input = document.getElementById('message-input');
    // Reset input to compact size before filling
    input.style.height = '48px';
    input.style.minHeight = '48px';
    input.style.maxHeight = '160px';
    input.style.overflowY = 'hidden';
    input.style.overflowX = 'hidden';
    // Clean the action text before setting it
    input.value = cleanQuestionText(action);
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
                const questions = content.questions || [];
                // Clean each question to remove hyphens and extra spaces
                return questions.map(q => cleanQuestionText(q));
            }
        }
        
        return null;
    } catch (error) {
        console.error('Failed to fetch related questions:', error);
        return null;
    }
}

async function fetchQuickActions() {
    const apiStart = Date.now();
    console.log('API call started at:', apiStart);
    
    try {
        const response = await fetch(`${API_BASE}/quick_actions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const fetchEnd = Date.now();
        console.log('Fetch completed at:', fetchEnd, 'Fetch duration:', fetchEnd - apiStart, 'ms');
        
        const data = await response.json();
        const parseEnd = Date.now();
        console.log('JSON parsed at:', parseEnd, 'Parse duration:', parseEnd - fetchEnd, 'ms');
        
        if (data.error) {
            console.error('Error fetching quick actions:', data.error);
            return null;
        } else if (data.result && data.result.content) {
            const content = data.result.content[0];
            if (content.text === 'quick_actions') {
                const finalTime = Date.now();
                console.log('Quick Actions function completed at:', finalTime, 'Total API duration:', finalTime - apiStart, 'ms');
                const questions = content.questions || [];
                // Clean each question to remove hyphens and extra spaces
                return questions.map(q => cleanQuestionText(q));
            }
        }
        return null;
    } catch (error) {
        console.error('Failed to fetch quick actions:', error);
        return null;
    }
}

function startQuickActionsLoading() {
    const toggleBtn = document.getElementById('toggle-quick-actions');
    const loadingIcon = document.getElementById('toggle-loading-icon');
    const arrowIcon = document.getElementById('toggle-arrow-icon');
    
    if (toggleBtn) {
        toggleBtn.classList.add('loading');
        toggleBtn.disabled = true; // Disable the button during loading
    }
    
    if (loadingIcon) {
        loadingIcon.style.display = 'flex';
    }
    
    if (arrowIcon) {
        arrowIcon.style.display = 'none';
    }
}

function showQuickActions() {
    // Prevent multiple calls
    if (quickActionsShown) {
        return;
    }
    quickActionsShown = true;
    
    const toggleBtn = document.getElementById('toggle-quick-actions');
    const loadingIcon = document.getElementById('toggle-loading-icon');
    const arrowIcon = document.getElementById('toggle-arrow-icon');
    
    if (toggleBtn) {
        toggleBtn.classList.remove('loading');
        toggleBtn.disabled = false; // Re-enable the button after loading
        // Add a brief success state
        toggleBtn.classList.add('loaded');
        setTimeout(() => {
            toggleBtn.classList.remove('loaded');
        }, 500);
    }
    
    if (loadingIcon) {
        loadingIcon.style.display = 'none';
    }
    
    if (arrowIcon) {
        arrowIcon.style.display = 'inline';
        // Add a smooth fade-in effect
        arrowIcon.style.opacity = '0';
        arrowIcon.style.transform = 'scale(0.8)';
        setTimeout(() => {
            arrowIcon.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
            arrowIcon.style.opacity = '1';
            arrowIcon.style.transform = 'scale(1)';
        }, 50);
    }
}



function autoOpenQuickActionsPanel() {
    const quickActionsContent = document.getElementById('quick-actions-content');
    const arrowIcon = document.getElementById('toggle-arrow-icon');
    
    console.log('autoOpenQuickActionsPanel called');
    console.log('quickActionsContent exists:', !!quickActionsContent);
    console.log('starterLoading:', starterLoading);
    console.log('starterQuestions length:', starterQuestions ? starterQuestions.length : 0);
    
    if (quickActionsContent) {
        // Only auto-open if we have questions loaded and loading is complete
        if (starterQuestions && starterQuestions.length > 0 && !starterLoading) {
            // Add a small delay for better UX
            setTimeout(() => {
                // Open the panel automatically with smooth animation
                console.log('Setting panel display to block');
                quickActionsContent.style.setProperty('display', 'block', 'important');
                quickActionsContent.style.animation = 'slideDownEnhanced 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)';
                console.log('Panel display style is now:', quickActionsContent.style.display);
                
                // Update arrow to show panel is open (down arrow when open)
                if (arrowIcon) {
                    arrowIcon.textContent = '▼';
                    arrowIcon.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    arrowIcon.style.transform = 'rotate(180deg)';
                }
                
                // Add success state class for enhanced animation (shorter duration)
                quickActionsContent.classList.add('loaded');
                setTimeout(() => {
                    quickActionsContent.classList.remove('loaded');
                }, 300);
                
                console.log('Quick Actions panel auto-opened with', starterQuestions.length, 'questions');
            }, 200); // Small delay for better visual flow
        } else {
            // Keep panel closed if no questions loaded or still loading
            quickActionsContent.style.display = 'none';
            if (arrowIcon) {
                arrowIcon.textContent = '▲';
                arrowIcon.style.transform = 'rotate(0deg)';
            }
            console.log('Quick Actions panel kept closed - no questions loaded or still loading');
        }
    } else {
        console.log('quickActionsContent element not found');
    }
}

function updateQuickActionsDisplay() {
    const quickActionsContent = document.getElementById('quick-actions-content');
    const quickActionsHeader = document.querySelector('.quick-actions-header h3');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeToggleText = modeToggleBtn.querySelector('.mode-toggle-text');
    
    console.log('updateQuickActionsDisplay called');
    console.log('starterLoading:', starterLoading);
    console.log('starterQuestions:', starterQuestions);
    console.log('starterQuestions length:', starterQuestions ? starterQuestions.length : 0);
    
    // Check if panel is collapsed
    const isPanelCollapsed = quickActionsContent.style.display === 'none';
    
    // Show/hide mode toggle button based on conversation state and panel visibility
    if (conversationStarted && relatedQuestions.length > 0 && !isPanelCollapsed && !isGenerating) {
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
        // Starter quick actions section
        quickActionsHeader.textContent = 'Quick Actions';
        if (conversationStarted && relatedQuestions.length > 0) {
            modeToggleText.textContent = 'Show Related Questions';
        }
        // Show loading placeholders while loading OR if no data received
        if (starterLoading || !starterQuestions || starterQuestions.length === 0) {
            // Show 4 loading gifs as placeholders
            const items = [0,1,2,3].map(() => `
                <div class="qa-loading-item"><img src="img/quick_actions_loading.gif" alt="Loading..." class="qa-loading-gif"></div>
            `).join('');
            quickActionsContent.innerHTML = `<div class="qa-loading-grid">${items}</div>`;
            return;
        }
        
        // Show actual quick actions when data is loaded
        if (starterQuestions && starterQuestions.length > 0) {
            const icons = [
                `<img src="img/graph.gif" alt="Graph" width="40" height="40">`,
                `<img src="img/done.gif" alt="Done" width="40" height="40">`,
                `<img src="img/eyes.gif" alt="Eyes" width="40" height="40">`,
                `<img src="img/target.gif" alt="Target" width="40" height="40">`
            ];
            const grid = starterQuestions.slice(0, 4).map((q, i) => `
                <button class="quick-action-btn" onclick="quickAction('${q.replace(/'/g, "\\'")}')">
                    <div class="quick-action-icon" style="background: transparent;">
                        ${icons[i % icons.length]}
                    </div>
                    <div class="quick-action-text">${q}</div>
                </button>
            `).join('');
            quickActionsContent.innerHTML = `<div class="quick-actions-grid">${grid}</div>`;
        }
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
        // Make header compact after first message
        const header = document.querySelector('.header');
        if (header) {
            header.classList.add('compact');
        }
    }
    
    // Set generation state
    isGenerating = true;
    currentGenerationController = new AbortController();
    setQuickActionsDisabled(true);
    
    // Make input read-only and show stop button (avoids browser disabled styling shifts)
    input.readOnly = true;
    sendButton.style.display = 'none';
    stopButton.style.display = 'flex';
    
    // Add user message
    addMessage('user', message);
    input.value = '';
    autoResize(input);
    

    
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
        input.readOnly = false;
        sendButton.style.display = 'flex';
        stopButton.style.display = 'none';
        input.focus();
        autoResize(input);
        setQuickActionsDisabled(false);
    }
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
    

}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 160);
    textarea.style.height = newHeight + 'px';
    // Hide scrollbars when not needed
    if (newHeight <= 48 || textarea.scrollHeight <= newHeight) {
        textarea.style.overflowY = 'hidden';
    } else {
        textarea.style.overflowY = 'auto';
    }
    // Ensure no horizontal overflow
    textarea.style.overflowX = 'hidden';
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
        document.getElementById('message-input').readOnly = false;
        
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
        // Re-enable quick actions and restore input sizing/scroll
        setQuickActionsDisabled(false);
    }
}



function toggleQuickActions(event) {
    // Prevent event bubbling if called from button
    if (event) {
        event.stopPropagation();
    }
    
    // Don't allow toggling while loading, generating, or disabled
    const toggleBtn = document.getElementById('toggle-quick-actions');
    if (toggleBtn && (toggleBtn.classList.contains('loading') || toggleBtn.disabled || isGenerating)) {
        return;
    }
    
    const content = document.getElementById('quick-actions-content');
    const toggleIcon = document.querySelector('.toggle-icon');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const isHidden = content.style.display === 'none';
    
    if (isHidden) {
        // Panel is currently hidden, so we're opening it
        const arrowIcon = document.getElementById('toggle-arrow-icon');
        if (arrowIcon) arrowIcon.textContent = '▼'; // Set arrow to down when panel is open
        content.style.display = 'block';
        content.style.animation = 'slideDown 0.3s ease-out';
        // Show mode toggle button if we have related questions
        if (conversationStarted && relatedQuestions.length > 0) {
            modeToggleBtn.style.display = 'flex';
        }
    } else {
        // Panel is currently visible, so we're closing it
        const arrowIcon = document.getElementById('toggle-arrow-icon');
        if (arrowIcon) arrowIcon.textContent = '▲'; // Set arrow to up when panel is closed
        content.style.display = 'none';
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
            
            // Clear the messages display and show animated greeting
            const messagesEl = document.getElementById('messages');
            messagesEl.innerHTML = '';
            await showInitialGreeting();
            
            // Reset quick actions to default
            updateQuickActionsDisplay();
        }
    } catch (error) {
        alert('Failed to clear history. Check if the API is running.');
    }
}