import clsx from 'clsx';

export interface SkeletonListProps {
  count?: number;
  className?: string;
}

export function SkeletonList({ count = 3, className }: SkeletonListProps) {
  return (
    <ul className={clsx('animate-pulse space-y-2', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <li key={i} className="h-6 bg-gray-200 rounded" />
      ))}
    </ul>
  );
}
