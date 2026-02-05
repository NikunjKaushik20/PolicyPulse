import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Configure axios defaults
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const baseUrl = import.meta.env.VITE_API_URL || '';
          const res = await axios.get(`${baseUrl}/auth/me`); 
          setUser(res.data);
        } catch (err) {
          console.error("Auth check failed:", err);
          logout();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (email, password) => {
    // Determine URL based on environment (dev vs prod)
    // For now assuming Vite proxy or direct URL
    const baseUrl = import.meta.env.VITE_API_URL || ''; 
    
    // OAuth2 standard requires x-www-form-urlencoded
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const res = await axios.post(`${baseUrl}/auth/login`, params, {
       headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    const newToken = res.data.access_token;
    
    localStorage.setItem('token', newToken);
    setToken(newToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    
    // Fetch user details immediately
    const userRes = await axios.get(`${baseUrl}/auth/me`);
    setUser(userRes.data);
    return userRes.data;
  };

  const signup = async (full_name, email, password) => {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    const res = await axios.post(`${baseUrl}/auth/signup`, {
      full_name,
      email,
      password
    });
    // Auto login after signup
    const newToken = res.data.access_token;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    
    const userRes = await axios.get(`${baseUrl}/auth/me`);
    setUser(userRes.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
