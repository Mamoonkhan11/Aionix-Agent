import Link from 'next/link';
import { useAuth } from '../../context/AuthProvider';

const nav = [
  { label: 'Overview', href: '/dashboard/overview', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'Tasks', href: '/dashboard/tasks', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'AI Agents', href: '/dashboard/agents', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'Voice', href: '/dashboard/voice', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'Insights', href: '/dashboard/insights', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'Reports', href: '/dashboard/reports', roles: ['admin', 'stakeholder', 'user'] },
  { label: 'Settings', href: '/dashboard/settings', roles: ['admin', 'stakeholder'] },
];

export default function Sidebar() {
  const { user } = useAuth();
  return (
    <aside className="w-56 p-6 bg-white dark:bg-zinc-900 shadow h-full flex flex-col">
      <div className="font-bold text-xl mb-10">Aionix</div>
      <nav className="flex-1 space-y-4">
        {nav.map(
          ({ label, href, roles }) => user && roles.includes(user.role) && (
            <Link key={href} href={href} className="block px-2 py-2 rounded hover:bg-primary/10">
              {label}
            </Link>
          )
        )}
      </nav>
    </aside>
  );
}

