import { useAuth } from '../../context/AuthProvider';
import { useTheme } from '../ThemeProvider';

export default function TopBar() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b bg-white dark:bg-black">
      <div className="font-bold">AI Dashboard</div>
      <div className="flex items-center gap-4">
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800" aria-label="Switch theme">
          {theme === 'dark' ? '🌙' : '☀️'}
        </button>
        <section className="flex items-center gap-2">
          <span className="font-medium">{user?.email}</span>
          <button onClick={logout} className="ml-2 text-xs text-red-600 hover:underline">Logout</button>
        </section>
      </div>
    </header>
  );
}

