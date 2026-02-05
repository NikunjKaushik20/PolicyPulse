import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';
import { Menu, Globe, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import Logo from '../assets/logo.png';

const ChatArea = ({ 
  messages, 
  onSendMessage, 
  isLoading, 
  onUploadComplete,
  onOpenSidebar,
  t,
  lang,
  setLang
}) => {
  const bottomRef = useRef(null);
  const { theme, toggleTheme } = useTheme();
  const [isLangOpen, setIsLangOpen] = React.useState(false);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 flex flex-col h-screen relative bg-white dark:bg-gray-900 transition-colors duration-300">
      {/* Header (Desktop & Mobile Unified) */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur border-b border-gray-100 dark:border-gray-700 p-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
            <button onClick={onOpenSidebar} className="md:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md">
                <Menu size={20} className="text-gray-600 dark:text-gray-300" />
            </button>
            <span className="font-semibold text-gray-700 dark:text-gray-100">PolicyPulse</span>
        </div>

        <div className="flex items-center gap-2">
            {/* Language Selector */}
            <div className="relative">
                <button 
                  onClick={() => setIsLangOpen(!isLangOpen)}
                  onBlur={() => setTimeout(() => setIsLangOpen(false), 200)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm font-medium text-gray-700 dark:text-gray-200"
                >
                    <Globe size={16} />
                    <span>{lang.split('-')[0].toUpperCase()}</span>
                </button>
                {/* Dropdown */}
                {isLangOpen && (
                  <div className="absolute right-0 top-full mt-1 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-100 dark:border-gray-700 py-1 z-20">
                      {[
                          { code: 'en-IN', label: 'English' },
                          { code: 'hi-IN', label: 'Hindi' },
                          { code: 'ta-IN', label: 'Tamil' },
                          { code: 'te-IN', label: 'Telugu' }
                      ].map(l => (
                          <button
                              key={l.code}
                              onClick={() => {
                                setLang(l.code);
                                setIsLangOpen(false);
                              }}
                              className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700
                                  ${lang === l.code ? 'text-indigo-600 font-medium' : 'text-gray-600 dark:text-gray-300'}
                              `}
                          >
                              {l.label}
                          </button>
                      ))}
                  </div>
                )}
            </div>

            {/* Theme Toggle */}
            <button 
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition-colors"
                title="Toggle Theme"
            >
                {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-3xl mx-auto w-full px-4 pt-10 pb-4">
          
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4 px-4">
              <div className="w-auto h-48 mb-0 flex items-center justify-center">
                  <img src={Logo} alt="PolicyPulse Logo" className="w-full h-full object-contain" />
              </div>
              <p className="text-gray-500 dark:text-gray-400 max-w-md">
                {t('welcomeDesc')}
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-xl mt-0">
                {[
                    { label: t('actions.suggest'), val: "Suggest schemes for farmers" },
                    { label: t('actions.nrega'), val: "Apply for NREGA" },
                    { label: t('actions.budget'), val: "PM Kisan budget 2024" },
                    { label: t('actions.eligible'), val: "Check my eligibility" }
                ].map(item => (
                  <button 
                    key={item.label}
                    onClick={() => onSendMessage(item.val)}
                    className="p-3 text-sm text-left bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl border border-gray-100 dark:border-gray-700 hover:border-gray-200 dark:hover:border-gray-600 transition-all"
                  >
                    {item.label} →
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
             <MessageBubble key={idx} message={msg} lang={lang} />
          ))}
          
          {isLoading && (
            <div className="flex justify-start mb-6">
               <div className="flex gap-4 max-w-3xl">
                  <div className="w-8 h-8 rounded-full bg-[hsl(var(--pk-accent))] flex items-center justify-center">
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce" />
                  </div>
                  <div className="text-gray-400 text-sm py-1.5 flex items-center gap-1">
                     {t('thinking')}
                     <span className="inline-flex gap-1 ml-1">
                        <span className="w-1 h-1 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="w-1 h-1 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="w-1 h-1 bg-gray-300 rounded-full animate-bounce"></span>
                     </span>
                  </div>
               </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 bg-gradient-to-t from-white via-white/80 to-transparent dark:from-gray-900 dark:via-gray-900/80 pb-4 pt-2">
        <InputBar 
            onSendMessage={onSendMessage} 
            onUploadComplete={onUploadComplete} 
            isLoading={isLoading} 
            t={t}
            lang={lang}
            setLang={setLang}
        />
      </div>
    </div>
  );
};

export default ChatArea;
