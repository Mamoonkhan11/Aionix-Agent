export default function LoadingSkeleton({ width = '100%', height = 32 }: { width?: string; height?: number }) {
  return (
    <div
      className="animate-pulse bg-gray-200 dark:bg-zinc-700 rounded w-full"
      style={{ width, height }}
    />
  );
}

