'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import * as authApi from '../lib/api/auth';

const AuthContext = createContext<any>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const data = await authApi.me();
        if (data) setUser(data);
      } catch (error) {
        console.log('User not authenticated');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    console.log('Attempting login with:', email);
    const result = await authApi.login(email, password);
    console.log('Login result:', result);

    if (result.success) {
      console.log('Login successful, setting user:', result.user);
      setUser(result.user);
      console.log('Redirecting to dashboard...');
      router.push('/dashboard/overview');
    } else {
      console.log('Login failed:', result.error);
    }
    return result;
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

