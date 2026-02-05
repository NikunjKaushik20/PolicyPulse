import React, { useState, useRef } from 'react';
import { Send, Mic, Paperclip, Loader2, StopCircle } from 'lucide-react';
import axios from 'axios';

const InputBar = ({ onSendMessage, isLoading, onUploadComplete, t, lang, setLang }) => {
  const [query, setQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleInput = (e) => {
    setQuery(e.target.value);
    e.target.style.height = 'auto'; 
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading || isUploading) return;
    
    onSendMessage(query);
    setQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // --- Voice Input Logic ---
  const recognitionRef = useRef(null);

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert("Voice input is not supported in this browser. Try Chrome or Edge.");
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    
    recognition.continuous = false;
    recognition.interimResults = true; 
    recognition.lang = lang; // Use global lang from props

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    
    recognition.onerror = (event) => {
        console.error("Speech error:", event.error);
        setIsListening(false);
    };
    
    recognition.onresult = (event) => {
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
          }
      }
      if (finalTranscript) {
           setQuery(prev => prev + (prev ? " " : "") + finalTranscript);
           setTimeout(() => {
                if(textareaRef.current) {
                    textareaRef.current.style.height = 'auto';
                    textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
                }
           }, 10);
      }
    };

    try {
        recognition.start();
    } catch (e) {
        console.error("Start error:", e);
    }
  };

  const handleFileClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await axios.post(`${baseUrl}/document/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (onUploadComplete) onUploadComplete(res.data);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload document.");
    } finally {
      setIsUploading(false);
      e.target.value = null; 
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full p-4 relative">
      <form 
        onSubmit={handleSubmit}
        className={`
            relative flex items-end gap-2 p-3 
            bg-white dark:bg-gray-800 
            border shadow-sm rounded-2xl transition-all
            ${isListening 
                ? 'border-red-400 ring-2 ring-red-100 dark:ring-red-900/30' 
                : 'border-gray-200 dark:border-gray-700 focus-within:ring-2 focus-within:ring-indigo-100 dark:focus-within:ring-indigo-900/30 focus-within:border-indigo-400 dark:focus-within:border-indigo-600'
            }
        `}
      >
        <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".pdf,.txt,.docx" />
        
        {/* Upload Button */}
        <button 
          type="button"
          onClick={handleFileClick}
          disabled={isUploading || isLoading}
          className={`p-2 rounded-full transition-colors flex-shrink-0 
            ${isUploading 
                ? 'text-indigo-500 animate-pulse' 
                : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          title="Attach document"
        >
          {isUploading ? <Loader2 size={20} className="animate-spin" /> : <Paperclip size={20} />}
        </button>

        {/* Text Input */}
        <textarea
          ref={textareaRef}
          value={query}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? t('listening') : t('inputPlaceholder')}
          className="flex-1 max-h-[150px] bg-transparent border-0 focus:ring-0 p-2 
                     text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 
                     resize-none leading-relaxed scrollbar-thin overflow-y-auto"
          rows={1}
          disabled={isLoading || isUploading}
        />

        {/* Actions Right */}
        <div className="flex items-center gap-1">
           {/* Voice Toggle (No Dropdown) */}
           {!query && (
             <button 
               type="button"
               onClick={toggleListening}
               className={`p-2 rounded-full transition-colors 
                 ${isListening 
                    ? 'text-red-500 bg-red-100 dark:bg-red-900/30 animate-pulse' 
                    : 'text-gray-400 dark:text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                 }`}
               title={isListening ? "Stop Listening" : "Start Voice Input"}
             >
               {isListening ? <StopCircle size={20} /> : <Mic size={20} />}
             </button>
           )}

           {/* Send Button */}
           <button 
             type="submit"
             disabled={!query.trim() || isLoading || isUploading}
             className={`
               p-2 rounded-xl transition-all flex-shrink-0
               ${query.trim() && !isLoading && !isUploading
                 ? 'bg-[hsl(var(--pk-accent))] text-white shadow-md hover:scale-105' 
                 : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-600 cursor-not-allowed'}
             `}
           >
             {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
           </button>
        </div>
      </form>
      
      <div className="text-center mt-2">
        <p className="text-xs text-gray-400 dark:text-gray-600 transition-colors">
          {t('disclaimer')}
        </p>
      </div>
    </div>
  );
};

export default InputBar;
