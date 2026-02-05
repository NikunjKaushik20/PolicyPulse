// API Client for PolicyPulse Backend

const API_BASE_URL = window.location.origin;

// Helper: Make API request
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Request Failed:', error);
    throw error;
  }
}

// Show loading spinner
function showLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = '<div class="flex-center"><div class="spinner"></div></div>';
  }
}

// Show error message
function showError(elementId, message) {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = `
      <div class="card" style="background: var(--error); color: white;">
        <h4>❌ Error</h4>
        <p>${message}</p>
      </div>
    `;
  }
}

// API Methods

// Query policy data
async function queryPolicy(query, language = 'en') {
  return apiRequest('/query', {
    method: 'POST',
    body: JSON.stringify({
      query_text: query,
      top_k: 5,
      language: language
    })
  });
}

// Check eligibility
async function checkEligibility(userProfile) {
  return apiRequest('/eligibility/check', {
    method: 'POST',
    body: JSON.stringify(userProfile)
  });
}

// Get drift analysis
async function getDriftAnalysis(policyId) {
  return apiRequest(`/drift/${policyId}`);
}

// Get recommendations
async function getRecommendations(policyId, count = 3) {
  return apiRequest(`/recommendations/${policyId}?count=${count}`);
}

// Translate text
async function translateText(text, targetLang) {
  return apiRequest('/translate', {
    method: 'POST',
    body: JSON.stringify({
      text: text,
      target_lang: targetLang
    })
  });
}

// Get text-to-speech audio
async function getTextToSpeech(text, language = 'hi') {
  const response = await fetch(`${API_BASE_URL}/tts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: text,
      lang: language
    })
  });
  
  if (!response.ok) {
    throw new Error('TTS request failed');
  }
  
  return await response.blob();
}

// Play audio from blob
function playAudio(audioBlob) {
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
  
  // Clean up URL after playing
  audio.onended = () => URL.revokeObjectURL(audioUrl);
}

// Get stats
async function getStats() {
  return apiRequest('/stats');
}

// Export API client
window.apiClient = {
  queryPolicy,
  checkEligibility,
  getDriftAnalysis,
  getRecommendations,
  translateText,
  getTextToSpeech,
  playAudio,
  getStats,
  showLoading,
  showError
};
