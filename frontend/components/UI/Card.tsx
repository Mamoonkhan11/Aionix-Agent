export default function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-xl shadow p-6 bg-white dark:bg-zinc-900 flex flex-col items-start">
      <span className="text-sm text-gray-500 mb-2">{title}</span>
      <span className="text-2xl font-bold">{value}</span>
    </div>
  );
}

