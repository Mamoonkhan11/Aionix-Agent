import { useState, useCallback, useContext, createContext } from 'react';

const ToastContext = createContext<any>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Array<{ message: string; type: string }>>([]);

  const showToast = useCallback((message: string, type = 'success') => {
    setToasts(prev => [...prev, { message, type }]);
    setTimeout(() => setToasts(prev => prev.slice(1)), 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

