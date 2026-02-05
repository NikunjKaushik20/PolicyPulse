import React, { useState, useEffect, createContext } from 'react';
import axios from 'axios';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import LoginModal from './components/LoginModal';
import { Loader2 } from 'lucide-react';
import { translations } from './translations';

export const LanguageContext = createContext();

const MainLayout = () => {
  const { user, token, loading } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingDemographics, setPendingDemographics] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  
  // Consume Language Context
  const { lang, setLang, t } = React.useContext(LanguageContext);

  useEffect(() => {
    if (user && token) {
      loadHistory();
    }
  }, [user, token]);

  const loadHistory = async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await axios.get(`${baseUrl}/history`, {
         headers: { Authorization: `Bearer ${token}` }
      });
      setChatHistory(res.data);
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const handleUploadComplete = (data) => {
      if (data.extracted_fields) {
          triggerAutoSuggestion(data.extracted_fields);
      }
  };

  const triggerAutoSuggestion = async (demographics) => {
      const text = "Suggest policies based on my uploaded document";
      const userMsg = { role: 'user', content: `[Uploaded ${demographics.document_type || 'Document'}]` };
      setMessages(prev => [...prev, userMsg]);
      setIsProcessing(true);

      try {
        const baseUrl = import.meta.env.VITE_API_URL || ''; 
        const res = await axios.post(`${baseUrl}/query`, {
            query_text: text,
            session_id: sessionId,
            demographics: demographics,
            language: lang.split('-')[0]
        });

        const botMsg = { 
            role: 'model', 
            content: res.data.final_answer,
            confidence: res.data.confidence_score,
            drift_timeline: res.data.drift_timeline,
            drift_max: res.data.drift_max,
            drift_policy: res.data.drift_policy
        };
        
        setMessages(prev => [...prev, botMsg]);
        
        if (!sessionId && res.data.session_id) {
            setSessionId(res.data.session_id);
        }
      } catch (err) {
          console.error(err);
      } finally {
          setIsProcessing(false);
      }
  };

  const handleSendMessage = async (text) => {
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsProcessing(true);

    try {
      const baseUrl = import.meta.env.VITE_API_URL || ''; 
      const res = await axios.post(`${baseUrl}/query`, {
        query_text: text,
        session_id: sessionId,
        demographics: pendingDemographics,
        language: lang.split('-')[0]
      });

      setPendingDemographics(null);

      const botMsg = { 
        role: 'model', 
        content: res.data.final_answer,
        confidence: res.data.confidence_score,
        drift_timeline: res.data.drift_timeline,
        drift_max: res.data.drift_max,
        drift_policy: res.data.drift_policy
      };
      
      setMessages(prev => [...prev, botMsg]);
      
      if (!sessionId && res.data.session_id) {
        setSessionId(res.data.session_id);
      }
      
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'model', 
        content: "Sorry, I encountered an error. Please try again." 
      }]);
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setPendingDemographics(null);
    if (window.innerWidth < 768) setIsSidebarOpen(false);
  };

  const loadChat = async (id) => {
    setSessionId(id);
    setIsProcessing(true);
    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await axios.get(`${baseUrl}/history/${id}`, {
          headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(res.data);
      if (window.innerWidth < 768) setIsSidebarOpen(false);
    } catch (err) {
      console.error("Failed to load session", err);
    } finally {
        setIsProcessing(false);
    }
  };

  if (loading) {
     return <div className="h-screen flex items-center justify-center bg-white dark:bg-gray-900"><Loader2 className="animate-spin text-indigo-500" /></div>;
  }

  if (!user) {
    return <LoginModal />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-white dark:bg-gray-900 transition-colors duration-300">
      <Sidebar 
        isOpen={isSidebarOpen} 
        setIsOpen={setIsSidebarOpen}
        history={chatHistory} 
        currentResponseId={sessionId}
        onNewChat={startNewChat}
        onSelectChat={loadChat}
        t={t}
      />
      
      <ChatArea 
        messages={messages}
        onSendMessage={handleSendMessage}
        onUploadComplete={handleUploadComplete}
        isLoading={isProcessing}
        onOpenSidebar={() => setIsSidebarOpen(true)}
        t={t}
        lang={lang}
        setLang={setLang}
      />
    </div>
  );
};

const App = () => {
  const [lang, setLang] = useState(localStorage.getItem('lang') || 'en-IN');

  const t = (key) => {
    const keys = key.split('.');
    let value = translations[lang];
    for (const k of keys) {
      value = value?.[k];
    }
    return value || key;
  };

  useEffect(() => {
    localStorage.setItem('lang', lang);
  }, [lang]);

  return (
    <ThemeProvider>
       <LanguageContext.Provider value={{ t, lang, setLang }}>
          <AuthProvider>
            <MainLayout />
          </AuthProvider>
       </LanguageContext.Provider>
    </ThemeProvider>
  );
}

export default App;
