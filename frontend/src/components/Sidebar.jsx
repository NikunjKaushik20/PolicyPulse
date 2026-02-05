import React from 'react';
import { Plus, MessageSquare, LogOut, User } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

const Sidebar = ({ 
  history = [], 
  onSelectChat, 
  onNewChat, 
  currentResponseId,  
  isOpen,
  setIsOpen,
  t 
}) => {
  const { user, logout } = useAuth();

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Panel */}
      <div className={`
        fixed inset-y-0 left-0 z-30 w-64 bg-[hsl(var(--pk-sidebar))] 
        border-r border-black/5 dark:border-white/5
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:static flex flex-col
      `}>
        
        {/* Header / New Chat */}
        <div className="p-4">
          <button 
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-4 py-3 bg-[hsl(var(--pk-accent))] text-white rounded-lg hover:opacity-90 transition-opacity font-medium shadow-sm"
          >
            <Plus size={18} />
            <span>{t('newChat')}</span>
          </button>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            {t('recent')}
          </div>
          
          {history.length === 0 && (
            <div className="px-3 py-4 text-sm text-gray-400 text-center italic">
              {t('noChats')}
            </div>
          )}

          {history.map((chat) => (
            <button
              key={chat.id}
              onClick={() => {
                onSelectChat(chat.id);
                if (window.innerWidth < 768) setIsOpen(false);
              }}
              className={`
                w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center gap-3
                transition-colors truncate
                ${currentResponseId === chat.id 
                  ? 'bg-white dark:bg-gray-800 shadow-sm ring-1 ring-black/5 dark:ring-white/10 font-medium text-gray-900 dark:text-gray-100' 
                  : 'text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-200'}
              `}
            >
              <MessageSquare size={16} className="shrink-0 opacity-70" />
              <span className="truncate">{chat.title || t('newChat')}</span>
            </button>
          ))}
        </div>

        {/* User Footer */}
        <div className="p-4 border-t border-black/5 dark:border-white/5 bg-black/5 dark:bg-white/5">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-indigo-700 dark:text-indigo-300 font-bold text-xs ring-2 ring-white dark:ring-gray-700">
                {user.full_name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {user.full_name}
                </p>
                <button 
                  onClick={logout}
                  className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1 mt-0.5"
                >
                  <LogOut size={10} /> {t('signOut')}
                </button>
              </div>
            </div>
          ) : (
             <div className="px-3 py-2 text-sm text-center text-gray-500">
               {t('guest')}
             </div>
          )}
        </div>
      </div>
    </>
  );
};

export default Sidebar;
