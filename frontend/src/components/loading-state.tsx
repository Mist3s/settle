/**
 * Reusable wrapper for TanStack Query states: loading, error, empty, children.
 * Reduces boilerplate in every page/widget that consumes useQuery.
 */

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
  /** TanStack Query `isLoading` (first fetch, no cached data) */
  isLoading: boolean;
  /** TanStack Query `isError` */
  isError: boolean;
  /** Optional error message override */
  errorMessage?: string;
  /** Show empty state if true and not loading/error */
  isEmpty?: boolean;
  /** Text for empty state */
  emptyMessage?: string;
  /** Number of skeleton lines to show */
  skeletonCount?: number;
  /** Custom skeleton height */
  skeletonHeight?: string;
  /** Content to render when data is ready */
  children: React.ReactNode;
}

export function LoadingState({
  isLoading,
  isError,
  errorMessage,
  isEmpty,
  emptyMessage = "Нет данных",
  skeletonCount = 3,
  skeletonHeight = "h-20",
  children,
}: LoadingStateProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: skeletonCount }, (_, i) => (
          <Skeleton key={i} className={`w-full ${skeletonHeight} rounded-lg`} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Card className="border-danger/30 bg-danger/5">
        <CardContent className="py-8 text-center">
          <p className="text-sm text-danger font-medium">
            {errorMessage ?? "Ошибка загрузки данных"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Попробуйте обновить страницу
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isEmpty) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          {emptyMessage}
        </CardContent>
      </Card>
    );
  }

  return <>{children}</>;
}
