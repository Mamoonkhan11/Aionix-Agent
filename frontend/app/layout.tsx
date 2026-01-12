import './styles/globals.css';
import { ReactNode } from 'react';
import { AuthProvider } from '../context/AuthProvider';
import { ThemeProvider } from '../components/ThemeProvider';

export const metadata = {
  title: 'Aionix AI Dashboard',
  description: 'Enterprise SaaS AI administration dashboard',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

