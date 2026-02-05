import React from 'react';
import Markdown from 'markdown-to-jsx';
import { User, Bot, Copy, Check, Volume2 } from 'lucide-react';
import { useState } from 'react';
import DriftChart from './DriftChart';

const MessageBubble = ({ message, lang }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(message.content);
    // Map our lang codes to browser standard if needed, or use as is
    // Browser usually expects 'en-US', 'hi-IN', etc.
    utterance.lang = lang; 
    
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  // Check if message has drift data for visualization
  const hasDriftData = !isUser && message.drift_timeline && message.drift_timeline.length > 0;

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6 group`}>
      <div className={`
        flex gap-4 max-w-3xl w-full
        ${isUser ? 'flex-row-reverse' : 'flex-row'}
      `}>
        
        {/* Avatar */}
        <div className={`
          w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1
          ${isUser 
            ? 'bg-gray-200 text-gray-600' 
            : 'bg-[hsl(var(--pk-accent))] text-white shadow-md'}
        `}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>

        {/* Message Content */}
        <div className={`
          flex-1 min-w-0 overflow-hidden
          ${isUser ? 'text-right' : 'text-left'}
        `}>
          
          {/* Header Name */}
          <div className="text-xs font-semibold text-gray-400 mb-1">
            {isUser ? "You" : "PolicyPulse"}
          </div>

          <div className={`
            prose prose-slate dark:prose-invert max-w-none text-[15px] leading-7
            ${isUser 
              ? 'bg-gray-100/80 dark:bg-gray-800/80 px-4 py-2.5 rounded-2xl rounded-tr-sm text-gray-800 dark:text-gray-100 inline-block' 
              : 'text-gray-800 dark:text-gray-200'}
          `}>
             <Markdown options={{
               overrides: {
                 a: {
                   component: ({ children, ...props }) => (
                     <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                       {children}
                     </a>
                   ),
                 },
               },
             }}>
               {message.content}
             </Markdown>
             
             {/* Drift Chart (when present) */}
             {hasDriftData && (
               <DriftChart 
                 timeline={message.drift_timeline}
                 maxDrift={message.drift_max}
                 policyId={message.drift_policy}
               />
             )}
             
             {/* Confidence Badge (Bot Only) */}
             {!isUser && message.confidence && (
                <div className="mt-3 flex items-center gap-2">
                   <span className={`
                     text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border
                     ${message.confidence > 0.7 ? 'bg-green-50 text-green-700 border-green-200' : 
                       message.confidence > 0.4 ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                       'bg-red-50 text-red-700 border-red-200'}
                   `}>
                     {message.confidence > 0.7 ? 'High Confidence' : 'Check Source'}
                   </span>
                </div>
             )}
          </div>

          {/* Actions */}
          {!isUser && (
             <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
               <button 
                 onClick={handleSpeak}
                 className={`p-1 rounded transition-all flex items-center gap-1 ${isSpeaking ? 'text-indigo-600 bg-indigo-50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
                 title="Read Aloud"
               >
                 <Volume2 size={14} className={isSpeaking ? "animate-pulse" : ""} />
                 <span className="text-xs">{isSpeaking ? 'Stop' : 'Speak'}</span>
               </button>
               <div className="w-px h-3 bg-gray-200 mx-1"></div>
               <button 
                 onClick={handleCopy}
                 className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-all"
                 title="Copy"
               >
                 {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
               </button>
             </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default MessageBubble;

