import React, { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Loader2 } from 'lucide-react';

const LoginModal = () => {
  const { login, signup, loginAsGuest } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      if (isLogin) {
        await login(formData.email, formData.password);
      } else {
        await signup(formData.full_name, formData.email, formData.password);
      }
    } catch (err) {
      console.error("Login Error:", err);
      const detail = err.response?.data?.detail;
      const status = err.response?.status;
      setError(detail ? `${detail} (${status})` : `Authentication failed (${status || 'Network Error'})`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 border border-white/20">
        <div className="text-center mb-8">
           <h1 className="text-3xl font-bold text-gray-800 mb-2">PolicyPulse</h1>
           <p className="text-gray-500">
             {isLogin ? "Welcome back" : "Create your account"}
           </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input 
                type="text" 
                required 
                className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                placeholder="John Doe"
                value={formData.full_name}
                onChange={e => setFormData({...formData, full_name: e.target.value})}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input 
              type="email" 
              required 
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
              placeholder="name@example.com"
              value={formData.email}
              onChange={e => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input 
              type="password" 
              required 
              className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
              placeholder="••••••••"
              value={formData.password}
              onChange={e => setFormData({...formData, password: e.target.value})}
            />
          </div>

          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-[hsl(var(--pk-accent))] text-white font-semibold py-2.5 rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 mt-6"
          >
            {isLoading && <Loader2 size={18} className="animate-spin" />}
            {isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-500">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            onClick={() => { setIsLogin(!isLogin); setError(""); }}
            className="text-indigo-600 font-semibold hover:underline"
          >
            {isLogin ? "Sign up" : "Log in"}
          </button>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-100">
          <button
            onClick={() => loginAsGuest()}
            className="w-full text-gray-600 font-medium py-2 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
          >
            Continue as Guest
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
