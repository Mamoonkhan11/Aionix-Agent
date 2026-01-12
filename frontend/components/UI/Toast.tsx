import { useToast } from '../../hooks/useToast';
export default function Toast() {
  const { toasts } = useToast();
  return (
    <div className="fixed top-4 right-4 z-40 space-y-2">
      {toasts.map((t, i) => (
        <div
          key={i}
          className={
            'p-3 rounded bg-white dark:bg-zinc-900 shadow border-l-4 ' +
            {
              error: 'border-red-500',
              success: 'border-green-500',
            }[t.type || 'success']
          }
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

