import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-zinc-950">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopBar />
        <main className="p-6 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

