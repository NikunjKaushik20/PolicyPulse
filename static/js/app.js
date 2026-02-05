/**
 * PolicyPulse - ChatGPT-Style UI
 * Main JavaScript Application
 */

// State Management
const state = {
    isLoggedIn: false,
    currentUser: null,
    conversations: [],
    currentConversation: null,
    messages: [],
    isRecording: false,
    uploadedFile: null,
    mediaRecorder: null
};

// API Base URL
const API_BASE = '';

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const appContainer = document.getElementById('appContainer');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const conversationList = document.getElementById('conversationList');
const welcomeScreen = document.getElementById('welcomeScreen');
const messagesContainer = document.getElementById('messagesContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const inputWrapper = document.getElementById('inputWrapper');
const recordingIndicator = document.getElementById('recordingIndicator');
const uploadPreview = document.getElementById('uploadPreview');
const uploadFileName = document.getElementById('uploadFileName');
const userAvatar = document.getElementById('userAvatar');
const userName = document.getElementById('userName');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    // Check for saved session
    const savedUser = localStorage.getItem('policyPulseUser');
    if (savedUser) {
        state.currentUser = JSON.parse(savedUser);
        state.isLoggedIn = true;
        showApp();
    }
    
    // Load conversations from localStorage
    const savedConversations = localStorage.getItem('policyPulseConversations');
    if (savedConversations) {
        state.conversations = JSON.parse(savedConversations);
        renderConversations();
    }
    
    // Focus input on load
    if (state.isLoggedIn) {
        messageInput.focus();
    }
});

// Mock Login
function mockLogin(method) {
    const users = {
        google: { name: 'Jai Sharma', avatar: 'JS', email: 'jai.sharma@gmail.com' },
        phone: { name: 'Mobile User', avatar: 'MU', phone: '+91 98765 43210' },
        email: { name: 'Email User', avatar: 'EU', email: 'user@example.com' },
        aadhaar: { name: 'Verified Citizen', avatar: 'VC', aadhaar: 'XXXX-XXXX-1234' },
        guest: { name: 'Guest User', avatar: 'G', isGuest: true }
    };
    
    state.currentUser = users[method] || users.guest;
    state.isLoggedIn = true;
    
    // Save to localStorage
    localStorage.setItem('policyPulseUser', JSON.stringify(state.currentUser));
    
    // Show app
    showApp();
}

// Show App
function showApp() {
    loginScreen.classList.add('hidden');
    appContainer.classList.add('active');
    
    // Update user info
    userAvatar.textContent = state.currentUser.avatar;
    userName.textContent = state.currentUser.name;
    
    // Focus input
    setTimeout(() => messageInput.focus(), 100);
}

// Toggle Sidebar (Mobile)
function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
}

// Start New Chat
function startNewChat() {
    // Save current conversation if has messages
    if (state.messages.length > 0 && state.currentConversation) {
        saveCurrentConversation();
    }
    
    // Reset state
    state.currentConversation = {
        id: Date.now(),
        title: 'New Conversation',
        timestamp: new Date().toISOString(),
        messages: []
    };
    state.messages = [];
    
    // Update UI
    welcomeScreen.style.display = 'flex';
    messagesContainer.classList.remove('active');
    messagesContainer.innerHTML = '';
    messageInput.value = '';
    clearUpload();
    
    // Update conversation list
    updateActiveConversation();
    
    // Close sidebar on mobile
    if (window.innerWidth < 768) {
        toggleSidebar();
    }
    
    messageInput.focus();
}

// Send Quick Query
function sendQuickQuery(query) {
    messageInput.value = query;
    sendMessage();
}

// Handle Key Press
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Send Message
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text && !state.uploadedFile) return;
    
    // Hide welcome screen
    welcomeScreen.style.display = 'none';
    messagesContainer.classList.add('active');
    
    // Create conversation if needed
    if (!state.currentConversation) {
        const title = state.uploadedFile 
            ? `Document: ${state.uploadedFile.name}` 
            : text.substring(0, 30) + (text.length > 30 ? '...' : '');
        state.currentConversation = {
            id: Date.now(),
            title: title,
            timestamp: new Date().toISOString(),
            messages: []
        };
        state.conversations.unshift(state.currentConversation);
        renderConversations();
    }
    
    // Add user message
    const userMessage = {
        id: Date.now(),
        role: 'user',
        content: text || `📄 Uploaded: ${state.uploadedFile?.name}`,
        timestamp: new Date().toISOString(),
        file: state.uploadedFile ? state.uploadedFile.name : null
    };
    
    state.messages.push(userMessage);
    renderMessage(userMessage);
    
    // Clear input
    messageInput.value = '';
    const uploadedFile = state.uploadedFile;
    clearUpload();
    
    // Scroll to bottom
    scrollToBottom();
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        let assistantMessage;
        
        // Check if we have an uploaded document to process
        if (uploadedFile) {
            // Process document first
            const docResult = await processDocument(uploadedFile);
            
            if (docResult.success) {
                // Build eligibility check based on extracted data
                const eligibilityResult = await checkEligibilityFromDocument(docResult);
                
                assistantMessage = {
                    id: Date.now(),
                    role: 'assistant',
                    content: buildDocumentResponse(docResult, eligibilityResult),
                    timestamp: new Date().toISOString(),
                    structured: {
                        documentType: docResult.document_type,
                        extractedFields: docResult.extracted_fields,
                        eligibleSchemes: eligibilityResult.eligible_schemes || [],
                        allSchemes: eligibilityResult
                    }
                };
            } else {
                assistantMessage = {
                    id: Date.now(),
                    role: 'assistant',
                    content: `❌ Could not process the document: ${docResult.error || 'Unknown error'}. Please upload a clearer image.`,
                    timestamp: new Date().toISOString()
                };
            }
        } else {
            // Standard text query
            const response = await fetch(`${API_BASE}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_text: text,
                    top_k: 5,
                    language: 'en'
                })
            });
            
            const data = await response.json();
            
            assistantMessage = {
                id: Date.now(),
                role: 'assistant',
                content: data.final_answer || 'I found some relevant information for you.',
                timestamp: new Date().toISOString(),
                structured: formatStructuredResponse(data)
            };
        }
        
        hideTypingIndicator();
        state.messages.push(assistantMessage);
        renderMessage(assistantMessage);
        
        // Update conversation title from first query
        if (state.messages.length === 2 && !uploadedFile) {
            state.currentConversation.title = text.substring(0, 30) + (text.length > 30 ? '...' : '');
            renderConversations();
        }
        
        saveCurrentConversation();
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        
        // Show error or mock response
        const mockResponse = generateMockResponse(text || 'document eligibility');
        const assistantMessage = {
            id: Date.now(),
            role: 'assistant',
            content: mockResponse.content,
            timestamp: new Date().toISOString(),
            structured: mockResponse.structured
        };
        
        state.messages.push(assistantMessage);
        renderMessage(assistantMessage);
        saveCurrentConversation();
    }
    
    scrollToBottom();
}

// Process uploaded document via API
async function processDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/document/upload`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    } catch (error) {
        console.error('Document processing error:', error);
        return { success: false, error: error.message };
    }
}

// Check eligibility based on extracted document data
async function checkEligibilityFromDocument(docResult) {
    const fields = docResult.extracted_fields || {};
    
    // Build profile from extracted data
    const profile = {
        age: fields.age || 30,
        income: fields.income || 100000,
        occupation: '',
        location_type: fields.locality || 'rural',
        category: 'general',
        land_ownership: docResult.document_type === 'land_record',
        has_toilet: true,
        willingness_manual_work: true,
        in_smart_city: fields.locality === 'urban'
    };
    
    try {
        const response = await fetch(`${API_BASE}/eligibility/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });
        
        const apiSchemes = await response.json();
        
        // Map API response format to display format
        // API returns: { policy_id, policy_name, description, benefits, documents_required, ... }
        // Display expects: { name, status, reason }
        const eligible_schemes = (Array.isArray(apiSchemes) ? apiSchemes : []).map(scheme => ({
            name: scheme.policy_name || scheme.policy_id || 'Unknown Scheme',
            status: scheme.priority === 'HIGH' ? 'eligible' : 'likely_eligible',
            reason: scheme.benefits || scheme.description || 'You may qualify for this scheme',
            documents: scheme.documents_required || [],
            link: scheme.application_link || ''
        }));
        
        return { eligible_schemes };
    } catch (error) {
        console.error('Eligibility check error:', error);
        // Return mock eligibility based on document type
        return getMockEligibility(docResult.document_type, fields);
    }
}

// Get mock eligibility when API unavailable
function getMockEligibility(docType, fields) {
    const age = fields.age || 30;
    const schemes = [];
    
    // Common schemes for Aadhaar holders
    if (docType === 'aadhaar') {
        schemes.push({
            name: 'Jan Dhan Yojana',
            status: 'eligible',
            reason: 'Aadhaar verified - can open zero balance account'
        });
        schemes.push({
            name: 'RTI Filing',
            status: 'eligible',
            reason: 'Aadhaar is sufficient ID proof'
        });
        
        if (age >= 18 && age <= 40) {
            schemes.push({
                name: 'Mudra Loan',
                status: 'eligible',
                reason: 'Age eligible for small business loan up to ₹10 lakh'
            });
        }
        
        if (age >= 60) {
            schemes.push({
                name: 'Atal Pension Yojana',
                status: 'eligible',
                reason: 'Senior citizen pension scheme'
            });
            schemes.push({
                name: 'PMJAY (Ayushman Bharat)',
                status: 'likely_eligible',
                reason: 'Senior citizens get priority - income verification needed'
            });
        }
        
        if (age >= 18 && age <= 50) {
            schemes.push({
                name: 'PM-KISAN',
                status: 'possibly_eligible',
                reason: 'Need land records to confirm farmer status'
            });
            schemes.push({
                name: 'NREGA',
                status: 'possibly_eligible',
                reason: 'Aadhaar linked - apply at local Gram Panchayat'
            });
        }
    }
    
    if (docType === 'income_certificate') {
        const income = fields.income || 0;
        if (income < 250000) {
            schemes.push({
                name: 'Ayushman Bharat (PM-JAY)',
                status: 'eligible',
                reason: `Annual income ₹${income.toLocaleString()} is below threshold`
            });
        }
    }
    
    if (docType === 'land_record') {
        schemes.push({
            name: 'PM-KISAN',
            status: 'eligible',
            reason: 'Land ownership verified - ₹6,000/year in 3 installments'
        });
        schemes.push({
            name: 'Kisan Credit Card',
            status: 'eligible',
            reason: 'Agricultural credit up to ₹3 lakh at 4% interest'
        });
        schemes.push({
            name: 'PM Fasal Bima Yojana',
            status: 'eligible',
            reason: 'Crop insurance at subsidized premium'
        });
    }
    
    return {
        eligible_schemes: schemes,
        profile_summary: {
            document_type: docType,
            age: age,
            extracted_info: fields
        }
    };
}

// Build response text from document processing
function buildDocumentResponse(docResult, eligibilityResult) {
    const docType = docResult.document_type?.toUpperCase() || 'DOCUMENT';
    const fields = docResult.extracted_fields || {};
    const schemes = eligibilityResult.eligible_schemes || [];
    
    let response = `✅ **${docType} Card Processed Successfully**\n\n`;
    
    // Show extracted info
    response += `**Extracted Information:**\n`;
    if (fields.name) response += `• Name: ${fields.name}\n`;
    if (fields.aadhaar_number) response += `• Aadhaar: XXXX-XXXX-${fields.aadhaar_number.slice(-4)}\n`;
    if (fields.dob) response += `• DOB: ${fields.dob}\n`;
    if (fields.age) response += `• Age: ${fields.age} years\n`;
    if (fields.locality) response += `• Location: ${fields.locality}\n`;
    if (fields.income) response += `• Annual Income: ₹${fields.income.toLocaleString()}\n`;
    
    response += `\n**Based on your profile, you may be eligible for these schemes:**\n`;
    
    return response;
}

// Format Structured Response
function formatStructuredResponse(data) {
    if (!data || !data.retrieved_points || data.retrieved_points.length === 0) {
        return null;
    }
    
    const points = data.retrieved_points.slice(0, 3);
    const policyId = points[0]?.policy_id || 'UNKNOWN';
    const year = points[0]?.year || 'N/A';
    
    return {
        policyId,
        year,
        confidence: data.confidence_score || 0,
        sources: points.map(p => ({
            content: p.content_preview?.substring(0, 150) + '...',
            year: p.year,
            modality: p.modality
        }))
    };
}

// Generate Mock Response (when API unavailable)
function generateMockResponse(query) {
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('pm kisan') || lowerQuery.includes('pm-kisan')) {
        return {
            content: 'PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) is a government scheme that provides income support to farmer families.',
            structured: {
                policyId: 'PM-KISAN',
                eligibility: true,
                benefits: [
                    '₹6,000 per year in three installments',
                    'Direct bank transfer to beneficiaries',
                    'Support for small and marginal farmers'
                ],
                documents: [
                    'Aadhaar Card',
                    'Bank Account Details',
                    'Land Records'
                ],
                lastUpdated: '2024',
                source: 'pmkisan.gov.in'
            }
        };
    }
    
    if (lowerQuery.includes('ayushman') || lowerQuery.includes('health')) {
        return {
            content: 'Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PM-JAY) is the world\'s largest health insurance scheme.',
            structured: {
                policyId: 'AYUSHMAN-BHARAT',
                eligibility: true,
                benefits: [
                    '₹5 lakh health cover per family per year',
                    'Cashless and paperless treatment',
                    'Coverage for 1,929 procedures'
                ],
                documents: [
                    'Aadhaar Card',
                    'Ration Card',
                    'Income Certificate'
                ],
                lastUpdated: '2024',
                source: 'pmjay.gov.in'
            }
        };
    }
    
    if (lowerQuery.includes('education') || lowerQuery.includes('scholarship') || lowerQuery.includes('loan')) {
        return {
            content: 'There are multiple education schemes available including scholarships and education loans with subsidized interest rates.',
            structured: {
                policyId: 'NEP-EDUCATION',
                eligibility: null,
                benefits: [
                    'Central Sector Scholarship for college students',
                    'National Means-cum-Merit Scholarship',
                    'Education loans at 4% interest (EWS families)'
                ],
                documents: [
                    'Income Certificate',
                    'Mark Sheets',
                    'Admission Letter'
                ],
                lastUpdated: '2024',
                source: 'scholarships.gov.in'
            }
        };
    }
    
    if (lowerQuery.includes('startup') || lowerQuery.includes('business')) {
        return {
            content: 'Startup India initiative provides various benefits for entrepreneurs including tax exemptions and easy compliance.',
            structured: {
                policyId: 'STARTUP-INDIA',
                eligibility: true,
                benefits: [
                    '3-year tax exemption',
                    'Self-certification for labor and environment laws',
                    'Fast-track patent application at reduced costs'
                ],
                documents: [
                    'Business Plan',
                    'Incorporation Certificate',
                    'PAN Card'
                ],
                lastUpdated: '2024',
                source: 'startupindia.gov.in'
            }
        };
    }
    
    // Default response
    return {
        content: `I found information related to your query about "${query}". Based on the available policy data, here are some relevant details.`,
        structured: {
            policyId: 'GENERAL',
            benefits: [
                'Multiple central and state schemes may apply',
                'Eligibility varies based on your profile',
                'Documents required depend on specific scheme'
            ],
            documents: [
                'Aadhaar Card',
                'Address Proof',
                'Income Certificate'
            ],
            lastUpdated: '2024',
            source: 'india.gov.in'
        }
    };
}

// Render Message
function renderMessage(message) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${message.role}`;
    
    // Convert markdown-like syntax to HTML
    let formattedContent = message.content
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    
    let contentHTML = `
        <div class="message-avatar">${message.role === 'user' ? '👤' : '🤖'}</div>
        <div class="message-content">
            <div class="message-text">${formattedContent}</div>
    `;
    
    // Add structured response if available
    if (message.structured) {
        const s = message.structured;
        
        // Handle document upload - show eligible schemes
        if (s.eligibleSchemes && s.eligibleSchemes.length > 0) {
            contentHTML += `
                <div class="response-section">
                    <div class="response-section-title">🎯 ELIGIBLE SCHEMES (${s.eligibleSchemes.length} found)</div>
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">
                        ${s.eligibleSchemes.map(scheme => `
                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 600; font-size: 15px; color: #1e293b; margin-bottom: 4px;">
                                            ✓ ${scheme.name}
                                        </div>
                                        <span style="display: inline-block; font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; background: ${getStatusColor(scheme.status)}; color: ${scheme.status === 'eligible' ? '#059669' : '#0369a1'};">
                                            ${getStatusText(scheme.status)}
                                        </span>
                                    </div>
                                </div>
                                <div style="font-size: 13px; color: #475569; line-height: 1.5; margin-bottom: 12px;">
                                    ${scheme.reason}
                                </div>
                                ${scheme.link ? `
                                    <a href="${scheme.link}" target="_blank" rel="noopener" 
                                       style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: linear-gradient(135deg, #1a56db 0%, #3b82f6 100%); color: white; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 500; transition: all 0.2s;">
                                        Apply Now →
                                    </a>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            
            // Show next steps
            contentHTML += `
                <div class="response-section" style="background: #f0fdf4; border-color: #86efac;">
                    <div class="response-section-title">📝 Next Steps</div>
                    <ul class="response-list">
                        <li>Click "Apply Now" to visit the official portal</li>
                        <li>Carry your Aadhaar and required documents</li>
                        <li>Or visit your nearest Common Service Centre (CSC)</li>
                    </ul>
                </div>
            `;
        }
        
        // Standard eligibility badge
        else if (s.eligibility !== undefined && s.eligibility !== null) {
            contentHTML += `
                <div class="response-section">
                    <div class="response-section-title">📋 Eligibility Status</div>
                    <span class="eligibility-badge ${s.eligibility ? 'eligible' : 'not-eligible'}">
                        ${s.eligibility ? '✓ Likely Eligible' : '✗ May Not Be Eligible'}
                    </span>
                </div>
            `;
        }
        
        // Benefits
        if (s.benefits && s.benefits.length > 0) {
            contentHTML += `
                <div class="response-section">
                    <div class="response-section-title">💰 Benefits</div>
                    <ul class="response-list">
                        ${s.benefits.map(b => `<li>${b}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Documents Required
        if (s.documents && s.documents.length > 0) {
            contentHTML += `
                <div class="response-section">
                    <div class="response-section-title">📄 Required Documents</div>
                    <ul class="response-list">
                        ${s.documents.map(d => `<li>${d}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Source
        if (s.source) {
            contentHTML += `
                <div class="source-link">
                    <strong>Source:</strong> <a href="https://${s.source}" target="_blank">${s.source}</a>
                    ${s.lastUpdated ? ` • Last Updated: ${s.lastUpdated}` : ''}
                </div>
            `;
        }
    }
    
    contentHTML += '</div>';
    messageEl.innerHTML = contentHTML;
    messagesContainer.appendChild(messageEl);
}

// Helper functions for scheme status display
function getStatusColor(status) {
    switch(status) {
        case 'eligible': return '#d1fae5';
        case 'likely_eligible': return '#dbeafe';
        case 'possibly_eligible': return '#fef3c7';
        default: return '#e2e8f0';
    }
}

function getStatusText(status) {
    switch(status) {
        case 'eligible': return '✓ Eligible';
        case 'likely_eligible': return '◐ Likely Eligible';
        case 'possibly_eligible': return '? Check Required';
        default: return status;
    }
}

// Show/Hide Typing Indicator
function showTypingIndicator() {
    typingIndicator.classList.add('active');
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.classList.remove('active');
}

// Scroll to Bottom
function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Voice Recording
async function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.mediaRecorder = new MediaRecorder(stream);
        const chunks = [];
        
        state.mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
        state.mediaRecorder.onstop = async () => {
            const blob = new Blob(chunks, { type: 'audio/webm' });
            await processAudio(blob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        state.mediaRecorder.start();
        state.isRecording = true;
        
        // Update UI
        inputWrapper.classList.add('recording');
        recordingIndicator.classList.add('active');
        messageInput.style.display = 'none';
        
    } catch (error) {
        console.error('Microphone error:', error);
        alert('Could not access microphone. Please check permissions.');
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.isRecording) {
        state.mediaRecorder.stop();
        state.isRecording = false;
        
        // Update UI
        inputWrapper.classList.remove('recording');
        recordingIndicator.classList.remove('active');
        messageInput.style.display = '';
    }
}

async function processAudio(blob) {
    // Show processing indicator
    messageInput.placeholder = 'Processing audio...';
    
    try {
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');
        
        const response = await fetch(`${API_BASE}/process-audio`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.transcription) {
            messageInput.value = data.transcription;
            sendMessage();
        }
    } catch (error) {
        console.error('Audio processing error:', error);
        messageInput.placeholder = 'Ask about any government scheme...';
        alert('Could not process audio. Please try typing instead.');
    }
    
    messageInput.placeholder = 'Ask about any government scheme...';
}

// File Upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    state.uploadedFile = file;
    uploadFileName.textContent = file.name;
    uploadPreview.classList.add('active');
    
    // Focus input
    messageInput.focus();
    messageInput.placeholder = `Describe what you need from ${file.name}...`;
}

function clearUpload() {
    state.uploadedFile = null;
    uploadPreview.classList.remove('active');
    document.getElementById('fileInput').value = '';
    messageInput.placeholder = 'Ask about any government scheme...';
}

// Conversation Management
function renderConversations() {
    conversationList.innerHTML = '';
    
    state.conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = `conversation-item ${state.currentConversation?.id === conv.id ? 'active' : ''}`;
        item.onclick = () => loadConversation(conv.id);
        
        item.innerHTML = `
            <span class="conversation-item-icon">💬</span>
            <span class="conversation-item-text">${conv.title}</span>
        `;
        
        conversationList.appendChild(item);
    });
}

function updateActiveConversation() {
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
}

function loadConversation(id) {
    const conv = state.conversations.find(c => c.id === id);
    if (!conv) return;
    
    state.currentConversation = conv;
    state.messages = conv.messages || [];
    
    // Update UI
    welcomeScreen.style.display = 'none';
    messagesContainer.classList.add('active');
    messagesContainer.innerHTML = '';
    
    // Render messages
    state.messages.forEach(msg => renderMessage(msg));
    
    // Update active state
    renderConversations();
    
    // Close sidebar on mobile
    if (window.innerWidth < 768) {
        toggleSidebar();
    }
    
    scrollToBottom();
}

function saveCurrentConversation() {
    if (!state.currentConversation) return;
    
    state.currentConversation.messages = state.messages;
    
    // Update in conversations array
    const index = state.conversations.findIndex(c => c.id === state.currentConversation.id);
    if (index === -1) {
        state.conversations.unshift(state.currentConversation);
    } else {
        state.conversations[index] = state.currentConversation;
    }
    
    // Save to localStorage
    localStorage.setItem('policyPulseConversations', JSON.stringify(state.conversations));
    renderConversations();
}

// Quick Access Handlers
function handleQuickAccess(type) {
    switch(type) {
        case 'saved':
            alert('Saved queries feature coming soon!');
            break;
        case 'language':
            alert('Language settings: Currently supporting Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and English.');
            break;
    }
}

// Settings
function openSettings() {
    alert('Settings panel coming soon!\n\nCurrent user: ' + state.currentUser?.name);
}

// Logout
function logout() {
    localStorage.removeItem('policyPulseUser');
    state.isLoggedIn = false;
    state.currentUser = null;
    
    loginScreen.classList.remove('hidden');
    appContainer.classList.remove('active');
}

// Handle window resize
window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    }
});
