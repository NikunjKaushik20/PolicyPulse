// Voice API using Web Speech API (browser-built-in, free)

let recognition = null;
let isListening = false;

// Initialize speech recognition
function initSpeechRecognition() {
  // Check browser support
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    console.error('Speech Recognition not supported in this browser');
    return null;
  }
  
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'hi-IN'; // Default to Hindi
  
  return recognition;
}

// Start listening
function startListening(language = 'hi-IN', onResult, onError) {
  if (!recognition) {
    recognition = initSpeechRecognition();
  }
  
  if (!recognition) {
    if (onError) onError('Speech recognition not supported');
    return;
  }
  
  // Set language
  recognition.lang = language;
  
  // Event handlers
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    if (onResult) onResult(transcript);
  };
  
  recognition.onerror = (event) => {
    if (onError) onError(event.error);
    isListening = false;
  };
  
  recognition.onend = () => {
    isListening = false;
  };
  
  // Start
  try {
    recognition.start();
    isListening = true;
  } catch (error) {
    if (onError) onError(error.message);
  }
}

// Stop listening
function stopListening() {
  if (recognition && isListening) {
    recognition.stop();
    isListening = false;
  }
}

// Get language code for speech recognition
function getRecognitionLanguage(lang) {
  const langMap = {
    'en': 'en-US',
    'hi': 'hi-IN',
    'ta': 'ta-IN',
    'te': 'te-IN',
    'bn': 'bn-IN',
    'mr': 'mr-IN',
    'gu': 'gu-IN',
    'kn': 'kn-IN',
    'ml': 'ml-IN',
    'pa': 'pa-IN'
  };
  
  return langMap[lang] || 'en-US';
}

// Check if speech recognition is supported
function isSpeechRecognitionSupported() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

// Export voice API
window.voiceAPI = {
  startListening,
  stopListening,
  isListening: () => isListening,
  isSpeechRecognitionSupported,
  getRecognitionLanguage
};
