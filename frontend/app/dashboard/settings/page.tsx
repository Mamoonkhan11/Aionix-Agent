import { useAuth } from '../../../context/AuthProvider';

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <div className="max-w-lg space-y-6">
        {/* Profile info section */}
        <div>
          <label>Email:</label>
          <div className="p-2 border rounded bg-gray-100 dark:bg-zinc-800">{user?.email}</div>
        </div>
        {/* Role visibility (admin only) */}
        {user?.role === 'admin' && (
          <div>
            <label>Role:</label>
            <div className="p-2 border rounded bg-blue-100 dark:bg-zinc-800">{user.role}</div>
          </div>
        )}
        {/* TODO: API Key management, Notification preferences, etc. */}
      </div>
    </div>
  );
}
